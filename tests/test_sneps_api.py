"""Tests for sneps_wrapper.sneps_api.

The helper tests run anywhere. The SNePS tests need Linux and the bundled SNePS build (on 64-bit
systems: `sudo apt install libc6-i386`); set SNEPS_DIR to use a different SNePS folder.
Run from the repository root:  python -m unittest discover -s tests
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sneps_wrapper.sneps_api import (DEFAULT_DIRECTORY, SnepsContradictionError, SnepsProcessError,
                                     SnepsSyntaxError, _balanced, _error_text, _wffs, sneps_api)

SNEPS_DIR = os.environ.get("SNEPS_DIR", DEFAULT_DIRECTORY)


def sneps_runs():
    if not sys.platform.startswith("linux"):
        return False
    try:
        with sneps_api(directory=SNEPS_DIR, enable_logging=False):
            return True
    except Exception:
        return False


class HelperTest(unittest.TestCase):
    def test_balanced(self):
        self.assertTrue(_balanced("all(x)({a(x)} &=> {b(x)})"))
        self.assertFalse(_balanced("isa(c"))
        self.assertFalse(_balanced("a)("))

    def test_error_text_is_what_follows_error(self):
        # SNePS quotes the rest of the line, including its line break; whitespace is collapsed.
        self.assertEqual(_error_text('foo(x)!.\r\nError: Extra text in input: ".\r\n"\r\n\r\n'),
                         'Extra text in input: ". "')
        # "error" inside the echoed input is not the start of the message
        self.assertTrue(_error_text("terror(x) b(c).\r\nError: Wff not followed by terminal punctuation")
                        .startswith("Wff not followed"))

    def test_wffs_either_case_and_nothing_else(self):
        output = "ask(a(?x)).\r\n\r\n  wff2!:  a(c)    \r\n  WFF1!:  A(B)\r\n CPU time : 0.00 \r\n"
        self.assertEqual(_wffs(output), ["a(c)", "A(B)"])


@unittest.skipUnless(sneps_runs(), "needs Linux and a runnable SNePS build")
class SnepsTest(unittest.TestCase):
    def test_round_trip_without_changing_directory(self):
        cwd = os.getcwd()
        with sneps_api(directory=SNEPS_DIR, enable_logging=False) as api:
            self.assertTrue(api.inform("a(b)"))
            self.assertTrue(api.inform("a(c)."))  # an existing final '.' is not doubled
            self.assertEqual(sorted(api.ask("a(?x)")), ["a(b)", "a(c)"])
            self.assertEqual(os.getcwd(), cwd)
        self.assertIsNone(api.process)

    def test_rejected_statement_reports_snepss_message_and_the_session_continues(self):
        with sneps_api(directory=SNEPS_DIR, enable_logging=False) as api:
            with self.assertRaisesRegex(SnepsSyntaxError, "terminal punctuation"):
                api.inform("a(b) c(d)")
            with self.assertRaises(SnepsSyntaxError):
                api.inform("isa(c")  # unbalanced: refused before it reaches SNePS
            self.assertTrue(api.inform("a(d)"))
            self.assertEqual(api.ask("a(?x)"), ["a(d)"])

    def test_contradiction_is_discarded_and_the_session_continues(self):
        with sneps_api(directory=SNEPS_DIR, enable_logging=False, timeout=15) as api:
            api.inform("a(b)")
            with self.assertRaises(SnepsContradictionError):
                api.inform("~a(b)")
            self.assertEqual(api.ask("a(?x)"), ["a(b)"])

    def test_snepsul_error_returns_to_snepslog(self):
        with sneps_api(directory=SNEPS_DIR, enable_logging=False, timeout=15) as api:
            api.inform("a(b)")
            with self.assertRaisesRegex(SnepsSyntaxError, "car of 1"):
                api._command("^(car 1)")
            self.assertEqual(api.ask("a(?x)"), ["a(b)"])

    def test_statement_longer_than_a_terminal_line(self):
        rule = "all(x)({" + ", ".join(f"p{i}(x)" for i in range(600)) + "} &=> {q(x)})"
        self.assertGreater(len(rule), 4096)
        with sneps_api(directory=SNEPS_DIR, enable_logging=False, timeout=30) as api:
            self.assertTrue(api.inform(rule))

    def test_timeout_stops_the_session(self):
        with sneps_api(directory=SNEPS_DIR, enable_logging=False, timeout=1) as api:
            with self.assertRaises(SnepsProcessError):
                api._command("^(sleep 3)")
            self.assertIsNone(api.process)


@unittest.skipUnless(sneps_runs(), "needs Linux and a runnable SNePS build")
class EndToEndTest(unittest.TestCase):
    def test_english_rule_fires_only_for_the_matching_person(self):  # issues #4, #6, #7
        try:
            from semantic_parser.core import snepslog
            engine = snepslog()
        except Exception as e:
            self.skipTest(f"needs spaCy with en_core_web_trf ({e})")
        with sneps_api(directory=SNEPS_DIR, enable_logging=False, timeout=120) as api:
            for sentence in ["person person_1 is in front of car car_1.", "person person_2 is behind car car_1.",
                             "Every person that is in front of a car is in danger."]:
                api.inform(engine.transcribe(sentence))
            derived = lambda person: [a for a in api.ask(f"reference(?s, {person})") if "({" in a]
            self.assertEqual(len(derived("person_1")), 1)
            self.assertEqual(derived("person_2"), [])


if __name__ == "__main__":
    unittest.main()
