#!/usr/bin/env python3
# -*-encoding: utf-8-*-


import time
import types

from .dbmanager import DBManager


def get_cur_time_str():
    cur_time = time.localtime()
    s = "{H:>02}:{M:>02}:{S:>02}"
    return s.format(H=cur_time.tm_hour, M=cur_time.tm_min, S=cur_time.tm_sec)


def build_random_words_by_uids(db: DBManager, uids: list):
    """
    For given database manager instance and user id list builds
    dict {user_id: (word_from, word_to)}

    :param db: DBManager instance (already connected!)
    :param uids: user_id's list
    :return: dict({user_id: (word_from, word_to)})
    """
    res = {uid: db.get_random_word_by_uid(uid) for uid in uids}
    return res


def dispatch_mainloop(path:str, delay: int, callback: types.FunctionType):
    """
    mainloop for scheduled word dispatching, intended to be target of Thread

    :param path: database path
    :param delay: polling delay
    :param callback: callable - callback function, which (supposedly)
                     processes scheduled word dispatch
    :return:
    """
    db = DBManager(path)

    # first preparation
    db.connect()
    uids = db.get_uids()
    cur_time_str = get_cur_time_str()

    # next schedule time for each user id
    uids_next_time = {uid: db.get_next_time_by_uid(cur_time_str, uid)
                      for uid in uids}
    db.disconnect()
    while True:
        # print("DISPATCHER AWAKE")
        # print("prev uids map:", uids_next_time)
        db.connect()

        # list with user ids, which needs to be processed now
        # (scheduled time arrived)
        uids = []
        cur_time_str = get_cur_time_str()
        for uid in db.get_uids():
            cur_uid_time = db.get_next_time_by_uid(cur_time_str, uid)

            # if new user added:
            if uid not in uids_next_time:
                uids_next_time[uid] = None
                continue

            # if new time was added, user is not supposed to be notified
            # immediately
            if uids_next_time[uid] is None and cur_uid_time is not None:
                uids_next_time[uid] = cur_uid_time
                continue

            # next time changed => last scheduled time passed => needs
            # to be processed
            if cur_uid_time != uids_next_time[uid]:
                uids_next_time[uid] = cur_uid_time
                uids.append(uid)
        new_words = build_random_words_by_uids(db, uids)
        if new_words:
            callback(uids, new_words)
        db.disconnect()
        # print("upd uids map:", uids_next_time)
        # print(f"DISPATCHER ASLEEP FOR: {delay} sec")
        time.sleep(delay)

