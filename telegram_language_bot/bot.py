#!/usr/bin/env python3
# -*-encoding: utf-8-*-


""" TODO: TEST FOR CONCURRENCY ERRORS
     - work on handlers placement (probably should be moved to another module)
     - add verification for /add_time
     - add schedule presets (every hour, every half an hour etc.)
     - update handlers to use Keyboard Markups for more convenient user exp
     - multiple notes management:
        Addition of new words when previous are studied (maybe send some
        kind of explanation in case user attempts to add new words when he isn't
        proficient enough with a certain percent of already uploaded ones)
        rework words retrieving: introduce *known* *unknown* status for each
        word, provide unknown words to user more frequently, than unlearnt.
     - if is_registered returns FALSE, this info should be return to a user
        somehow.
"""

import sys
import logging as log
from functools import partial, wraps
from threading import Thread

from telegram_language_bot.utils import ThreadedDict, Scheduler
from language_bot_core import dispatch_mainloop, DBManager, \
                            build_random_words_by_uids, parse
from telegram_language_bot.constants import TOKEN, DB_PATH, GREETING_MSG,\
                            WORDS_UPLOAD_MSG, COMMANDS

import telebot as tb


log.basicConfig(stream=sys.stdout,
                format='%(message)s',
                level=log.DEBUG)


# global storage for all currently asked words {uid: (asked word: answer)}
# designed to be thread-sustainable
words_buffer = ThreadedDict()

# to allow users answer questions and upload new words we store
# id's of currently answering/uploading users

# TODO: strange approach, REVISE!
permitted_for_answer = {}
permitted_for_update = {}
registered_users_buffer = set()


