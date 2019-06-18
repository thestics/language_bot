#!/usr/bin/env python3
# -*-encoding: utf-8-*-


import sqlite3


class BaseDatabaseException(Exception):
    pass


class DisconnectedDatabaseError(BaseDatabaseException):
    pass


class ConnectedDatabaseError(BaseDatabaseException):
    pass


class DisconnectedDBMeta(type):
    """Metaclass which defines common behavior of unimplemented methods for
        DisconnectedDB class

            Metaclass required because State classes implemented in such a way
        that they are never instantiated. Following example explains why
        this directly means that custom metaclass is required.
        a = DisconnectedDB()
        a.method()              -- invokes a.__class__.__getattribute__
        (or __getattr__). In this case a.__class__ == DisconnectedDB, likewise
        DisconnectedDB.method() -- invokes DisconnectedDB.__class__.__getattr__
        however, in this case __class__ == type (because any class in Python
        is an instance of type) and all method management is hidden in
        type.__getattr__, so in this case it is crucial to define own custom
        metaclass
    """

    def __getattr__(self, item):
        raise DisconnectedDatabaseError('Cannot perform queries '
                                        'on closed database')


class ConnectedDB:
    """Class which represents connected database state"""

    @staticmethod
    def connect(db_manager):
        raise ConnectedDatabaseError("Already connected")

    @staticmethod
    def disconnect(db_manager):
        db_manager.conn.close()
        db_manager.curs = None
        db_manager.new_state(DisconnectedDB)

    @staticmethod
    def get_uids(db_manager):
        q = "select user_id from user_ids"
        db_manager.curs.execute(q)
        res = [item[0] for item in db_manager.curs.fetchall()]
        return res

    @staticmethod
    def get_schedule_by_uid(db_manager, uid):
        q = """select time from schedule where user_id=?"""
        res = [item[0] for item in db_manager.curs.execute(q, (uid,))]
        return res

    @staticmethod
    def is_registered(db_manager, uid):
        q = """select * from user_ids where user_id=?"""
        db_manager.curs.execute(q, (uid,))
        return bool(db_manager.curs.fetchall())

    @staticmethod
    def register(db_manager, uid):
        if not db_manager.is_registered(uid):
            q = """insert into user_ids values (?)"""
            db_manager.curs.execute(q, (uid,))
            db_manager.conn.commit()

    @staticmethod
    def get_all_words_by_uid(db_manager, uid):
        q = """select word_from, word_to from word_src where user_id = ?"""
        db_manager.curs.execute(q, (uid,))
        return db_manager.curs.fetchall()

    @staticmethod
    def add_scheduled_time_by_uid(db_manager, uid: int, time_string: str):
        q = "select * from schedule where time=?"
        db_manager.curs.execute(q, (time_string, ))
        if not db_manager.curs.fetchall():
            q = "insert into schedule values (?, ?)"
            db_manager.curs.execute(q, (uid, time_string))
        db_manager.conn.commit()

    @staticmethod
    def delete_scheduled_time_by_uid(db_manager, uid: int, time_string: str):
        q1 = "select count(*) from schedule where user_id=? and time=?"
        db_manager.curs.execute(q1, (uid, time_string))
        status = db_manager.curs.fetchone()[0]

        q2 = "delete from schedule where user_id=? and time=?"
        db_manager.curs.execute(q2, (uid, time_string))
        db_manager.conn.commit()
        return status

    @staticmethod
    def add_words(db_manager, uid: int, words: list):
        q = "insert into word_src values (?, ?, ?, ?)"
        for word_from, word_to in words:
            db_manager.curs.execute(q, (uid, word_from, word_to, 0))
        db_manager.conn.commit()

    @staticmethod
    def get_next_time_by_uid(db_manager, cur_time_str, uid):
        q = "select time from schedule where time >= ? and user_id = ? " \
            "order by time asc limit 1"
        db_manager.curs.execute(q, (cur_time_str, uid))
        resp = db_manager.curs.fetchone()
        if not resp:
            return None
        return resp[0]

    @staticmethod
    def get_random_word_by_uid(db_manager, uid: int):
        q = """select t1.word_from, t1.word_to from
               (
                 select word_from, word_to from word_src where user_id = ?
               ) as t1
               
               limit 1
               offset (abs(random()) % 
               (select count(*) from word_src where user_id = ?))"""
        db_manager.curs.execute(q, (uid, uid))
        return db_manager.curs.fetchone()


class DisconnectedDB(metaclass=DisconnectedDBMeta):
    """Class which represents disconnected database state"""

    @staticmethod
    def connect(db_manager):
        db_manager.new_state(ConnectedDB)
        db_manager.conn = sqlite3.connect(db_manager.path)
        db_manager.curs = db_manager.conn.cursor()


class DBManager:
    """Database class manager.

        Implemented as a state machine, each state is implemented
        in it's own class. Any operation on database is delegated to be
        executed by current state class.
    """
    def __init__(self, path):
        self.path = path
        self.conn = None
        self.curs = None
        self._state = None
        self.new_state(DisconnectedDB)

    def new_state(self, new_state):
        self._state = new_state

    def connect(self):
        self._state.connect(self)

    def disconnect(self):
        self._state.disconnect(self)

    def get_uids(self):
        return self._state.get_uids(self)

    def get_schedule_by_uid(self, uid: int) -> tuple:
        return self._state.get_schedule_by_uid(self, uid)

    def add_scheduled_time_by_uid(self, uid: int, time_string: str):
        self._state.add_scheduled_time_by_uid(self, uid, time_string)

    def delete_scheduled_time_by_uid(self, uid: int, time_string: str):
        return self._state.delete_scheduled_time_by_uid(self, uid, time_string)

    def get_next_time_by_uid(self, cur_time_str, uid):
        return self._state.get_next_time_by_uid(self, cur_time_str, uid)

    def is_registered(self, uid: int) -> bool:
        return self._state.is_registered(self, uid)

    def register(self, uid: int) -> None:
        self._state.register(self, uid)

    def get_all_words_by_uid(self, uid: int) -> tuple:
        return self._state.get_all_words_by_uid(self, uid)

    def get_random_word_by_uid(self, uid: int):
        return self._state.get_random_word_by_uid(self, uid)

    def add_words(self, uid: int, words: list):
        self._state.add_words(self, uid, words)


if __name__ == '__main__':
    db = DBManager('../source.db')
    db.connect()
    print(db.get_next_time_by_uid('00:00:00', 123456))
