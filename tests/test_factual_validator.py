import unittest

from validators.factual_validator import (
    FactualValidationError,
    enforce_factual_claims,
    validate_factual_claims,
)


class FactualValidatorTests(
    unittest.TestCase
):

    def setUp(self):

        self.brief = (
            "Seven Ministry of Agriculture services "
            "are now available online through Dawlati."
        )


    def test_safe_content_passes(self):

        result = validate_factual_claims(
            self.brief,
            (
                "7 Ministry of Agriculture services "
                "are now available online through Dawlati."
            )
        )


        self.assertTrue(
            result[
                "valid"
            ]
        )


        self.assertEqual(
            result[
                "status"
            ],
            "PASS"
        )

    def test_now_available_online_is_not_continuous_availability(self):
        result = validate_factual_claims(
            self.brief,
            "Seven services are now available online through Dawlati.",
        )
        self.assertEqual(result["status"], "PASS")

    def test_available_online_is_not_continuous_availability(self):
        result = validate_factual_claims(
            "The services are available online.",
            "The services are available online.",
        )
        self.assertEqual(result["status"], "PASS")

    def test_arabic_now_electronically_available_is_not_continuous(self):
        text = "أصبحت 7 خدمات متاحة الآن إلكترونياً عبر منصة دولتي."
        result = validate_factual_claims(text, text)
        self.assertEqual(result["status"], "PASS")

    def test_available_24_7_is_continuous_availability(self):
        result = validate_factual_claims(
            "Services are available online.",
            "Services are available 24/7.",
        )
        self.assertEqual(result["status"], "BLOCK")

    def test_available_anytime_is_continuous_availability(self):
        result = validate_factual_claims(
            "Services are available online.",
            "Services are available anytime.",
        )
        self.assertEqual(result["status"], "BLOCK")

    def test_always_available_is_continuous_availability(self):
        result = validate_factual_claims(
            "Services are available online.",
            "Services are always available.",
        )
        self.assertEqual(result["status"], "BLOCK")

    def test_arabic_around_the_clock_is_continuous_availability(self):
        result = validate_factual_claims(
            "الخدمات متاحة إلكترونياً.",
            "الخدمات متاحة على مدار الساعة.",
        )
        self.assertEqual(result["status"], "BLOCK")

    def test_arabic_always_available_is_continuous_availability(self):
        result = validate_factual_claims(
            "الخدمات متاحة إلكترونياً.",
            "الخدمات متاحة دائماً.",
        )
        self.assertEqual(result["status"], "BLOCK")


    def test_application_claim_is_blocked(self):

        result = validate_factual_claims(
            self.brief,
            (
                "7 services are available online. "
                "Start your application through Dawlati."
            )
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_arabic_application_claim_is_blocked(self):

        result = validate_factual_claims(
            self.brief,
            (
                "أصبحت 7 خدمات متاحة إلكترونياً عبر دولتي. "
                "ابدأ بطلبك عبر دولتي."
            )
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_24_7_claim_is_blocked(self):

        result = validate_factual_claims(
            self.brief,
            (
                "7 services are available "
                "through Dawlati 24/7."
            )
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_efficiency_claim_is_blocked(self):

        result = validate_factual_claims(
            self.brief,
            (
                "أصبحت 7 خدمات متاحة عبر دولتي "
                "لتحقيق كفاءة في الإجراءات الحكومية."
            )
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_ease_claim_is_blocked(self):

        result = validate_factual_claims(
            self.brief,
            (
                "أصبحت 7 خدمات متاحة إلكترونياً "
                "عبر منصة دولتي للاستفادة منها بسهولة."
            )
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_missing_number_is_blocked(self):

        result = validate_factual_claims(
            self.brief,
            (
                "Ministry of Agriculture services "
                "are now available online through Dawlati."
            )
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


        self.assertIn(
            "7",
            result[
                "brief_numbers"
            ]
        )


    def test_number_word_matches_digit(self):

        result = validate_factual_claims(
            self.brief,
            (
                "7 Ministry of Agriculture services "
                "are now available online through Dawlati."
            )
        )


        self.assertEqual(
            result[
                "brief_numbers"
            ],
            [
                "7"
            ]
        )


        self.assertIn(
            "7",
            result[
                "generated_numbers"
            ]
        )


    def test_arabic_number_word_matches_digit(self):

        result = validate_factual_claims(
            "سبع خدمات حكومية متاحة عبر دولتي.",
            "7 خدمات حكومية متاحة عبر دولتي."
        )


        self.assertTrue(
            result[
                "valid"
            ]
        )


    def test_enforcement_raises_exception(self):

        with self.assertRaises(
            FactualValidationError
        ):

            enforce_factual_claims(
                self.brief,
                (
                    "7 services are available online. "
                    "Start your application through Dawlati."
                )
            )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
    
