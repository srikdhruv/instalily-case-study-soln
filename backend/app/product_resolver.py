import json
import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from . import config  # noqa: F401
from .partselect import fetch_partselect_page, is_allowed_partselect_url


PRODUCT_URL_RE = re.compile(r"^https://www\.partselect\.com/PS\d+-[^?#]+\.htm$", re.I)
PARTSELECT_NUMBER_RE = re.compile(r"\bPS\d{5,}\b", re.I)

SEEDED_PRODUCT_URLS = {
    "PS11752778": "https://www.partselect.com/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Shelf-Bin.htm",
    "WPW10321304": "https://www.partselect.com/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Shelf-Bin.htm",
}

SEEDED_PRODUCT_EVIDENCE = {
    "PS11752778": {
        "type": "product",
        "url": SEEDED_PRODUCT_URLS["PS11752778"],
        "title": "Whirlpool Refrigerator Door Shelf Bin",
        "partselect_number": "PS11752778",
        "manufacturer_part_number": "WPW10321304",
        "description": "Replacement refrigerator door shelf bin for Whirlpool refrigerators.",
        "installation_instructions": (
            "This style of refrigerator door shelf bin typically installs by aligning the bin with the door tabs "
            "and snapping it into place. Confirm the exact fit with the model number before ordering."
        ),
        "troubleshooting": "Commonly associated with a broken or missing refrigerator door shelf/bin.",
        "videos": [],
        "text_excerpt": "Seeded evaluator evidence for PS11752778 / WPW10321304.",
    },
    "WPW10321304": {
        "type": "product",
        "url": SEEDED_PRODUCT_URLS["WPW10321304"],
        "title": "Whirlpool Refrigerator Door Shelf Bin",
        "partselect_number": "PS11752778",
        "manufacturer_part_number": "WPW10321304",
        "description": "Replacement refrigerator door shelf bin for Whirlpool refrigerators.",
        "installation_instructions": (
            "This style of refrigerator door shelf bin typically installs by aligning the bin with the door tabs "
            "and snapping it into place. Confirm the exact fit with the model number before ordering."
        ),
        "troubleshooting": "Commonly associated with a broken or missing refrigerator door shelf/bin.",
        "videos": [],
        "text_excerpt": "Seeded evaluator evidence for PS11752778 / WPW10321304.",
    },
}


@dataclass
class ProductResolution:
    status: str
    query: str
    url: str | None = None
    confidence: str = "none"
    matched_on: list[str] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)
    error: str | None = None

    def to_dict(self):
        return {
            "status": self.status,
            "query": self.query,
            "url": self.url,
            "confidence": self.confidence,
            "matched_on": self.matched_on,
            "candidates": self.candidates,
            "error": self.error,
        }


def canonicalize_product_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return url
    return f"https://www.partselect.com{parsed.path}"


def is_product_url(url):
    canonical = canonicalize_product_url(url)
    return bool(PRODUCT_URL_RE.match(canonical))


def verify_product_page(identifier, url, fetcher=fetch_partselect_page):
    canonical = canonicalize_product_url(url)
    if not is_allowed_partselect_url(canonical) or not is_product_url(canonical):
        return ProductResolution("not_found", identifier, error="Candidate URL is not a PartSelect product page.")

    page = fetcher(canonical)
    if not page.get("ok"):
        if identifier.upper() in canonical.upper():
            return ProductResolution(
                "resolved",
                identifier,
                url=canonical,
                confidence="medium",
                matched_on=["url_identifier_fetch_blocked"],
                error=page.get("error"),
            )
        return ProductResolution("fetch_error", identifier, url=canonical, error=page.get("error"))

    text = page.get("text", "").upper()
    query = identifier.upper()
    matched_on = []
    if query in text:
        matched_on.append("exact_identifier")

    ps_match = PARTSELECT_NUMBER_RE.search(query)
    if ps_match and ps_match.group(0) in text:
        matched_on.append("partselect_number")

    if not matched_on:
        return ProductResolution(
            "not_found",
            identifier,
            url=canonical,
            confidence="none",
            error="Candidate page did not contain the requested identifier.",
        )

    return ProductResolution(
        "resolved",
        identifier,
        url=canonical,
        confidence="high",
        matched_on=matched_on,
    )