class ObjectedTeleBot(tb.TeleBot):
    """This subclass intended to allow reply handlers to be class methods
    instead of global functions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # object of class, where handlers are defined
        self._handler_object = None

    def polling(self, none_stop=False, interval=0,
                timeout=20, handler_obj=None):
        if handler_obj is not None:
            self._handler_object = handler_obj
        super().polling(none_stop, interval, timeout)

    def _build_handler_dict(self, handler, **filters):
        log.info(f"Registered handler: {handler}")
        # now instead of storing a reference to a global function we will
        # extract method with getattr from provided object
        res = {
            'function': lambda msg: getattr(self._handler_object,
                                            handler.__name__)(msg),
            'filters': filters
        }
        return res


bot = ObjectedTeleBot(TOKEN)


def is_registered(msg):
    """
    Helper validation function to prevent any actions from unregistered users

    :param msg:
    :return: is allowed to use command
    """
    if msg.chat.id in registered_users_buffer:
        return True
    log.info(f"Unregistered user: {msg.from_user.username} made an attempt "
             f"to access bot commands")
    return False


class HandlerMeta(type):
    """
    Metaclass for telegram bot handler classes. Adds common functionality
    to all methods which name ends with 'handler'

    """
    def __new__(mcs, name, bases, attrs):
        def log_call(f):

            @wraps(f)
            def wrapper(self, msg):
                log.debug(f"{f.__name__} called by {msg.from_user}")
                f(self, msg)

            return wrapper

        for attr_name, attr in attrs.items():
            if attr_name.endswith('handler'):
                attrs[attr_name] = log_call(attr)

        return type(name, bases, attrs)


class CommandsProcessor(metaclass=HandlerMeta):

    @bot.message_handler(commands=['start'])
    def start_handler(self, msg):
        """
        /start command handler

        :param msg: message
        :return: None
        """
        db = DBManager(DB_PATH)
        db.connect()
        if not db.is_registered(msg.chat.id):
            db.register(msg.chat.id)
            bot.send_message(msg.chat.id, GREETING_MSG)
            permitted_for_answer[msg.chat.id] = True
            permitted_for_update[msg.chat.id] = False
            registered_users_buffer.update([msg.chat.id])
        else:
            bot.send_message(msg.chat.id, "I know you.")
        db.disconnect()

    @bot.message_handler(commands=['info'], func=is_registered)
    def info_handler(self, msg):
        reply = ""
        for command, desc in COMMANDS.items():
            reply += "/{} - {}\n".format(command, desc)
        bot.send_message(msg.chat.id, reply)

    @bot.message_handler(commands=['upload_info'], func=is_registered)
    def upload_info_handler(self, msg):
        bot.send_message(msg.chat.id, WORDS_UPLOAD_MSG)

    @bot.message_handler(commands=['next_word'], func=is_registered)
    def next_word_handler(self, msg):
        """
        "I dont want wait, or I can not answer given word - give me a new one"
        (Implicitly modifies global words buffer)

        :param msg: message
        :return: None
        """
        global words_buffer
        db = DBManager(DB_PATH)
        db.connect()
        new_pair = build_random_words_by_uids(db, [msg.chat.id])
        db.disconnect()
        if not new_pair:
            bot.send_message(msg.chat.id, "You haven't added any words yet")
            return
        if msg.chat.id in words_buffer:
            words_buffer.pop(msg.chat.id)   # ensure absence of previous word
        callback([msg.chat.id], new_pair)
        permitted_for_answer[msg.chat.id] = True
        permitted_for_update[msg.chat.id] = False

    @bot.message_handler(commands=['reveal_last'], func=is_registered)
    def reveal_word_handler(self, msg):
        """
        "I forgot translation - give it to me!"

        :param msg: message
        :return: None
        """
        global words_buffer
        resp = words_buffer.get(msg.chat.id)
        if resp is None:
            resp = "Looks like there is no scheduled words for you yet, " \
                   "or you already answered one."
        else:
            resp = resp[1]
        bot.send_message(msg.chat.id, resp)


    @bot.message_handler(commands=['show_words'], func=is_registered)
    def show_words_helper(self, msg):
        db = DBManager(DB_PATH)
        db.connect()
        resp_data = db.get_all_words_by_uid(msg.chat.id)
        if not resp_data:
            resp = "No words uploaded yet"
        else:
            resp = " ".join(map(lambda s: " - ".join(s) + '\n', resp_data)) + ' '
        bot.send_message(msg.chat.id, resp)
        db.disconnect()

    @bot.message_handler(commands=['add_time'], func=is_registered)
    def add_time_handler(self, msg):
        """
        "Send me message ALSO at this time"

        :param msg: message
        :return: None
        """
        raw_data = msg.text.split(' ')
        log.info(f'User {msg.from_user.username} attempted to '
                 f'add time {raw_data}')
        if len(raw_data) != 2 or not is_valid_time_string(raw_data[1]):
            bot.send_message(msg.chat.id,
                             "Inconsistent time format, try to stick with hh:mm:ss")
        else:
            time_string = raw_data[1]
            db = DBManager(DB_PATH)
            db.connect()
            db.add_scheduled_time_by_uid(msg.chat.id, time_string)
            bot.send_message(msg.chat.id,
                             f"Time {time_string} added in schedule")


    @bot.message_handler(commands=['add_words'], func=is_registered)
    def add_words_handler(self, msg):
        log.info(f"User {msg.from_user.username} is now updating his words")
        bot.send_message(msg.chat.id,
                         "Send me your notes in next message\n "
                         "(Type BREAK to abandon)")
        permitted_for_answer[msg.chat.id] = False
        permitted_for_update[msg.chat.id] = True

    @bot.message_handler(commands=['schedule'], func=is_registered)
    def schedule_helper(self, msg):
        db = DBManager(DB_PATH)
        db.connect()
        schedule = db.get_schedule_by_uid(msg.chat.id)
        if not schedule:
            resp = "You haven't schedule any questions yet"
        else:
            resp = "\n".join(schedule)
        bot.send_message(msg.chat.id, resp)

    @bot.message_handler(func=lambda msg:
                         permitted_for_answer.get(msg.chat.id, False))
    def answer_handler(self, msg):
        """
        Translation attempt handler

        :param msg:
        :return:
        """
        global words_buffer
        if msg.chat.id in words_buffer \
           and msg.text.lower().strip() in words_buffer[msg.chat.id][1].lower():
            words_buffer.pop(msg.chat.id)
            bot.send_message(msg.chat.id, "Correct!")
        else:
            if is_registered(msg):
                bot.send_message(msg.chat.id, "Incorrect, try again.")
            else:
                bot.send_message(msg.chat.id, "You are not registered"
                                              "Type /start to begin")

    @bot.message_handler(func=lambda msg:
                         permitted_for_update.get(msg.chat.id, False))
    def upload_handler(self, msg):
        permitted_for_update[msg.chat.id] = False
        permitted_for_answer[msg.chat.id] = True
        plain_text = msg.text
        if plain_text.strip().lower() == 'break':
            log.info(f'User {msg.from_user.username} has abandoned his upload.')
            bot.send_message(msg.chat.id, "Upload abandoned")
            return
        processed, unprocessed = parse(plain_text)
        db = DBManager(DB_PATH)
        db.connect()
        db.add_words(msg.chat.id, processed)
        log.info(f"User {msg.from_user.username} has updated his "
                 f"words successfully")
        resp1 = "Processed words:" + \
                " ".join(map(lambda s: " ".join(s) + '\n', processed)) + "\n"
        resp2 = "Unprocessed words:" + \
                " ".join(map(lambda s: " ".join(s) + '\n', unprocessed))
        bot.send_message(msg.chat.id, resp1 + resp2)


def is_valid_time_string(time_str: str) -> bool:
    try:
        hh, mm, ss = time_str.split(':')
        hh, mm, ss = int(hh), int(mm), int(ss)
        if not 0 <= hh <= 23 or not 0 <= mm <= 59 or not 0 <= mm <= 59:
            raise ValueError
    except ValueError:
        return False
    return True


def update_words_buffer_with(data: dict):
    """
    Modified behavior of dictionary updating: new records do not rewrite
    already present ones -- such behaviour required because
    word buffer contains all users's last words, and given function
    is called whenever a new user needs to be notified, hence
    data, which is already present in dict is supposed to be unharmed.

    :param data:
    :return:
    """
    global words_buffer
    for k, v in data.items():
        # assure that word was answered correctly
        if k not in words_buffer.keys():
            words_buffer[k] = v


def callback(uids: list, words: dict):
    """
    Callback function. Awaits for two provided arguments
    (uid: list, new_words: list)

    uid -           list of user id's, which needs to be traversed and each user
                    supposed to be notified with new (or probably old, but
                    incorrectly answered word)
    new_words -     dictionary (uid: (word_from, word_to)) new words for each
                    user in case old one was answered correct
    :param uids:
    :param words:
    :return:
    """
    update_words_buffer_with(words)
    for id in uids:
        if id in words_buffer.keys():
            log.info(f"Notifying user: {id}")
            bot.send_message(id, "Translation for: " + words_buffer[id][0])


def _initialize_variables():
    db = DBManager(DB_PATH)
    db.connect()
    uids = db.get_uids()

    for uid in uids:
        permitted_for_answer[uid] = True
        permitted_for_update[uid] = False
    registered_users_buffer.update(uids)
    db.disconnect()


def run_bot(polling_delay):
    handler_object = CommandsProcessor()
    _initialize_variables()
    t1 = Thread(target=bot.polling,
                kwargs={"none_stop": True, 'interval': 1, 'handler_obj': handler_object})
    t2 = Thread(target=dispatch_mainloop,
                args=(DB_PATH, polling_delay, callback))

    t1.start()
    t2.start()

    t1.join()
    t2.join()


if __name__ == '__main__':
    pass

