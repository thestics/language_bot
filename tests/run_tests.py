#!/usr/bin/env python3
# -*-encoding: utf-8-*-


from language_bot_core.tests import test_language_core
from telegram_language_bot.tests import test_bot_front


test_language_core('../language_bot_core/tests/test_db.db')
test_bot_front()
