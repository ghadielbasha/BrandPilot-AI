import unittest

from validators.factual_validator import (
    enforce_structured_factual_claims,
    validate_structured_factual_claims,
)


class StructuredFactualValidatorTests(unittest.TestCase):

    def setUp(self):
        self.brief = (
            "Seven Ministry of Agriculture services are now available "
            "online through Dawlati."
        )
        self.strategy = {
            "brand_key": "dawlati",
            "platform": "Instagram",
            "target_audience": [
                "Farmers", "Producers", "Agricultural businesses",
            ],
            "campaign_angle": (
                "Announce that 7 Ministry of Agriculture services are now "
                "available online through Dawlati."
            ),
            "cta": "Explore the 7 available Ministry of Agriculture services on Dawlati",
        }
        self.knowledge = {
            "organization": {
                "summary": "Dawlati is Lebanon's government-services platform.",
                "core_functions": [
                    {"name_en": "Government Service Directory", "scope": "platform_wide"},
                    {"name_en": "Government Information", "scope": "platform_wide"},
                    {"name_en": "Digital Application", "scope": "service_dependent"},
                    {"name_en": "Online Payment", "scope": "service_dependent"},
                    {"name_en": "Request Tracking", "scope": "service_dependent"},
                ],
            },
            "approved_services": {"services": []},
        }

    def _safe_campaign(self):
        return {
            "caption_ar": "",
            "caption_en": self.brief,
            "content_structure": [
                {
                    "number": 1,
                    "type": "Slide",
                    "headline": "7 Ministry of Agriculture services",
                    "body": "Services are now available online through Dawlati.",
                },
                {
                    "number": 2,
                    "type": "Slide",
                    "headline": "Discover the available services",
                    "body": "For farmers, producers, and agricultural businesses.",
                },
            ],
            "visual_concept": (
                "A factual public-sector carousel about seven Ministry of "
                "Agriculture services available through Dawlati."
            ),
            "visual_generation_prompt": (
                "Create a professional carousel with a clear announcement "
                "and generic service imagery."
            ),
            "cta": "Explore the 7 available Ministry of Agriculture services on Dawlati",
            "hashtags": ["#Dawlati", "#Agriculture"],
        }

    def _validate(self, campaign):
        return validate_structured_factual_claims(
            brief=self.brief,
            content=campaign,
            approved_strategy=self.strategy,
            approved_knowledge=self.knowledge,
        )

    def test_invented_seven_service_structure_is_blocked(self):
        campaign = self._safe_campaign()
        invented = [
            "Agricultural subsidies application",
            "Crop insurance registration",
            "Farm land records access",
            "Agricultural extension services",
            "Market price monitoring",
            "Farm input procurement",
            "Agricultural training programs",
        ]
        campaign["content_structure"] = [
            {
                "number": index,
                "type": "Slide",
                "headline": title,
                "body": title,
            }
            for index, title in enumerate(invented, start=1)
        ]

        result = self._validate(campaign)

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any(
            issue["type"] == "unsupported_service_detail"
            and issue["field"].startswith("content_structure[")
            for issue in result["issues"]
        ))

    def test_repaired_generic_structure_passes(self):
        repaired = self._safe_campaign()

        result = self._validate(repaired)

        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["valid"])

    def test_unsupported_apply_now_and_link_in_bio_ctas_are_blocked(self):
        for cta in ("Apply now", "Explore the services — link in bio"):
            with self.subTest(cta=cta):
                campaign = self._safe_campaign()
                campaign["cta"] = cta
                result = self._validate(campaign)
                self.assertEqual(result["field_results"]["cta"]["status"], "BLOCK")

    def test_visual_prompt_with_invented_service_details_is_blocked(self):
        campaign = self._safe_campaign()
        campaign["visual_generation_prompt"] = (
            "Create seven labeled icons including crop insurance registration, "
            "farm input procurement, and market price monitoring."
        )

        result = self._validate(campaign)

        self.assertEqual(
            result["field_results"]["visual_generation_prompt"]["status"],
            "BLOCK",
        )

    def test_unsupported_benefits_and_audience_expansion_are_blocked(self):
        campaign = self._safe_campaign()
        campaign["caption_en"] = (
            "Seven services streamline agricultural activities, improve "
            "productivity, and support rural communities in Lebanon."
        )

        result = self._validate(campaign)

        issue_types = {issue["type"] for issue in result["issues"]}
        capabilities = {
            issue.get("capability") for issue in result["issues"]
        }
        self.assertIn("unsupported_claim", issue_types)
        self.assertIn("unsupported_audience", issue_types)
        self.assertIn("efficiency_improvement", capabilities)
        self.assertIn("productivity_improvement", capabilities)

    def test_safe_generic_campaign_passes_enforcement(self):
        result = enforce_structured_factual_claims(
            brief=self.brief,
            content=self._safe_campaign(),
            approved_strategy=self.strategy,
            approved_knowledge=self.knowledge,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(
            field["status"] == "PASS"
            for field in result["field_results"].values()
        ))

    def test_access_anytime_from_anywhere_is_blocked_with_field(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = (
            "Access services anytime from anywhere with Dawlati."
        )

        result = self._validate(campaign)
        issues = result["field_results"]["content_structure[1].body"]["issues"]

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any(
            issue.get("matched_phrase") == "Access services anytime from anywhere"
            for issue in issues
        ))

    def test_access_services_anytime_is_blocked(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = "Access services anytime."
        result = self._validate(campaign)
        self.assertEqual(
            result["field_results"]["content_structure[1].body"]["status"],
            "BLOCK",
        )

    def test_access_services_from_anywhere_is_blocked(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = "Access services from anywhere."
        result = self._validate(campaign)
        self.assertEqual(
            result["field_results"]["content_structure[1].body"]["status"],
            "BLOCK",
        )

    def test_explore_available_services_is_safe(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = (
            "Explore the available services through Dawlati."
        )
        self.assertEqual(self._validate(campaign)["status"], "PASS")

    def test_campaign_audience_overrides_broader_brand_audience(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = (
            "Citizens of Lebanon who use government services."
        )
        knowledge = {
            "organization": {
                "primary_audiences": ["Citizens", "Businesses"],
            },
            "approved_services": {"services": []},
        }

        result = validate_structured_factual_claims(
            brief=self.brief,
            content=campaign,
            approved_strategy=self.strategy,
            approved_knowledge=knowledge,
        )
        issue = next(
            item for item in result["issues"]
            if item["type"] == "unsupported_audience"
        )

        self.assertEqual(issue["field"], "content_structure[1].body")
        self.assertEqual(issue["generated_audience"], "Citizens of Lebanon")
        self.assertEqual(
            issue["approved_audience"],
            ["Farmers", "Producers", "Agricultural businesses"],
        )

    def test_exact_approved_audience_is_safe(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = (
            "Farmers, producers, and agricultural businesses."
        )
        self.assertEqual(self._validate(campaign)["status"], "PASS")

    def test_arabic_anytime_and_anywhere_is_blocked(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = "في أي وقت ومن أي مكان"
        result = self._validate(campaign)
        issues = result["field_results"]["content_structure[1].body"]["issues"]
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            {issue.get("capability") for issue in issues},
            {"continuous_availability", "unrestricted_access"},
        )

    def test_safe_arabic_online_availability_is_allowed(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = (
            "أصبحت 7 خدمات تابعة لوزارة الزراعة متاحة الآن إلكترونياً عبر منصة دولتي."
        )
        self.assertEqual(self._validate(campaign)["status"], "PASS")

    def test_access_claim_is_checked_in_every_required_field(self):
        paths = (
            "caption_ar", "caption_en", "visual_concept",
            "visual_generation_prompt", "cta",
        )
        for path in paths:
            with self.subTest(field=path):
                campaign = self._safe_campaign()
                campaign[path] = "Access services anytime."
                result = self._validate(campaign)
                self.assertEqual(result["field_results"][path]["status"], "BLOCK")

        for member in ("headline", "body"):
            with self.subTest(field=member):
                campaign = self._safe_campaign()
                campaign["content_structure"][1][member] = "Access services anytime."
                path = f"content_structure[1].{member}"
                result = self._validate(campaign)
                self.assertEqual(result["field_results"][path]["status"], "BLOCK")

    def test_compliant_repaired_structure_passes(self):
        repaired = self._safe_campaign()
        repaired["content_structure"][1]["body"] = (
            "Farmers, producers, and agricultural businesses can explore "
            "the available services through Dawlati."
        )
        result = self._validate(repaired)
        self.assertEqual(result["status"], "PASS")

    def test_new_government_services_substitution_is_blocked(self):
        campaign = self._safe_campaign()
        campaign["caption_en"] = "7 new government services are available on Dawlati."
        result = self._validate(campaign)
        issues = result["field_results"]["caption_en"]["issues"]
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("subject_preservation_failure", {i["type"] for i in issues})
        self.assertIn("new_service_claim", {i.get("capability") for i in issues})

    def test_quantified_ministry_subject_is_preserved(self):
        campaign = self._safe_campaign()
        campaign["caption_en"] = (
            "7 Ministry of Agriculture services are now available online "
            "through Dawlati."
        )
        self.assertEqual(self._validate(campaign)["status"], "PASS")

    def test_platform_features_cannot_be_the_unnamed_ministry_services(self):
        campaign = self._safe_campaign()
        names = [
            "Government Service Directory",
            "Government Information",
            "Digital Application",
            "Online Payment",
            "Request Tracking",
        ]
        campaign["content_structure"] = [
            {
                "number": index,
                "type": "Slide",
                "headline": name,
                "body": name,
            }
            for index, name in enumerate(names, start=1)
        ]
        result = self._validate(campaign)
        substitutions = [
            issue for issue in result["issues"]
            if issue["type"] == "subject_binding_violation"
        ]
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(substitutions)
        self.assertTrue(all(
            issue["knowledge_scope"] == "platform_level"
            for issue in substitutions
        ))

    def test_platform_fact_is_allowed_as_explicit_separate_context(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][1]["body"] = (
            "As a general Dawlati platform feature, the Government Service "
            "Directory helps users find government services; it is separate "
            "from the announced Ministry services."
        )
        self.assertEqual(self._validate(campaign)["status"], "PASS")

    def test_new_service_claim_is_blocked_when_brief_only_says_now_available(self):
        campaign = self._safe_campaign()
        campaign["content_structure"][0]["body"] = (
            "Seven new Ministry of Agriculture services are available on Dawlati."
        )
        result = self._validate(campaign)
        self.assertTrue(any(
            issue.get("capability") == "new_service_claim"
            for issue in result["issues"]
        ))

    def test_arabic_new_government_services_are_blocked(self):
        campaign = self._safe_campaign()
        campaign["caption_ar"] = "7 خدمات حكومية جديدة"
        result = self._validate(campaign)
        issues = result["field_results"]["caption_ar"]["issues"]
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("new_service_claim", {i.get("capability") for i in issues})
        self.assertIn("subject_preservation_failure", {i["type"] for i in issues})

    def test_arabic_ministry_subject_is_safe(self):
        campaign = self._safe_campaign()
        campaign["caption_ar"] = (
            "7 خدمات تابعة لوزارة الزراعة متاحة الآن إلكترونياً عبر منصة دولتي."
        )
        self.assertEqual(self._validate(campaign)["status"], "PASS")

    def test_named_service_card_visual_is_blocked_without_catalog(self):
        campaign = self._safe_campaign()
        campaign["visual_generation_prompt"] = (
            "Show a grid of 7 named service cards with icons and brief descriptions."
        )
        result = self._validate(campaign)
        self.assertEqual(
            result["field_results"]["visual_generation_prompt"]["status"],
            "BLOCK",
        )

    def test_individual_service_links_are_blocked_without_catalog_urls(self):
        campaign = self._safe_campaign()
        campaign["visual_generation_prompt"] = (
            "Each card should have a service name and a link to the service page."
        )
        result = self._validate(campaign)
        self.assertTrue(any(
            issue["type"] == "unknown_service_visual_detail"
            for issue in result["field_results"]["visual_generation_prompt"]["issues"]
        ))

    def test_generic_subject_preserving_visual_is_safe(self):
        campaign = self._safe_campaign()
        campaign["visual_generation_prompt"] = (
            "Create a visual announcing that 7 Ministry of Agriculture services "
            "are available online through Dawlati. Use generic agricultural and "
            "digital-service elements without individual service names or URLs."
        )
        self.assertEqual(self._validate(campaign)["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
