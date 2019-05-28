# NEEDS TO BE TESTED FOR CONCURRENCY ERRORS
# GLOBAL VARIABLE IS EXPOSED TO BE MODIFIED FROM DIFFERENT THREADS


from threading import Thread

import telebot as tb

from language_bot_core import dispatch_mainloop, DBManager, \
                            build_random_words_by_uids, parse
from constants import token, db_path, greeting_msg, words_upload_msg, commands

# global storage for all currently asked words {uid: (asked word: answer)}
words_buffer = {}

# to allow users answer questions and upload new words we store
# id's of currently answering/uploading users

# TODO: strange approach, REVISE!
permitted_for_answer = {}
permitted_for_update = {}
registered_users_buffer = set()


bot = tb.TeleBot(token)


# TODO: work on handlers placement (probably should be moved to another module)
def is_registered(msg):
    """
    Helper validation function to prevent any actions from unregistered users

    :param msg:
    :return: is allowed to use command
    """
    if msg.chat.id in registered_users_buffer:
        return True
    return False

@bot.message_handler(commands=['start'])
def start_handler(msg):
    """
    /start command handler

    :param msg: message
    :return: None
    """
    db = DBManager(db_path)
    db.connect()
    if not db.is_registered(msg.chat.id):
        db.register(msg.chat.id)
        bot.send_message(msg.chat.id, greeting_msg)
        permitted_for_answer[msg.chat.id] = True
        permitted_for_update[msg.chat.id] = False
    else:
        bot.send_message(msg.chat.id, "I know you.")
    db.disconnect()


@bot.message_handler(commands=['info'], func=is_registered)
def info_helper(msg):
    reply = ""
    for command, desc in commands.items():
        reply += "/{} - {}\n".format(command, desc)
    bot.send_message(msg.chat.id, reply)


@bot.message_handler(commands=['upload_info'], func=is_registered)
def upload_info_helper(msg):
    bot.send_message(msg.chat.id, words_upload_msg)


@bot.message_handler(commands=['next_word'], func=is_registered)
def next_word_handler(msg):
    """
    "I dont want wait, or I can not answer given word - give me a new one"
    (Implicitly modifies global words buffer)

    :param msg: message
    :return: None
    """
    global words_buffer
    db = DBManager(db_path)
    db.connect()
    new_pair = build_random_words_by_uids(db, [msg.chat.id])
    db.disconnect()
    if new_pair is None:
        bot.send_message(msg.chat.id, "You haven't added any words yet")
        return
    if msg.chat.id in words_buffer:
        words_buffer.pop(msg.chat.id)   # ensure absence of previous word
    callback([msg.chat.id], new_pair)
    permitted_for_answer[msg.chat.id] = True
    permitted_for_update[msg.chat.id] = False


@bot.message_handler(commands=['reveal_last'], func=is_registered)
def reveal_word_handler(msg):
    """
    "I forgot translation - give it to me!"

    :param msg: message
    :return: None
    """
    global words_buffer
    resp = words_buffer.get(msg.chat.id, None)
    if resp is None:
        resp = "Looks like there is no scheduled words for you yet, " \
               "or you already answered one."
    else:
        resp = resp[1]
    bot.send_message(msg.chat.id, resp)


@bot.message_handler(commands=['show_words'], func=is_registered)
def show_words_helper(msg):
    db = DBManager(db_path)
    db.connect()
    resp_data = db.get_all_words_by_uid(msg.chat.id)
    resp = " ".join(map(lambda s: " - ".join(s) + '\n', resp_data)) + ' '
    bot.send_message(msg.chat.id, resp)
    db.disconnect()


def is_valid_time_string(time_str: str) -> bool:
    try:
        hh, mm, ss = time_str.split(':')
        hh, mm, ss = int(hh), int(mm), int(ss)
        assert 0 <= hh <= 23
        assert 0 <= mm <= 59
        assert 0 <= mm <= 59
    except ValueError:
        return False
    except AssertionError:
        return False
    return True


@bot.message_handler(commands=['add_time'], func=is_registered)
def add_time_handler(msg):
    """
    "Send me message ALSO at this time"

    :param msg: message
    :return: None
    """
    raw_data = msg.text.split(' ')
    if len(raw_data) != 2 or not is_valid_time_string(raw_data[1]):
        bot.send_message(msg.chat.id,
                         "Inconsistent time format, try to stick with hh:mm:ss")
    else:
        time_string = raw_data[1]
        db = DBManager(db_path)
        db.connect()
        db.add_scheduled_time_by_uid(msg.chat.id, time_string)
        bot.send_message(msg.chat.id,
                         f"Time {time_string} added in schedule")


@bot.message_handler(commands=['add_words'], func=is_registered)
def add_words_handler(msg):
    bot.send_message(msg.chat.id,
                     "Send me your notes in next message\n "
                     "(Type BREAK to abandon)")
    permitted_for_answer[msg.chat.id] = False
    permitted_for_update[msg.chat.id] = True


@bot.message_handler(commands=['schedule'], func=is_registered)
def schedule_helper(msg):
    db = DBManager(db_path)
    db.connect()
    schedule = db.get_schedule_by_uid(msg.chat.id)
    if not schedule:
        resp = "You haven't schedule any questions yet"
    else:
        resp = "\n".join(schedule)
    bot.send_message(msg.chat.id, resp)


@bot.message_handler(func=lambda msg:
                     permitted_for_answer.get(msg.chat.id, False))
def answer_handler(msg):
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
def upload_handler(msg):
    permitted_for_update[msg.chat.id] = False
    permitted_for_answer[msg.chat.id] = True
    plain_text = msg.text
    if plain_text.strip().lower() == 'break':
        bot.send_message(msg.chat.id, "Upload abandoned")
        return
    processed, unprocessed = parse(plain_text)
    db = DBManager(db_path)
    db.connect()
    db.add_words(msg.chat.id, processed)
    resp1 = "Processed words:" + \
            " ".join(map(lambda s: " ".join(s) + '\n', processed)) + "\n"
    resp2 = "Unprocessed words:" + \
            " ".join(map(lambda s: " ".join(s) + '\n', unprocessed))
    bot.send_message(msg.chat.id, resp1 + resp2)


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
            bot.send_message(id, "Translation for: " + words_buffer[id][0])


def initialize_variables():
    db = DBManager(db_path)
    db.connect()
    uids = db.get_uids()

    for uid in uids:
        permitted_for_answer[uid] = True
        permitted_for_update[uid] = False
    registered_users_buffer.update(uids)
    db.disconnect()


if __name__ == '__main__':
    initialize_variables()

    t1 = Thread(target=bot.polling, kwargs={"none_stop": True})
    t2 = Thread(target=dispatch_mainloop, args=(db_path, 10, callback))

    t1.start()
    t2.start()
