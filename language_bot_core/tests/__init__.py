#!/usr/bin/env python3
# -*-encoding: utf-8-*-


from itertools import product
import unittest

from .tests import DBManagerTester, DispatcherTester, ParserTester


def test_language_core(db_path):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # very verbose way to add parameters to test case class constructor
    # but I haven't found any better approach for this task yet
    db_test_cases_names = loader.getTestCaseNames(DBManagerTester)
    params = product((db_path, ), db_test_cases_names)
    tests = [DBManagerTester(p1, p2) for p1, p2 in params]
    suite.addTests(tests)

    suite.addTest(loader.loadTestsFromTestCase(DispatcherTester))
    suite.addTest(loader.loadTestsFromTestCase(ParserTester))

    test_runner = unittest.TextTestRunner(verbosity=2)
    test_runner.run(suite)


__all__ = ['test_language_core']
