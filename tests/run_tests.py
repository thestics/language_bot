#!/usr/bin/env python3
# -*-encoding: utf-8-*-



from language_bot_core.tests import test_bot_core
from telegram_language_bot.tests import test_bot_front


def run_tests():
    test_bot_core()
    test_bot_front()
