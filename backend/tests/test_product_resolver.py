import unittest

from backend.app.product_resolver import (
    ProductResolution,
    canonicalize_product_url,
    is_product_url,
    resolve_product_url,
    verify_product_page,
)


PRODUCT_URL = "https://www.partselect.com/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Shelf-Bin.htm"


def ok_page(text):
    return {"ok": True, "url": PRODUCT_URL, "text": text, "links": [], "error": None}


class ProductResolverTests(unittest.TestCase):
    def test_canonicalizes_tracking_params(self):
        self.assertEqual(canonicalize_product_url(f"{PRODUCT_URL}?SourceCode=18"), PRODUCT_URL)

    def test_recognizes_product_url(self):
        self.assertTrue(is_product_url(PRODUCT_URL))
        self.assertFalse(is_product_url("https://www.partselect.com/Repair/Refrigerator/Not-Making-Ice/"))

    def test_verifies_page_contains_identifier(self):
        result = verify_product_page("PS11752778", PRODUCT_URL, fetcher=lambda url: ok_page("PartSelect Number PS11752778"))
        self.assertEqual(result.status, "resolved")

    def test_rejects_page_without_identifier(self):
        result = verify_product_page("PS11752778", PRODUCT_URL, fetcher=lambda url: ok_page("Some other product"))
        self.assertEqual(result.status, "not_found")

    def test_accepts_url_identifier_when_fetch_blocked(self):
        blocked = {"ok": False, "url": PRODUCT_URL, "text": "", "links": [], "error": "HTTP Error 403: Forbidden"}
        result = verify_product_page("PS11752778", PRODUCT_URL, fetcher=lambda url: blocked)
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.confidence, "medium")
        self.assertIn("url_identifier_fetch_blocked", result.matched_on)

    def test_resolves_single_verified_search_candidate(self):
        def searcher(query):
            return [{"title": "Door Shelf Bin", "url": PRODUCT_URL, "snippet": "PS11752778"}]

        result = resolve_product_url("PS11752778", searcher=searcher, fetcher=lambda url: ok_page("PartSelect Number PS11752778"))
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.url, PRODUCT_URL)

    def test_propagates_search_unavailable(self):
        def searcher(query):
            return ProductResolution("search_unavailable", query, error="missing keys")

        result = resolve_product_url("PS11752778", searcher=searcher)
        self.assertEqual(result.status, "search_unavailable")


if __name__ == "__main__":
    unittest.main()
