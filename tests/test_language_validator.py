import unittest

from validators.language_validator import (
    LanguageValidationError,
    enforce_campaign_language_quality,
    enforce_language_quality,
    validate_campaign_language_quality,
    validate_language_quality,
)


class LanguageValidatorTests(
    unittest.TestCase
):

    def test_valid_arabic_passes(self):

        result = validate_language_quality(
            (
                "أصبحت 7 خدمات تابعة لوزارة الزراعة "
                "متاحة الآن إلكترونياً عبر منصة «دولتي»."
            ),
            "Arabic"
        )

        self.assertTrue(
            result[
                "valid"
            ]
        )


    def test_bad_dawlati_arabic_structure_is_blocked(self):

        result = validate_language_quality(
            (
                "منصة «دولتي» تُعَدُّ الآن "
                "7 خدمات حكومية لقطاع الزراعة."
            ),
            "Arabic"
        )

        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_nonsensical_arabic_phrase_is_blocked(self):

        result = validate_language_quality(
            (
                "منصة «دولتي» هي خيارًا "
                "مُثَلَّثًا للخدمات الحكومية."
            ),
            "Arabic"
        )

        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_english_in_arabic_field_is_blocked(self):

        result = validate_language_quality(
            (
                "Seven government services are "
                "available online through Dawlati."
            ),
            "Arabic"
        )

        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_valid_english_passes(self):

        result = validate_language_quality(
            (
                "Seven Ministry of Agriculture services "
                "are now available online through Dawlati."
            ),
            "English"
        )

        self.assertTrue(
            result[
                "valid"
            ]
        )


    def test_arabic_in_english_field_is_blocked(self):

        result = validate_language_quality(
            (
                "أصبحت سبع خدمات حكومية "
                "متاحة عبر منصة دولتي."
            ),
            "English"
        )

        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_enforcement_raises_exception(self):

        with self.assertRaises(
            LanguageValidationError
        ):

            enforce_language_quality(
                (
                    "منصة «دولتي» تُعَدُّ الآن "
                    "7 خدمات حكومية."
                ),
                "Arabic"
            )


    def test_full_campaign_passes(self):

        content = {
            "caption_ar": (
                "أصبحت 7 خدمات تابعة لوزارة الزراعة "
                "متاحة الآن إلكترونياً عبر منصة «دولتي»."
            ),

            "caption_en": (
                "Seven Ministry of Agriculture services "
                "are now available online through Dawlati."
            ),

            "content_structure": [
                {
                    "headline": (
                        "7 Ministry of Agriculture Services"
                    ),

                    "body": (
                        "The services are now available "
                        "online through Dawlati."
                    )
                }
            ],

            "cta": (
                "Explore the 7 available services on Dawlati"
            ),

            "visual_concept": (
                "A clear public-sector carousel announcing "
                "seven Ministry of Agriculture services."
            ),

            "visual_generation_prompt": (
                "Create a professional government-services "
                "carousel with clear information hierarchy."
            ),
        }


        result = validate_campaign_language_quality(
            content,
            [
                "Arabic",
                "English"
            ]
        )


        self.assertTrue(
            result[
                "valid"
            ]
        )


    def test_bad_carousel_slide_is_blocked(self):

        content = {
            "caption_ar": (
                "أصبحت 7 خدمات تابعة لوزارة الزراعة "
                "متاحة الآن إلكترونياً عبر منصة «دولتي»."
            ),

            "caption_en": (
                "Seven Ministry of Agriculture services "
                "are now available online through Dawlati."
            ),

            "content_structure": [
                {
                    "headline": (
                        "خدمات وزارة الزراعة"
                    ),

                    "body": (
                        "منصة «دولتي» تُعَدُّ الآن "
                        "7 خدمات حكومية."
                    )
                }
            ],

            "cta": (
                "Explore the available services"
            ),

            "visual_concept": (
                "Professional government-service carousel."
            ),

            "visual_generation_prompt": (
                "Create a clean government-service carousel."
            ),
        }


        result = validate_campaign_language_quality(
            content,
            [
                "Arabic",
                "English"
            ]
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_bad_cta_is_blocked(self):

        content = {
            "caption_ar": (
                "أصبحت 7 خدمات تابعة لوزارة الزراعة "
                "متاحة الآن إلكترونياً عبر منصة «دولتي»."
            ),

            "caption_en": (
                "Seven Ministry of Agriculture services "
                "are now available online through Dawlati."
            ),

            "content_structure": [],

            "cta": (
                "Dawlati is 7 services"
            ),

            "visual_concept": (
                "Professional public-sector announcement."
            ),

            "visual_generation_prompt": (
                "Create a professional government carousel."
            ),
        }


        result = validate_campaign_language_quality(
            content,
            [
                "Arabic",
                "English"
            ]
        )


        self.assertFalse(
            result[
                "valid"
            ]
        )


    def test_campaign_enforcement_raises_exception(self):

        content = {
            "caption_ar": (
                "منصة «دولتي» تُعَدُّ الآن "
                "7 خدمات حكومية."
            ),

            "caption_en": (
                "Seven services are available through Dawlati."
            ),

            "content_structure": [],

            "cta": (
                "Explore the services"
            ),

            "visual_concept": (
                "Government-service announcement."
            ),

            "visual_generation_prompt": (
                "Create a professional carousel."
            ),
        }


        with self.assertRaises(
            LanguageValidationError
        ):

            enforce_campaign_language_quality(
                content,
                [
                    "Arabic",
                    "English"
                ]
            )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
    