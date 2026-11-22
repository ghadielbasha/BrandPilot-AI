import unittest

from validators.terminology_validator import (
    TerminologyValidationError,
    enforce_terminology,
    validate_terminology,
    normalize_terminology,
    correct_global_terminology,
    normalize_global_terminology,
)


class TerminologyValidatorTests(unittest.TestCase):

    def test_correct_dawlati_arabic_passes(self):

        result = validate_terminology(
            "اكتشف الخدمات عبر منصة «دولتي».",
            "dawlati"
        )

        self.assertTrue(
            result["valid"]
        )

        self.assertEqual(
            result["status"],
            "PASS"
        )

    def test_correct_dawlati_english_passes(self):

        result = validate_terminology(
            "Discover services through DAWLATI.",
            "dawlati"
        )

        self.assertTrue(
            result["valid"]
        )

    def test_dawlaty_variant_is_blocked(self):

        result = validate_terminology(
            "اكتشف الخدمات عبر داولاتي.",
            "dawlati"
        )

        self.assertFalse(
            result["valid"]
        )

        self.assertEqual(
            result["status"],
            "BLOCK"
        )

    def test_dwalti_variant_is_blocked(self):

        result = validate_terminology(
            "اكتشف الخدمات عبر دوالتي.",
            "dawlati"
        )

        self.assertFalse(
            result["valid"]
        )

    def test_dawalti_variant_is_blocked(self):

        result = validate_terminology(
            "اكتشف الخدمات عبر داولتي.",
            "dawlati"
        )

        self.assertFalse(
            result["valid"]
        )

    def test_diacritic_variant_is_blocked(self):

        result = validate_terminology(
            "اكتشف الخدمات عبر دَولتي.",
            "dawlati"
        )

        self.assertFalse(
            result["valid"]
        )

    def test_enforcement_raises_exception(self):

        with self.assertRaises(
            TerminologyValidationError
        ):
            enforce_terminology(
                "اكتشف الخدمات عبر داولاتي.",
                "dawlati"
            )

    def test_matchmaking_misspellings_are_normalized_then_pass(self):
        for incorrect in ("Matcha" + "making", "Matcha" + "matching"):
            with self.subTest(incorrect=incorrect):
                blocked = validate_terminology(incorrect, "omsar")
                self.assertEqual(blocked["status"], "BLOCK")
                normalized = normalize_terminology(incorrect, "omsar")
                self.assertEqual(normalized["text"], "Matchmaking")
                self.assertEqual(
                    validate_terminology(normalized["text"], "omsar")["status"],
                    "PASS",
                )

    def test_legacy_global_normalizer_delegates_to_canonical_function(self):
        incorrect = "Matcha" + "matching"
        self.assertEqual(
            correct_global_terminology(incorrect),
            normalize_global_terminology(incorrect),
        )
        self.assertEqual(normalize_global_terminology(incorrect), "Matchmaking")


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
