import unittest

from validators.terminology_validator import (
    TerminologyValidationError,
    enforce_terminology,
    validate_terminology,
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


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )