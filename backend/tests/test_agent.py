import unittest
from unittest.mock import patch

from backend.app.agent import category_from_model_number, classify_identifier, handle_chat, route_intent
from backend.app.product_resolver import ProductResolution


PRODUCT_URL = "https://www.partselect.com/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Shelf-Bin.htm"
MODEL_URL = "https://www.partselect.com/Models/WDT780SAEM1/"


def ok_page(url, text):
    return {"ok": True, "url": url, "text": text, "links": [], "error": None}


class AgentTests(unittest.TestCase):
    def test_classifies_partselect_and_model_numbers(self):
        identifiers = classify_identifier("Is PS11752778 compatible with WDT780SAEM1?")
        self.assertIn("PS11752778", identifiers["partselect_numbers"])
        self.assertIn("WDT780SAEM1", identifiers["model_numbers"])

    def test_self_service_linkout_uses_canonical_url(self):
        result = handle_chat([{"role": "user", "content": "Check my order status"}])
        self.assertEqual(result.flow, "self_service")
        self.assertIn("https://www.partselect.com/user/self-service/", result.content)

    def test_model_locator_linkout(self):
        result = handle_chat([{"role": "user", "content": "Where do I find my refrigerator model number?"}])
        self.assertEqual(result.flow, "model_locator")
        self.assertIn("Find-Your-Model-Number", result.content)

    def test_out_of_scope_redirects(self):
        result = handle_chat([{"role": "user", "content": "Write me a poem about space"}])
        self.assertEqual(result.flow, "out_of_scope")
        self.assertIn("refrigerator and dishwasher", result.content)

    def test_troubleshooting_clarifies_model_number_for_known_appliance(self):
        result = handle_chat([{"role": "user", "content": "The ice maker on my Whirlpool fridge is not working"}])
        self.assertEqual(result.flow, "troubleshoot")
        self.assertIn("Do you have the model number", result.content)
        self.assertTrue(any("Find-Your-Model-Number" in source["url"] for source in result.sources))
        self.assertFalse(any(source["url"] == "https://www.partselect.com/Repair/" for source in result.sources))

    def test_troubleshooting_requires_appliance_type_when_missing(self):
        result = handle_chat([{"role": "user", "content": "My ice maker is not working"}])
        self.assertEqual(result.flow, "troubleshoot")
        self.assertIn("Which appliance", result.content)

    @patch("backend.app.agent.fetch_partselect_page")
    def test_continue_without_model_uses_specific_symptom_page(self, fetch_page):
        fetch_page.return_value = ok_page(
            "https://www.partselect.com/Repair/Refrigerator/Not-Making-Ice/",
            "Refrigerator not making ice. Water inlet valve, water filter, and ice maker assembly are common causes.",
        )
        result = handle_chat(
            [
                {"role": "user", "content": "The ice maker on my Whirlpool fridge is not working"},
                {"role": "assistant", "content": "Do you have the model number?"},
                {"role": "user", "content": "Continue without model"},
            ],
            current_flow="troubleshoot",
        )
        self.assertEqual(result.flow, "troubleshoot")
        self.assertTrue(any("Not-Making-Ice" in source["url"] for source in result.sources))
        self.assertFalse(any(source["url"] == "https://www.partselect.com/Repair/" for source in result.sources))

    @patch("backend.app.agent.fetch_partselect_page")
    def test_continue_without_model_fetch_failure_still_shows_specific_symptom_page(self, fetch_page):
        fetch_page.return_value = {"ok": False, "url": "", "text": "", "links": [], "error": "blocked"}
        result = handle_chat(
            [
                {"role": "user", "content": "The ice maker on my Whirlpool fridge is not working"},
                {"role": "assistant", "content": "Do you have the model number?"},
                {"role": "user", "content": "Continue without model"},
            ],
            current_flow="troubleshoot",
        )
        self.assertEqual(result.flow, "troubleshoot")
        self.assertTrue(any("Not-Making-Ice" in source["url"] for source in result.sources))
        self.assertFalse(any(source["url"] == "https://www.partselect.com/Repair/Refrigerator/" for source in result.sources))

    def test_routes_context_switch_to_installation(self):
        self.assertEqual(route_intent("Actually, help me install PS11752778", "troubleshoot"), "installation")

    def test_model_number_reply_stays_in_current_flow(self):
        self.assertEqual(route_intent("I found the model number WDT780SAEM1", "troubleshoot"), "troubleshoot")

    def test_model_prefix_category_heuristic_for_known_dishwasher_model(self):
        self.assertEqual(category_from_model_number("WDT780SAEM1"), "dishwasher")

    @patch("backend.app.agent.resolve_product_url")
    def test_product_resolver_error_mentions_openai_not_google(self, resolve_product):
        from backend.app.product_resolver import ProductResolution

        resolve_product.return_value = ProductResolution("fetch_error", "PS11752778", error="search failed")
        result = handle_chat([{"role": "user", "content": "How can I install PS11752778?"}])
        self.assertIn("OpenAI key", result.content)
        self.assertNotIn("Google", result.content)

    @patch("backend.app.agent.fetch_partselect_page")
    @patch("backend.app.agent.resolve_product_url")
    def test_installation_uses_resolved_product_url(self, resolve_product, fetch_page):
        resolve_product.return_value = ProductResolution("resolved", "PS11752778", url=PRODUCT_URL, confidence="high")
        fetch_page.return_value = ok_page(
            PRODUCT_URL,
            "Refrigerator Door Shelf Bin. PartSelect Number PS11752778. Installation Instructions snap the bin into the door tabs.",
        )
        result = handle_chat([{"role": "user", "content": "How can I install part number PS11752778?"}])
        self.assertEqual(result.flow, "installation")
        self.assertTrue(any(source["url"] == PRODUCT_URL for source in result.sources))
        self.assertIn("PS11752778", result.content)

    @patch("backend.app.agent.fetch_partselect_page")
    @patch("backend.app.agent.resolve_product_url")
    def test_product_information_describes_product_from_evidence(self, resolve_product, fetch_page):
        resolve_product.return_value = ProductResolution("resolved", "PS11752778", url=PRODUCT_URL, confidence="high")
        fetch_page.return_value = ok_page(
            PRODUCT_URL,
            "Whirlpool Refrigerator Door Shelf Bin. PartSelect Number PS11752778. Manufacturer Part Number WPW10321304. Product Description refrigerator door bin.",
        )
        result = handle_chat([{"role": "user", "content": "What is PS11752778?"}])
        self.assertEqual(result.flow, "information")
        self.assertIn("PS11752778", result.content)
        self.assertTrue("Door Shelf Bin" in result.content or "door bin" in result.content)

    @patch("backend.app.agent.fetch_partselect_page")
    @patch("backend.app.agent.resolve_product_url")
    def test_compatibility_is_conservative_on_category_mismatch(self, resolve_product, fetch_page):
        resolve_product.return_value = ProductResolution("resolved", "PS11752778", url=PRODUCT_URL, confidence="high")

        def fake_fetch(url):
            if url == PRODUCT_URL:
                return ok_page(url, "Refrigerator Door Shelf Bin. PartSelect Number PS11752778.")
            if url == MODEL_URL:
                return ok_page(url, "WDT780SAEM1 Whirlpool Dishwasher - Overview OEM Parts")
            return ok_page(url, "")

        fetch_page.side_effect = fake_fetch
        result = handle_chat([{"role": "user", "content": "Is PS11752778 compatible with my WDT780SAEM1 model?"}])
        self.assertEqual(result.flow, "compatibility")
        self.assertIn("Decision", result.content)
        self.assertIn("No", result.content)
        self.assertIn("PS11752778", result.content)
        self.assertIn("WDT780SAEM1", result.content)
        self.assertTrue(any(source["url"] == PRODUCT_URL for source in result.sources))
        self.assertTrue(any(source["url"] == MODEL_URL for source in result.sources))


if __name__ == "__main__":
    unittest.main()
