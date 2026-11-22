import unittest

from content_generator import _normalize_generated_text
from text_rendering import (
    correct_known_spelling,
    format_arabic_html,
    format_english_html,
)


class TextRenderingTests(unittest.TestCase):
    def test_arabic_only_sentence_is_rtl(self):
        rendered = format_arabic_html("هذه حملة توعوية رسمية")
        self.assertIn('dir="rtl"', rendered)
        self.assertIn('lang="ar"', rendered)
        self.assertIn("direction: rtl;", rendered)
        self.assertIn("text-align: start;", rendered)
        self.assertIn("unicode-bidi: plaintext;", rendered)
        self.assertIn('"Noto Sans Arabic", "Tajawal", "Arial", sans-serif', rendered)

    def test_arabic_sentence_isolates_matchmaking(self):
        rendered = format_arabic_html("تعرّف على Matchmaking اليوم")
        self.assertIn('<bdi dir="ltr">Matchmaking</bdi>', rendered)

    def test_arabic_sentence_isolates_omsar(self):
        rendered = format_arabic_html("مبادرة جديدة من OMSAR")
        self.assertIn('<bdi dir="ltr">OMSAR</bdi>', rendered)

    def test_arabic_sentence_isolates_dawlati(self):
        rendered = format_arabic_html("اكتشف الخدمات عبر Dawlati")
        self.assertIn('<bdi dir="ltr">Dawlati</bdi>', rendered)

    def test_arabic_sentence_isolates_url(self):
        rendered = format_arabic_html("للمزيد قم بزيارة https://example.gov.lb/service")
        self.assertIn('<bdi dir="ltr">https://example.gov.lb/service</bdi>', rendered)

    def test_english_output_remains_ltr(self):
        rendered = format_english_html("Official English campaign content")
        self.assertIn('dir="ltr"', rendered)
        self.assertIn("direction: ltr;", rendered)
        self.assertIn("text-align: start;", rendered)
        self.assertNotIn("brandpilot-rtl", rendered)

    def test_incorrect_matchmaking_spelling_is_never_emitted(self):
        incorrect = "Matcha" + "making"
        corrected = correct_known_spelling(f"Use {incorrect} in this sentence")
        normalized = _normalize_generated_text(
            f"Use {incorrect} in this sentence",
            "omsar",
            [],
        )
        rendered = format_arabic_html(f"استخدم {incorrect} في هذه الجملة")
        self.assertNotIn(incorrect, corrected)
        self.assertNotIn(incorrect, normalized)
        self.assertNotIn(incorrect, rendered)
        self.assertIn("Matchmaking", corrected)
        self.assertIn("Matchmaking", normalized)
        self.assertIn("Matchmaking", rendered)

    def test_all_known_matchmaking_misspellings_are_corrected(self):
        for incorrect in ("Matcha" + "making", "Matcha" + "matching"):
            with self.subTest(incorrect=incorrect):
                self.assertEqual(correct_known_spelling(incorrect), "Matchmaking")


if __name__ == "__main__":
    unittest.main()
