import unittest
from unittest.mock import patch

from content_generator import (
    MarketingContent,
    ContentItem,
    BrandCheck,
    build_content_prompt,
    generate_marketing_content,
)


class ContentGeneratorRepairTests(
    unittest.TestCase
):

    def setUp(self):

        self.brief = (
            "Seven Ministry of Agriculture services "
            "are now available online through Dawlati."
        )

        self.strategy = {
            "brand_key": "dawlati",
            "brand": "DAWLATI",
            "objective": "Service Adoption",

            "target_audience": [
                "Farmers",
                "Producers",
                "Agricultural businesses",
            ],

            "platform": "Instagram",

            "languages": [
                "Arabic",
                "English",
            ],

            "tone": [
                "Informative",
                "Clear",
                "Benefit-focused",
            ],

            "recommended_format": "Carousel",

            "campaign_angle": (
                "Announce that 7 Ministry of Agriculture "
                "services are now available online through "
                "Dawlati and encourage farmers, producers, "
                "and agricultural businesses to explore "
                "the available services."
            ),

            "cta": (
                "Explore the 7 available services on Dawlati"
            ),
        }


    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _valid_content(self):

        return MarketingContent(
            caption_ar=(
                "أصبحت 7 خدمات تابعة لوزارة الزراعة "
                "متاحة الآن إلكترونياً عبر منصة «دولتي»."
            ),

            caption_en=(
                "Seven Ministry of Agriculture services "
                "are now available online through Dawlati."
            ),

            content_structure=[
                ContentItem(
                    number=1,
                    type="Slide",
                    headline=(
                        "7 Ministry of Agriculture Services"
                    ),
                    body=(
                        "Seven Ministry of Agriculture "
                        "services are now available online "
                        "through Dawlati."
                    ),
                ),

                ContentItem(
                    number=2,
                    type="Slide",
                    headline="Available through Dawlati",
                    body=(
                        "Explore the available Ministry of "
                        "Agriculture services on Dawlati."
                    ),
                ),

                ContentItem(
                    number=3,
                    type="Slide",
                    headline="For the agricultural sector",
                    body=(
                        "The announcement is relevant to "
                        "farmers, producers, and agricultural "
                        "businesses."
                    ),
                ),

                ContentItem(
                    number=4,
                    type="Slide",
                    headline="Explore the services",
                    body=(
                        "Discover the 7 available Ministry of Agriculture services "
                        "through Dawlati."
                    ),
                ),
            ],

            visual_concept=(
                "A professional public-sector carousel "
                "announcing seven Ministry of Agriculture "
                "services available through Dawlati."
            ),

            visual_generation_prompt=(
                "Create a professional government-services "
                "carousel with clear information hierarchy "
                "for seven Ministry of Agriculture services."
            ),

            cta=(
                "Explore the 7 available Ministry of Agriculture services on Dawlati"
            ),

            hashtags=[
                "#Dawlati",
                "#دولتي",
            ],

            brand_check=BrandCheck(
                status="PASS",
                issues=[],
                recommendations=[],
            ),
        )


    def _bad_language_content(self):

        return MarketingContent(
            caption_ar=(
                "منصة «دولتي» تُعَدُّ الآن "
                "7 خدمات حكومية لقطاع الزراعة."
            ),

            caption_en=(
                "Seven Ministry of Agriculture services "
                "are now available online through Dawlati."
            ),

            content_structure=[
                ContentItem(
                    number=1,
                    type="Slide",
                    headline="7 Agriculture Services",
                    body=(
                        "Seven Ministry of Agriculture "
                        "services are available through Dawlati."
                    ),
                ),
            ],

            visual_concept=(
                "A professional government-services carousel "
                "for seven Ministry of Agriculture services."
            ),

            visual_generation_prompt=(
                "Create a professional government-services "
                "carousel with clear information hierarchy."
            ),

            cta=(
                "Explore the 7 available Ministry of Agriculture services on Dawlati"
            ),

            hashtags=[
                "#Dawlati",
                "#دولتي",
            ],

            brand_check=BrandCheck(
                status="PASS",
                issues=[],
                recommendations=[],
            ),
        )


    # --------------------------------------------------
    # Tests
    # --------------------------------------------------

    def test_initial_prompt_declares_authoritative_campaign_audience(self):
        prompt = build_content_prompt(self.brief, self.strategy)

        self.assertIn("AUTHORITATIVE CAMPAIGN AUDIENCE", prompt)
        self.assertIn("Farmers\nProducers\nAgricultural businesses", prompt)
        self.assertIn(
            "The audience above is authoritative for this campaign.",
            prompt,
        )
        self.assertIn("organization-wide audiences", prompt)

    def test_initial_prompt_scopes_general_brand_knowledge_as_context(self):
        prompt = build_content_prompt(self.brief, self.strategy)
        self.assertIn("GENERAL BRAND KNOWLEDGE IS CONTEXT ONLY", prompt)
        self.assertIn("If the brief refers to unnamed services, keep them unnamed", prompt)
        self.assertIn("Do not transform general Dawlati capabilities into service names", prompt)
        self.assertNotIn("grounding_provenance", prompt)
        self.assertNotIn("strategy_validation", prompt)
        self.assertLess(len(prompt), 12000)

    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_valid_first_draft_does_not_trigger_repair(
        self,
        mock_repair,
        mock_initial,
    ):

        mock_initial.return_value = (
            self._valid_content()
        )


        result = generate_marketing_content(
            brief=self.brief,
            strategy=self.strategy,
        )


        mock_repair.assert_not_called()


        self.assertFalse(
            result[
                "repair"
            ][
                "repair_attempted"
            ]
        )

        self.assertFalse(result["fallback"]["attempted"])
        self.assertFalse(result["fallback"]["successful"])
        self.assertEqual(result["generation_source"], "AI")


        self.assertFalse(
            result[
                "repair"
            ][
                "repair_successful"
            ]
        )


        self.assertEqual(
            result[
                "factual_validation"
            ][
                "status"
            ],
            "PASS"
        )


        self.assertEqual(
            result[
                "language_validation"
            ][
                "status"
            ],
            "PASS"
        )


    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_bad_first_draft_is_repaired_successfully(
        self,
        mock_repair,
        mock_initial,
    ):

        mock_initial.return_value = (
            self._bad_language_content()
        )

        mock_repair.return_value = (
            self._valid_content()
        )


        result = generate_marketing_content(
            brief=self.brief,
            strategy=self.strategy,
        )


        mock_repair.assert_called_once()


        self.assertTrue(
            result[
                "repair"
            ][
                "repair_attempted"
            ]
        )

        self.assertFalse(result["fallback"]["attempted"])
        self.assertFalse(result["fallback"]["successful"])
        self.assertEqual(result["generation_source"], "AI repair")


        self.assertTrue(
            result[
                "repair"
            ][
                "repair_successful"
            ]
        )


        self.assertIsNotNone(
            result[
                "repair"
            ][
                "initial_validation_error"
            ]
        )


        self.assertEqual(
            result[
                "language_validation"
            ][
                "status"
            ],
            "PASS"
        )


        self.assertEqual(
            result[
                "caption_ar"
            ],
            (
                "أصبحت 7 خدمات تابعة لوزارة الزراعة "
                "متاحة الآن إلكترونياً عبر منصة «دولتي»."
            )
        )


    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_structured_service_hallucination_is_repaired_generically(
        self,
        mock_repair,
        mock_initial,
    ):
        hallucinated = self._valid_content()
        hallucinated.content_structure[1].headline = (
            "Crop insurance registration"
        )
        hallucinated.content_structure[1].body = (
            "Register for crop insurance through Dawlati."
        )
        mock_initial.return_value = hallucinated
        mock_repair.return_value = self._valid_content()

        result = generate_marketing_content(
            brief=self.brief,
            strategy=self.strategy,
        )

        mock_repair.assert_called_once()
        self.assertTrue(result["repair"]["repair_attempted"])
        self.assertTrue(result["repair"]["repair_successful"])
        self.assertEqual(result["factual_validation"]["status"], "PASS")
        self.assertNotIn(
            "Crop insurance registration",
            str(result["content_structure"]),
        )


    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_access_and_audience_expansion_trigger_one_repair(
        self,
        mock_repair,
        mock_initial,
    ):
        invalid = self._valid_content()
        invalid.content_structure[1].body = (
            "Access services anytime from anywhere with Dawlati."
        )
        invalid.content_structure[2].body = (
            "Citizens of Lebanon who use government services."
        )
        mock_initial.return_value = invalid
        mock_repair.return_value = self._valid_content()

        result = generate_marketing_content(
            brief=self.brief,
            strategy=self.strategy,
        )

        mock_repair.assert_called_once()
        repair_error = mock_repair.call_args.kwargs["validation_error"]
        repair_context = mock_repair.call_args.kwargs["validation_context"]
        self.assertIn("content_structure[1].body", repair_error)
        self.assertIn("Access services anytime from anywhere", repair_error)
        self.assertIn("content_structure[2].body", repair_error)
        self.assertIn("Citizens of Lebanon", repair_error)
        self.assertEqual(repair_context["validation_stage"], "factual_validation")
        self.assertTrue(any(
            issue.get("field") == "content_structure[2].body"
            and issue.get("generated_audience") == "Citizens of Lebanon"
            for issue in repair_context["issues"]
        ))
        self.assertTrue(result["repair"]["repair_attempted"])
        self.assertTrue(result["repair"]["repair_successful"])
        self.assertEqual(result["factual_validation"]["status"], "PASS")


    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_bad_audience_repair_uses_fallback_after_one_ai_attempt(
        self,
        mock_repair,
        mock_initial,
    ):
        initial = self._valid_content()
        initial.content_structure[2].body = (
            "Citizens of Lebanon can use these services."
        )
        invalid_repair = self._valid_content()
        invalid_repair.content_structure[2].body = (
            "Citizens can use these services."
        )
        mock_initial.return_value = initial
        mock_repair.return_value = invalid_repair

        result = generate_marketing_content(
            brief=self.brief,
            strategy=self.strategy,
        )

        mock_repair.assert_called_once()
        self.assertTrue(result["fallback"]["attempted"])
        self.assertTrue(result["fallback"]["successful"])
        self.assertFalse(result["repair"]["repair_successful"])


    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_platform_feature_substitution_is_repaired_generically(
        self,
        mock_repair,
        mock_initial,
    ):
        invalid = self._valid_content()
        invalid.content_structure[1].headline = "Government Service Directory"
        invalid.content_structure[1].body = "Government Information"
        mock_initial.return_value = invalid
        mock_repair.return_value = self._valid_content()

        result = generate_marketing_content(self.brief, self.strategy)

        mock_repair.assert_called_once()
        context = mock_repair.call_args.kwargs["validation_context"]
        self.assertTrue(any(
            issue["type"] == "subject_binding_violation"
            for issue in context["issues"]
        ))
        self.assertTrue(result["repair"]["repair_attempted"])
        self.assertTrue(result["repair"]["repair_successful"])
        self.assertEqual(result["factual_validation"]["status"], "PASS")


    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_platform_feature_substitution_in_repair_uses_fallback(
        self,
        mock_repair,
        mock_initial,
    ):
        initial = self._valid_content()
        initial.content_structure[1].headline = "Government Service Directory"
        invalid_repair = self._valid_content()
        invalid_repair.content_structure[1].headline = "Digital Application"
        mock_initial.return_value = initial
        mock_repair.return_value = invalid_repair

        result = generate_marketing_content(self.brief, self.strategy)

        mock_repair.assert_called_once()
        self.assertTrue(result["fallback"]["attempted"])
        self.assertTrue(result["fallback"]["successful"])
        self.assertFalse(result["repair"]["repair_successful"])


    @patch(
        "content_generator._generate_initial_content"
    )
    @patch(
        "content_generator._generate_repaired_content"
    )
    def test_bad_repair_is_blocked(
        self,
        mock_repair,
        mock_initial,
    ):

        bad_initial = self._valid_content()
        bad_initial.caption_ar = (
            "منصة «دولتي» تُعَدُّ الآن 7 خدمات تابعة لوزارة الزراعة."
        )
        bad_repair = self._valid_content()
        bad_repair.caption_ar = (
            "منصة «دولتي» تُعَدُّ الآن 7 خدمات تابعة لوزارة الزراعة."
        )
        mock_initial.return_value = bad_initial
        mock_repair.return_value = bad_repair


        with self.assertRaises(
            RuntimeError
        ) as context:

            generate_marketing_content(
                brief=self.brief,
                strategy=self.strategy,
            )


        mock_repair.assert_called_once()


        error_message = str(
            context.exception
        )


        self.assertIn(
            "after one automatic repair attempt",
            error_message
        )


        self.assertIn(
            "Initial validation error",
            error_message
        )


        self.assertIn(
            "Repair validation error",
            error_message
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
    
