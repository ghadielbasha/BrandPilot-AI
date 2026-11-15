import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import knowledge_loader


class KnowledgeLoaderTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)

        self.brand_dir = self.base / "omsar"
        self.brand_dir.mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_json(self, name, data):
        path = self.brand_dir / name

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

    def create_valid_knowledge(self):

        self.write_json(
            "sources.json",
            {
                "brand": "omsar",
                "sources": [
                    {
                        "id": "OMSAR-TEST-001",
                        "status": "approved",
                        "classification": "public",
                        "title": "Approved Test Source"
                    }
                ]
            }
        )

        self.write_json(
            "organization.json",
            {
                "id": "OMSAR-ORG-TEST",
                "brand_key": "omsar",
                "record_type": "organization_profile",
                "classification": "public",
                "status": "approved",
                "source_ids": [
                    "OMSAR-TEST-001"
                ]
            }
        )

        self.write_json(
            "terminology.json",
            {
                "brand": "omsar",
                "record_type": "terminology_dictionary",
                "classification": "public",
                "status": "approved",
                "terms": [
                    {
                        "id": "TERM-TEST-001",
                        "source_ids": [
                            "OMSAR-TEST-001"
                        ]
                    }
                ]
            }
        )

    def test_valid_knowledge_passes(self):

        self.create_valid_knowledge()

        with patch.object(
            knowledge_loader,
            "KNOWLEDGE_DIR",
            self.base
        ):

            result = knowledge_loader.load_brand_knowledge(
                "omsar"
            )

        self.assertEqual(
            result["brand"],
            "omsar"
        )

        self.assertEqual(
            len(result["sources"]),
            1
        )

    def test_unknown_source_is_blocked(self):

        self.create_valid_knowledge()

        organization_path = (
            self.brand_dir
            / "organization.json"
        )

        with open(
            organization_path,
            "r",
            encoding="utf-8"
        ) as file:
            organization = json.load(file)

        organization[
            "source_ids"
        ] = [
            "FAKE-SOURCE-999"
        ]

        self.write_json(
            "organization.json",
            organization
        )

        with patch.object(
            knowledge_loader,
            "KNOWLEDGE_DIR",
            self.base
        ):

            with self.assertRaises(
                knowledge_loader.KnowledgeError
            ):
                knowledge_loader.load_brand_knowledge(
                    "omsar"
                )

    def test_unapproved_source_is_blocked(self):

        self.create_valid_knowledge()

        self.write_json(
            "sources.json",
            {
                "brand": "omsar",
                "sources": [
                    {
                        "id": "OMSAR-TEST-001",
                        "status": "pending",
                        "classification": "public",
                        "title": "Pending Source"
                    }
                ]
            }
        )

        with patch.object(
            knowledge_loader,
            "KNOWLEDGE_DIR",
            self.base
        ):

            with self.assertRaises(
                knowledge_loader.KnowledgeError
            ):
                knowledge_loader.load_brand_knowledge(
                    "omsar"
                )

    def test_unapproved_record_is_blocked(self):

        self.create_valid_knowledge()

        organization_path = (
            self.brand_dir
            / "organization.json"
        )

        with open(
            organization_path,
            "r",
            encoding="utf-8"
        ) as file:
            organization = json.load(file)

        organization[
            "status"
        ] = "draft"

        self.write_json(
            "organization.json",
            organization
        )

        with patch.object(
            knowledge_loader,
            "KNOWLEDGE_DIR",
            self.base
        ):

            with self.assertRaises(
                knowledge_loader.KnowledgeError
            ):
                knowledge_loader.load_brand_knowledge(
                    "omsar"
                )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )