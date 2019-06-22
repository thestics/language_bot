#!/usr/bin/env python3
# -*-encoding: utf-8-*-


from threading import RLock
from language_bot_core import DBManager
import datetime


class SchedulerException(Exception):
    pass


class SchedulerPresetTypeHelperError(SchedulerException):
    pass


class ThreadedDict:
    """
    Dictionary wrapper class for safe usage from different threads
    """
    def __init__(self):
        self.data = {}

        # lock object to avoid simultaneous modifying from different threads
        self.lock = RLock()

    def _wrap(self, f):
        """
        Decorator for non-magic methods of dict
        """

        def new_f(*args, **kwargs):

            # if was acquired by a different thread
            # the new one will wait here until it is released
            with self.lock:
                res = f(*args, **kwargs)
                return res

        return new_f

    def __getitem__(self, item):
        with self.lock:
            return self.data.__getitem__(item)

    def __setitem__(self, key, value):
        with self.lock:
            self.data.__setitem__(key, value)

    def __delitem__(self, key):
        with self.lock:
            self.data.__delitem__(key)

    def __contains__(self, item):
        with self.lock:
            return self.data.__contains__(item)

    def __getattr__(self, name):
        """
        Wrapper for non-magic methods calls (magic methods are not called
        via any handler, so they have to be redefined explicitly)

        :param name: param name
        :return:
        """
        cur = self.data.__getattribute__(name)
        return self._wrap(cur)


class ArithmeticTime(datetime.time):
    """time class intended to support arithmetic operations and to
    utilize already implemented datetime.time class functionality
    """

    def _normalize_time(self, hh, mm, ss):
        h = hh
        m = mm
        s = ss

        if s % 60 != s:
            m += s // 60
            s %= 60

        if m % 60 != m:
            h += m // 60
            m %= 60

        if h % 24 != h:
            h %= 24
        return h, m, s

    def __add__(self, other: datetime.time):
        h = self.hour + other.hour
        m = self.minute + other.minute
        s = self.second + other.second
        h, m, s = self._normalize_time(h, m, s)
        res = ArithmeticTime(h, m, s)
        return res

    def __sub__(self, other):
        h = abs(self.hour - other.hour)
        m = abs(self.minute - other.minute)
        s = abs(self.second - other.second)
        h, m, s = self._normalize_time(h, m, s)
        return ArithmeticTime(h, m, s)

    def __mul__(self, other):
        if isinstance(other, int):
            h = self.hour * other
            m = self.minute * other
            s = self.second * other
            h, m, s = self._normalize_time(h, m, s)
            return ArithmeticTime(h, m, s)
        else:
            raise NotImplementedError("Only integer factor allowed")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        left_sec = self.second + self.minute * 60 + self.hour * 3600
        right_sec = other.second + other.minute * 60 + other.hour * 3600
        return left_sec // right_sec


time = ArithmeticTime


class SchedulerBase:
    """Base class for time scheduling

    """

    def __init__(self, db_manager: DBManager, uid: int):
        self.db_manager = db_manager
        self.uid = uid
        self.db_manager.connect()

    def add_time(self, time_str):
        if self._is_valid_time_string(time_str):
            self.db_manager.add_scheduled_time_by_uid(self.uid, time_str)
        else:
            raise SchedulerException('Incorrect '
                                     'time string: {}'.format(time_str))

    def add_times(self, time_str_list: list):
        for time_str in time_str_list:
            self.add_time(time_str)

    def delete_time(self, time_str):
        self.db_manager.delete_scheduled_time_by_uid(self.uid, time_str)

    def clear_schedule(self):
        for time_str in self.get_schedule():
            self.delete_time(time_str)

    def get_schedule(self):
        return self.db_manager.get_schedule_by_uid(self.uid)

    def _is_valid_time_string(self, time_str: str) -> bool:
        try:
            hh, mm, ss = time_str.split(':')
            hh, mm, ss = int(hh), int(mm), int(ss)
            if not 0 <= hh <= 23 \
                    or not 0 <= mm <= 59 \
                    or not 0 <= mm <= 59:
                raise ValueError
        except ValueError:
            return False
        return True


class Scheduler(SchedulerBase):

    allowed_preset_types = (1, 2, 3)

    def add_time_from_preset(self, preset_type, min_time_str, max_time_str):
        """
        Rebuilds user time schedule according to given preset type and time
        range.

        :param preset_type: preset_types = {
                                0: 'Every half an hour',
                                1: 'Every hour',
                                2: 'Every two hours',
                            }
        :param min_time_str:
        :param max_time_str:
        :return:
        """
        self.clear_schedule()
        if preset_type not in self.allowed_preset_types:
            raise SchedulerException('Incorrect preset type.')
        else:
            attr_name = "_handle_type{}_preset".format(preset_type)
            schedule_gen_method = getattr(self, attr_name, lambda *x: None)
            schedule = schedule_gen_method(min_time_str, max_time_str)
            if schedule is None:
                raise SchedulerPresetTypeHelperError('An error occurred while'
                                                     'handling preset type')
        self.clear_schedule()
        return schedule
        # self.add_times(schedule)

    def _handle_type1_preset(self, min_time_str, max_time_str) -> list:
        """
        Build type one (one msg per half an hour) time schedule preset
        in given time range

        :param min_time_str:
        :param max_time_str:
        :return:
        """
        delta_time_str = "00:30:00"
        return self.base_preset_handler(min_time_str,
                                        max_time_str,
                                        delta_time_str)

    def _handle_type2_preset(self, min_time_str, max_time_str) -> list:
        """
        Build type two (one msg per hour) time schedule preset
        in given time range

        :param min_time_str:
        :param max_time_str:
        :return:
        """
        delta_time_str = "01:00:00"
        return self.base_preset_handler(min_time_str,
                                        max_time_str,
                                        delta_time_str)

    def _handle_type3_preset(self, min_time_str, max_time_str) -> list:
        """
        Build type one (one msg per two hours) time schedule preset
        in given time range

        :param min_time_str:
        :param max_time_str:
        :return:
        """
        delta_time_str = "02:00:00"
        return self.base_preset_handler(min_time_str,
                                        max_time_str,
                                        delta_time_str)

    def base_preset_handler(self, min_time_str, max_time_str, delta_time_str):
        start = time.fromisoformat(min_time_str)
        stop = time.fromisoformat(max_time_str)
        delta = time.fromisoformat(delta_time_str)
        return [start + i * delta for i in range((start - stop)/delta)]


