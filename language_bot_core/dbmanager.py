import sqlite3


class ConnectedDB:
    """Class which represents connected database state"""

    @staticmethod
    def connect(db_manager):
        raise RuntimeError("Already connected")

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
    def get_words_by_uid(db_manager, uid):
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
    def add_words(db_manager, uid: int, words: list):
        q = "insert into word_src values (?, ?, ?, ?)"
        for word_from, word_to in words:
            db_manager.curs.execute(q, (uid, word_from, word_to, 0))
        db_manager.conn.commit()

class DisconnectedDB:
    """Class which represents disconnected database state"""

    @staticmethod
    def connect(db_manager):
        db_manager.new_state(ConnectedDB)
        db_manager.conn = sqlite3.connect(db_manager.path)
        db_manager.curs = db_manager.conn.cursor()

    @staticmethod
    def disconnect(db_manager):
        raise RuntimeError("Already disconnected")

    @staticmethod
    def get_uids(db_manager):
        raise RuntimeError("Cannot perform queries on closed database")

    @staticmethod
    def get_schedule_by_uid(db_manager, uid):
        raise RuntimeError("Cannot perform queries on closed database")

    @staticmethod
    def is_registered(db_manager, uid):
        raise RuntimeError("Cannot perform queries on closed database")

    @staticmethod
    def register(db_manager, uid):
        raise RuntimeError("Cannot perform queries on closed database")

    @staticmethod
    def get_words_by_uid(db_manager, uid):
        raise RuntimeError("Cannot perform queries on closed database")

    @staticmethod
    def add_scheduled_time_by_uid(db_manager, uid: int, time_string: str):
        raise RuntimeError("Cannot perform queries on closed database")

    @staticmethod
    def add_words(db_manager, uid: int, words: list):
        raise RuntimeError("Cannot perform queries on closed database")


class DBManager:

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

    # TODO: intensive calls expected, needs to be optimized
    def get_next_time_by_uid(self, cur_time_str, uid):
        schedule = self.get_schedule_by_uid(uid)
        if not schedule:
            return None
        for i, time_str in enumerate(sorted(schedule)):
            if time_str > cur_time_str:
                return schedule[i]
        return None

    def is_registered(self, uid: int) -> bool:
        return self._state.is_registered(self, uid)

    def register(self, uid: int) -> None:
        self._state.register(self, uid)

    # TODO: probably it is more convenient to make separate method for
    # TODO: getting random word rather then extracting entire dictionary
    # TODO: and work with it
    def get_words_by_uid(self, uid: int) -> tuple:
        return self._state.get_words_by_uid(self, uid)

    def add_words(self, uid: int, words: list):
        self._state.add_words(self, uid, words)
