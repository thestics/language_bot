#!/usr/bin/env python3
# -*-encoding: utf-8-*-

import re

from .constants import ENG_CHARS, RUS_CHARS



ENG_WORD = 1
RUS_WORD = 2


# TODO: probably line-wise parsing will cause problems for different users
# TODO: (not everyone use \n-s for separating different phrases)
# TODO: make an attempt to make parsing more general


class ParseException(Exception):
    pass


class UnrecognizedWordError(ParseException):
    pass


class InconsistentWordOrder(ParseException):
    pass


def _find_lang(word: str):
    """
    Performs an attempt to guess word language by comparing presented
    characters with given

    :param word:
    :return:
    """
    word = word.strip()
    rus_status = []
    eng_status = []
    for c in word:
        if c not in RUS_CHARS and c not in ENG_CHARS or \
                c in RUS_CHARS and c in ENG_CHARS:
            continue
        elif c in RUS_CHARS:
            rus_status.append(True)
            eng_status.append(False)
        elif c in ENG_CHARS:
            rus_status.append(False)
            eng_status.append(True)
    if all(rus_status):
        return RUS_WORD
    elif all(eng_status):
        return ENG_WORD
    else:
        return -1


# TODO: refactor!
def split_by_lang(row: str):
    """
    Performs an attempts to split row into two different languages

    (i.e "To ride for 'вписаться за'" -> ("To ride for", "вписаться за"))
    :param row: operated string
    :return: (['recognized pairs'], [unrecognized pairs])
    """
    marked_words = [(w, _find_lang(w)) for w in row.split()]
    prev_mark = marked_words[0][1]  # first mark as reference
    for i, data in enumerate(marked_words[1:]):
        w, mark = data
        if mark != prev_mark:
            left = next(zip(*marked_words[:i + 1]))
            right = next(zip(*marked_words[i + 1:]))
            return " ".join(left), " ".join(right)
    else:
        return row.strip(), ''


def parse(plain_text: str):
    plain_text = re.sub(" +", " ", plain_text)  # extra spaces removal
    plain_text = re.sub("[!?*'`_/]", "", plain_text)   # spec characters removal
    data_rows = plain_text.split("\n")
    processed_rows = []
    unprocessed_rows = []
    for row in data_rows:
        left, right = split_by_lang(row)
        if left and right:                      # if translation given
            processed_rows.append((left.lower(), right.lower()))
        else:
            unprocessed_rows.append((left.lower(), right.lower()))
    return processed_rows, unprocessed_rows


if __name__ == '__main__':
    data = """Dean
              Incredulously
              Inane
              Low-level baloney
              To shiver трястись
              To smart
              Fraudulent мошеннический
              To ride for 'вписаться за'
              Preliminary предварительный
              Aptly МЕТКО
              Dukes up поднять кулаки
              To entail conclusion заключать
              Premises предпосылки
              Ostensibly как будто бы
              Liable подлежащий
              To be caught on skimming быть пойманным на воровстве
              Man mane"""
    processed, unprocessed = parse(data)
    from pprint import pprint
    print("PROCESSED")
    pprint(processed)
    print("UNPROCESSED")
    pprint(unprocessed)