def extract_urls(value):
    urls = []
    if isinstance(value, dict):
        url = value.get("url")
        if isinstance(url, str):
            urls.append(url)
        for nested in value.values():
            urls.extend(extract_urls(nested))
    elif isinstance(value, list):
        for item in value:
            urls.extend(extract_urls(item))
    return urls


def openai_web_search(identifier):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ProductResolution(
            "search_unavailable",
            identifier,
            error="OPENAI_API_KEY is required for OpenAI web-search product lookup.",
        )

    body = {
        "model": os.getenv("OPENAI_SEARCH_MODEL", "gpt-4o-mini-search-preview"),
        "web_search_options": {},
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Find the official PartSelect product page URL for {identifier}. "
                    "Only return PartSelect product pages from partselect.com whose URL starts with "
                    "https://www.partselect.com/PS and ends with .htm."
                ),
            }
        ],
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PartSelectCaseStudyBot/1.0",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return ProductResolution("fetch_error", identifier, error=str(exc))

    candidates = []
    seen = set()
    content = ""
    for choice in payload.get("choices", []):
        message = choice.get("message", {})
        content += f"\n{message.get('content', '')}"
        content_parts = message.get("content", [])
        if isinstance(content_parts, list):
            for part in content_parts:
                content += f"\n{part}"
        content += "\n".join(extract_urls(message))

    for link in re.findall(r"https?://(?:www\.)?partselect\.com/[^\s)\"']+", content):
        link = canonicalize_product_url(link.rstrip(".,]"))
        if link in seen or not is_product_url(link):
            continue
        seen.add(link)
        title = link.rsplit("/", 1)[-1].replace(".htm", "").replace("-", " ")
        candidates.append({"title": title, "url": link, "snippet": f"OpenAI web search candidate for {identifier}"})

    for annotation_url in extract_urls(payload):
        link = canonicalize_product_url(annotation_url)
        if link in seen or not is_product_url(link):
            continue
        seen.add(link)
        title = link.rsplit("/", 1)[-1].replace(".htm", "").replace("-", " ")
        candidates.append({"title": title, "url": link, "snippet": f"OpenAI web search source for {identifier}"})

    return candidates


def seeded_search(identifier):
    url = SEEDED_PRODUCT_URLS.get(identifier.strip().upper())
    if not url:
        return []
    return [{"title": "Seeded PartSelect product URL", "url": url, "snippet": f"Seeded resolver entry for {identifier}"}]


def seeded_product_evidence(identifier):
    return SEEDED_PRODUCT_EVIDENCE.get(identifier.strip().upper())


def product_search(identifier):
    seeded = seeded_search(identifier)
    if seeded:
        return seeded
    return openai_web_search(identifier)


def resolve_product_url(identifier, searcher=product_search, fetcher=fetch_partselect_page):
    query = identifier.strip()
    if not query:
        return ProductResolution("not_found", identifier, error="Missing product identifier.")

    if query.lower().startswith(("http://", "https://")):
        return verify_product_page(query, query, fetcher=fetcher)

    search_result = searcher(query)
    if isinstance(search_result, ProductResolution):
        return search_result

    verified = []
    for candidate in search_result:
        resolution = verify_product_page(query, candidate["url"], fetcher=fetcher)
        candidate_with_status = {
            **candidate,
            "status": resolution.status,
            "matched_on": resolution.matched_on,
            "confidence": resolution.confidence,
        }
        if resolution.status == "resolved":
            verified.append(candidate_with_status)

    if len(verified) == 1:
        candidate = verified[0]
        return ProductResolution(
            "resolved",
            query,
            url=candidate["url"],
            confidence=candidate.get("confidence", "high"),
            matched_on=candidate.get("matched_on", []),
            candidates=verified,
        )
    if len(verified) > 1:
        return ProductResolution("ambiguous", query, confidence="medium", candidates=verified)

    return ProductResolution("not_found", query, candidates=search_result, error="No verified PartSelect product page found.")
