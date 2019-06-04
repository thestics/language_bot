#!/usr/bin/env python3
# -*-encoding: utf-8-*-


import unittest
import language_bot_core


class DBManagerTester(unittest.TestCase):

    def __init__(self, db_path, method_name='runTest'):
        self.data = language_bot_core.DBManager(db_path)
        self.data.connect()
        super().__init__(method_name)

    def test_connected_state(self):
        self.assertIs(self.data._state,
                      language_bot_core.dbmanager.ConnectedDB,
                      "Incorrect state change after connection: "
                      "(Expected connected state)")
        with self.assertRaises(language_bot_core.dbmanager.
                               ConnectedDatabaseError):
            self.data.connect()

    def test_disconnected_state(self):
        self.data.disconnect()
        self.assertIs(self.data._state,
                      language_bot_core.dbmanager.DisconnectedDB,
                      "Incorrect state after disconnection: "
                      "(Expected disconnected state)")
        with self.assertRaises(language_bot_core.dbmanager.
                               DisconnectedDatabaseError):
            self.data.get_uids()
        self.data.connect()

    def test_get_uids(self):
        expected = [123456, 654321, 347698, 827569]
        retrieved = self.data.get_uids()
        self.assertEqual(expected, retrieved, "Incorrect user id return")

    def test_get_schedule_by_uid(self):
        uid1 = 123456
        uid2 = 654321
        expected1 = ['12:31:24','13:22:00','13:23:00']
        expected2 = ['00:00:00','00:01:00']
        retrieved1 = self.data.get_schedule_by_uid(uid1)
        retrieved2 = self.data.get_schedule_by_uid(uid2)
        self.assertEqual(expected1, retrieved1)
        self.assertEqual(expected2, retrieved2)

    def test_get_next_time_by_uid(self):
        time_str1 = "12:00:00"
        time_str2 = "12:40:00"
        time_str3 = "23:59:59"
        time_str_list = [time_str1, time_str2, time_str3]
        retrieved_list = [self.data.get_next_time_by_uid(cur, 123456)
                          for cur in time_str_list]
        self.assertEqual(retrieved_list[0], "12:31:24")
        self.assertEqual(retrieved_list[1], "13:22:00")
        self.assertIsNone(retrieved_list[2])

    def test_is_registered(self):
        status1 = self.data.is_registered(123456)
        status2 = self.data.is_registered(101000)
        self.assertTrue(status1)
        self.assertFalse(status2)

    def test_register(self):
        new_id = 999999
        q = "select user_id from user_ids where user_id=?"
        self.data.register(new_id)

        # it would be more convenient to use is_registered method of db manager
        # but i'd like to keep test cases isolated from each other
        # (is_registered may throw an exception in test case which intended
        # to test totally different method)
        self.data.curs.execute(q, (new_id,))
        res = self.data.curs.fetchall()
        self.assertTrue(res)
        q = "delete from user_ids where user_id=?"
        self.data.curs.execute(q, (new_id,))
        self.data.conn.commit()

    def test_get_all_words_by_uid(self):
        uid1 = 123456
        expected = [('word1_f', 'word1_t'), ('word2_f', 'word2_t')]
        retrieved = self.data.get_all_words_by_uid(uid1)
        self.assertEqual(expected, retrieved)

    def test_add_words(self):
        expected = [('__w1f__', '__w1t__'), ('__w2f__', '__w2t__')]
        self.data.add_words(999999, expected)
        q = """select word_from, word_to from word_src where user_id=999999"""
        self.data.curs.execute(q)
        received = self.data.curs.fetchall()
        self.assertEqual(expected, received)
        q = """delete from word_src where user_id=999999"""
        self.data.curs.execute(q)
        self.data.conn.commit()

    def test_add_schedule_time_by_uid(self):
        self.data.add_scheduled_time_by_uid(123456, '99:99:99')
        q = """select time from schedule where time='99:99:99'"""
        self.data.curs.execute(q)
        self.assertTrue(self.data.curs.fetchall())
        q = """delete from schedule where time='99:99:99'"""
        self.data.curs.execute(q)
        self.data.conn.commit()


class DispatcherTester(unittest.TestCase):
    pass


class ParserTester(unittest.TestCase):
    pass
