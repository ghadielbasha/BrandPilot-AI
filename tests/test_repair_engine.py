import unittest

from repair_engine import (
    MAX_REPAIR_ATTEMPTS,
    RepairEngineError,
    build_repair_prompt,
    create_repair_metadata,
)


class RepairEngineTests(
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
            "languages": [
                "Arabic",
                "English",
            ],
        }

        self.failed_content = {
            "caption_ar": (
                "منصة «دولتي» تُعَدُّ الآن "
                "7 خدمات حكومية."
            ),

            "caption_en": (
                "Seven services are available "
                "through Dawlati."
            ),
        }

        self.validation_error = (
            "caption_ar: Malformed Arabic structure detected."
        )


    def test_repair_attempt_limit_is_one(self):

        self.assertEqual(
            MAX_REPAIR_ATTEMPTS,
            1
        )


    def test_repair_prompt_contains_validator_error(self):

        prompt = build_repair_prompt(
            brief=self.brief,
            strategy=self.strategy,
            failed_content=self.failed_content,
            validation_error=self.validation_error,
        )


        self.assertIn(
            self.validation_error,
            prompt
        )


    def test_repair_prompt_contains_original_brief(self):

        prompt = build_repair_prompt(
            brief=self.brief,
            strategy=self.strategy,
            failed_content=self.failed_content,
            validation_error=self.validation_error,
        )


        self.assertIn(
            self.brief,
            prompt
        )


    def test_repair_prompt_contains_failed_content(self):

        prompt = build_repair_prompt(
            brief=self.brief,
            strategy=self.strategy,
            failed_content=self.failed_content,
            validation_error=self.validation_error,
        )


        self.assertIn(
            "منصة «دولتي»",
            prompt
        )

    def _audience_repair_prompt(self):
        strategy = dict(self.strategy)
        strategy["target_audience"] = [
            "Farmers",
            "Producers",
            "Agricultural businesses",
        ]
        return build_repair_prompt(
            brief=self.brief,
            strategy=strategy,
            failed_content={
                **self.failed_content,
                "content_structure": [{
                    "number": 2,
                    "type": "Slide",
                    "headline": "Who benefits?",
                    "body": "Citizens of Lebanon can use these services.",
                }],
            },
            validation_error=(
                "factual_validation: Unsupported audience expansion. "
                "field: content_structure[0].body; generated audience: "
                '"Citizens of Lebanon"; approved audience: Farmers, '
                "Producers, Agricultural businesses."
            ),
            validation_context={
                "validation_stage": "factual_validation",
                "issues": [{
                    "type": "unsupported_audience",
                    "field": "content_structure[0].body",
                    "generated_audience": "Citizens of Lebanon",
                    "approved_audience": [
                        "Farmers", "Producers", "Agricultural businesses",
                    ],
                }],
            },
        )

    def test_audience_repair_prompt_contains_approved_audience(self):
        prompt = self._audience_repair_prompt()
        self.assertIn("MANDATORY AUDIENCE REPAIR", prompt)
        self.assertIn("- Farmers\n- Producers\n- Agricultural businesses", prompt)
        self.assertIn("The approved strategy is authoritative.", prompt)

    def test_audience_repair_prompt_explicitly_removes_citizens(self):
        prompt = self._audience_repair_prompt()
        self.assertIn("REMOVE ALL UNSUPPORTED AUDIENCE REFERENCES", prompt)
        self.assertIn("- Citizens", prompt)
        self.assertIn("- Citizens of Lebanon", prompt)
        self.assertIn("failed draft is NOT authoritative", prompt)

    def test_repair_prompt_contains_structured_validation_context(self):
        prompt = self._audience_repair_prompt()
        self.assertIn("STRUCTURED VALIDATION CONTEXT", prompt)
        self.assertIn('"validation_stage": "factual_validation"', prompt)
        self.assertIn('"field": "content_structure[0].body"', prompt)
        self.assertIn('"generated_audience": "Citizens of Lebanon"', prompt)

    def test_repair_prompt_omits_redundant_validation_results(self):
        prompt = build_repair_prompt(
            brief=self.brief,
            strategy={**self.strategy, "grounding_provenance": {"duplicate": True}},
            failed_content=self.failed_content,
            validation_error=self.validation_error,
            validation_context={
                "validation_stage": "language_validation",
                "issues": [{"type": "language", "field": "caption_ar"}],
                "field_results": {"caption_en": {"status": "PASS"}},
            },
        )
        self.assertNotIn("grounding_provenance", prompt)
        self.assertNotIn("field_results", prompt)

    def test_subject_binding_repair_removes_platform_substitutions(self):
        strategy = dict(self.strategy)
        strategy["target_audience"] = [
            "Farmers", "Producers", "Agricultural businesses",
        ]
        prompt = build_repair_prompt(
            brief=self.brief,
            strategy=strategy,
            failed_content={
                **self.failed_content,
                "content_structure": [{
                    "number": 1,
                    "type": "Slide",
                    "headline": "Government Service Directory",
                    "body": "Digital Application",
                }],
            },
            validation_error=(
                "factual_validation: Subject binding violation. "
                "field: content_structure[0].headline"
            ),
            validation_context={
                "validation_stage": "factual_validation",
                "issues": [{
                    "type": "subject_binding_violation",
                    "field": "content_structure[0].headline",
                    "campaign_subject": "Seven Ministry of Agriculture services",
                    "generated_substitution": "Government Service Directory",
                }],
            },
        )
        self.assertIn("MANDATORY SUBJECT-BINDING REPAIR", prompt)
        self.assertIn("Seven Ministry of Agriculture services", prompt)
        self.assertIn("Approved general brand knowledge is context only", prompt)
        self.assertIn("must not fill missing", prompt)
        self.assertIn("service names or become an item", prompt)


    def test_empty_validation_error_is_blocked(self):

        with self.assertRaises(
            RepairEngineError
        ):

            build_repair_prompt(
                brief=self.brief,
                strategy=self.strategy,
                failed_content=self.failed_content,
                validation_error="",
            )


    def test_repair_metadata(self):

        metadata = create_repair_metadata(
            attempted=True,
            successful=True,
            initial_error="Test error",
        )


        self.assertTrue(
            metadata[
                "repair_attempted"
            ]
        )

        self.assertTrue(
            metadata[
                "repair_successful"
            ]
        )

        self.assertEqual(
            metadata[
                "max_repair_attempts"
            ],
            1
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
    
