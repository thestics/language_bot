#!/usr/bin/env python3
# -*-encoding: utf-8-*-


TOKEN = "858148579:AAGRbz8Y_xa0RrdPL45lsPiB--rrT3MwiAU"
DB_PATH = "source.db"
GREETING_MSG = "You was successfully registered!"
WORDS_UPLOAD_MSG = "For uploading words it is enough to copy your stored\n" \
                   "data here in the following format:\n\n" \
                   "<some word> <definition>\n" \
                   "<again word> <it's own definition>\n\n" \
                   "For example:\n" \
                   "To shiver трястись\n"\
                   "To smart\n"\
                   "Fraudulent мошеннический\n"\
                   "To ride for 'вписаться за'\n"\
                   "Preliminary предварительный\n"\
                   "Aptly МЕТКО\n"\
                   "Dukes up поднять кулаки\n\n"\
                   "Bot will try to separate your note in a \n"\
                   "list of <word>-<translation> and on scheduled\n"\
                   "time will send you a message to ask you for "\
                   "translation\n\n"\
                   "NOTE [0]: all non-alphabetic characters will be skipped\n"\
                   "NOTE [1]: currently supported languages: " \
                              "Russian, English\n"\
                   "NOTE [2]: lines without translation " \
                              "(like 1st) will be skipped (for now) \n"\
                   "NOTE [3]: for now, you are supposed to separate your data "\
                   "with newlines."

COMMANDS = {
            'start': 'start fun',
            'info': 'show full info on available commands',
            'upload_info': 'detailed info about uploading words',
            'next_word:': 'force next word',
            'reveal_last': 'show translation for last word and skip it',
            'show_words': 'show full list of uploaded words',
            'add_time': 'add time to schedule 00:00:00 - 23:59:59',
            'add_words': 'add words',
            'schedule': 'list your timetable for questions'
            }
