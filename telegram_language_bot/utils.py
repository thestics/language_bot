#!/usr/bin/env python3
# -*-encoding: utf-8-*-


from threading import RLock


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
            # it will wait here until release it's release
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
