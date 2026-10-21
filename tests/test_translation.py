"""Regression tests for the English -> SNePSLOG translator.

Run from the repository root:  python -m unittest discover -s tests
They need spaCy and en_core_web_trf, and are skipped without them.
"""
import re
import sys
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import spacy
    spacy.load("en_core_web_trf")
    HAVE_MODEL = True
except Exception:
    HAVE_MODEL = False


@unittest.skipUnless(HAVE_MODEL, "needs spaCy with en_core_web_trf")
class TranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from semantic_parser.core import snepslog
        cls.engine = snepslog()

    def transcribe(self, sentence):
        return self.engine.transcribe(sentence)

    def test_identifiers_are_kept_and_named_consistently(self):  # issue #4
        self.assertEqual(self.transcribe("car_1 is below car_8").count("car_8"), 1)
        out = self.transcribe("car_1 is completely to the right of person_1")
        self.assertIn("reference(", out)
        self.assertRegex(out, r"reference\(\w+, car_1\)")
        self.assertIn("person_1)", out)

    def test_untranslatable_parts_raise_a_warning_not_a_print(self):  # issue #4
        import contextlib
        import io
        from nlp_utils.spaCy_helpers import TranscriptionWarning
        stdout = io.StringIO()
        with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(stdout):
            warnings.simplefilter("always")
            self.transcribe("Two boys like the cat.")  # the number modifier "two" is not translated
        self.assertTrue(any(issubclass(w.category, TranscriptionWarning) for w in caught))
        self.assertEqual(stdout.getvalue(), "")

    def test_adverb_does_not_hide_the_prepositional_object(self):  # issue #5
        left = self.transcribe("person_1 is completely to the left of car_1")
        right = self.transcribe("person_1 is completely to the right of car_1")
        self.assertRegex(left, r"left\(\w+\)")
        self.assertRegex(right, r"right\(\w+\)")
        self.assertIn("car_1)", left)
        self.assertRegex(left, r"completely\(s\w+\)")

    def test_sentences_get_their_own_constants(self):  # issue #6
        first = self.transcribe("person_1 is in front of car_1")
        second = self.transcribe("person_2 is in front of car_1")
        state = lambda out: re.search(r"state\((\w+)\)", out).group(1)
        self.assertNotEqual(state(first), state(second))
        self.assertNotEqual(re.search(r"front\((\w+)\)", first).group(1), re.search(r"front\((\w+)\)", second).group(1))

    def test_rule_condition_goes_into_the_antecedent(self):  # issue #7
        rule = self.transcribe("Every person that is in front of a car is in danger.")
        antecedent, consequent = rule.split("&=>")
        for atom in ("person(", "in(", "front(", "of(", "car("):
            self.assertIn(atom, antecedent)
        self.assertIn("danger(", consequent)
        self.assertNotIn("concerns(", rule)
        variables = re.match(r"all\(([^)]*)\)", rule).group(1).split(", ")
        self.assertEqual(len(variables), 4)  # the person, the clause's state, "front", "a car"

    def test_iff_right_hand_side_is_parenthesised(self):  # issue #8
        rule = self.transcribe("The persons behind a car are in danger.")
        self.assertRegex(rule, r"<=> \(")

    def test_nested_prepositional_object_keeps_its_own_reference(self):  # issue #8
        rule = self.transcribe("Every person in front of a car is in danger.")
        front = re.search(r"front\((\w+)\)", rule).group(1)
        self.assertRegex(rule, rf"of\({front}, \w+\)")

    def test_ground_statements_are_conjunctions(self):  # issue #9
        self.assertNotIn(" or ", self.transcribe("person person_1 is a person."))
        self.assertNotIn(" or ", self.transcribe("The boy likes the cat and the dog."))

    def test_preposition_without_children_does_not_crash(self):  # issue #10
        self.assertTrue(self.transcribe("person_1 is below stop sign_1"))


if __name__ == "__main__":
    unittest.main()
