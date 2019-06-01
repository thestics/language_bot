from threading import Lock


class WordsBuffer:
    """
    Dictionary wrapper class for safe usage from different threads
    """
    def __init__(self):
        self.data = {}

        # lock object to avoid simultaneous modifying from different threads
        self.lock = Lock()

    def _wrap(self, f):
        """
        Decorator for non-magic methods of dict
        """

        def new_f(*args, **kwargs):

            # if was acquired by a different thread
            # it will wait here until release it's release
            self.lock.acquire()
            try:
                res = f(*args, **kwargs)
                return res
            finally:
                self.lock.release()

        return new_f

    def __getitem__(self, item):
        self.lock.acquire()
        try:
            return self.data.__getitem__(item)
        finally:
            self.lock.release()

    def __setitem__(self, key, value):
        self.lock.acquire()
        try:
            self.data.__setitem__(key, value)
        finally:
            self.lock.release()

    def __delitem__(self, key):
        self.lock.acquire()
        try:
            self.data.__delitem__(key)
        finally:
            self.lock.release()

    def __getattr__(self, name):
        """
        Wrapper for non-magic methods calls (magic methods are not called
        via any handler, so they have to be redefined explicitly)

        :param name: param name
        :return:
        """
        cur = self.data.__getattribute__(name)
        return self._wrap(cur)
