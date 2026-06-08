from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
import re
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


BASE_URL = "https://www.partselect.com"
SELF_SERVICE_URL = f"{BASE_URL}/user/self-service/"
INSTANT_REPAIRMAN_URL = f"{BASE_URL}/Instant-Repairman/"
REPAIR_HELP_URL = f"{BASE_URL}/Repair/"
REFRIGERATOR_REPAIR_URL = f"{BASE_URL}/Repair/Refrigerator/"
DISHWASHER_REPAIR_URL = f"{BASE_URL}/Repair/Dishwasher/"
MODEL_LOCATOR_URL = f"{BASE_URL}/Find-Your-Model-Number/"
DISHWASHER_PARTS_URL = f"{BASE_URL}/Dishwasher-Parts.htm"
REFRIGERATOR_PARTS_URL = f"{BASE_URL}/Refrigerator-Parts.htm"


SYMPTOM_SLUGS = {
    "refrigerator": [
        (("ice maker", "not making ice", "not working", "no ice"), "Not-Making-Ice"),
        (("leak", "leaking", "water leaking"), "Leaking"),
        (("not cooling", "warm", "too warm"), "Fridge-Too-Warm"),
        (("noisy", "noise", "loud"), "Noisy"),
    ],
    "dishwasher": [
        (("not draining", "won't drain", "wont drain", "water standing"), "Not-Draining"),
        (("leak", "leaking", "water leaking"), "Leaking"),
        (("not cleaning", "dirty dishes", "not cleaning dishes"), "Not-Cleaning-Dishes-Properly"),
        (("will not fill", "won't fill", "wont fill", "not filling"), "Will-not-fill-with-water"),
        (("not starting", "won't start", "wont start"), "Will-Not-Start"),
    ],
}


class PageTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._href = None
        self.text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        attr_map = dict(attrs)
        if tag == "a":
            self._href = attr_map.get("href")
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "br"}:
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "a":
            self._href = None
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4"}:
            self.text.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        clean = " ".join(data.split())
        if not clean:
            return
        self.text.append(clean)
        if self._href:
            self.links.append({"text": clean, "href": absolutize_url(self._href)})


def absolutize_url(url):
    if not url:
        return url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{BASE_URL}{url}"
    return f"{BASE_URL}/{url}"


def is_allowed_partselect_url(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc in {
        "partselect.com",
        "www.partselect.com",
    }


def fetch_partselect_page(url, timeout=12):
    if not is_allowed_partselect_url(url):
        return {"ok": False, "url": url, "text": "", "links": [], "error": "URL is not an allowed PartSelect page."}

    request = Request(url, headers={"User-Agent": "PartSelectCaseStudyBot/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return {"ok": False, "url": url, "text": "", "links": [], "error": str(exc)}

    parser = PageTextParser()
    parser.feed(html)
    text = "\n".join(" ".join(line.split()) for line in "".join(parser.text).splitlines())
    text = "\n".join(line for line in text.splitlines() if line)
    return {"ok": True, "url": url, "text": text[:50000], "links": parser.links[:200], "error": None}


def model_url(model_number):
    return f"{BASE_URL}/Models/{quote(model_number.strip().upper())}/"


def repair_appliance_url(appliance):
    if appliance == "refrigerator":
        return REFRIGERATOR_REPAIR_URL
    if appliance == "dishwasher":
        return DISHWASHER_REPAIR_URL
    return REPAIR_HELP_URL


def detect_symptom_slug(appliance, symptom_text):
    lowered = symptom_text.lower()
    for needles, slug in SYMPTOM_SLUGS.get(appliance, []):
        if any(needle in lowered for needle in needles):
            return slug
    return None


def repair_symptom_url(appliance, symptom_text):
    slug = detect_symptom_slug(appliance, symptom_text)
    if not slug:
        return None
    return f"{BASE_URL}/Repair/{appliance.title()}/{slug}/"


def model_symptom_url(model_number, symptom_text, appliance=None):
    slug = None
    if appliance:
        slug = detect_symptom_slug(appliance, symptom_text)
    if not slug:
        for candidate_appliance in SYMPTOM_SLUGS:
            slug = detect_symptom_slug(candidate_appliance, symptom_text)
            if slug:
                break
    if not slug:
        return None
    return f"{model_url(model_number)}Symptoms/{slug}/"


def extract_between(text, start_label, end_labels):
    start = text.lower().find(start_label.lower())
    if start == -1:
        return ""
    start += len(start_label)
    end = len(text)
    lowered = text.lower()
    for label in end_labels:
        idx = lowered.find(label.lower(), start)
        if idx != -1:
            end = min(end, idx)
    return text[start:end].strip()


def summarize_product_page(page):
    text = page.get("text", "")
    links = page.get("links", [])
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = next((line for line in lines if " PartSelect.com" not in line and len(line) > 8), "")
    videos = [link for link in links if "video" in link["text"].lower() or "replacing" in link["text"].lower()]
    install = extract_between(text, "Installation Instructions", ["Questions and Answers", "Model Cross Reference", "Back to Top"])
    description = extract_between(text, "Product Description", ["Related Parts", "Part Videos", "Troubleshooting"])
    troubleshooting = extract_between(text, "Troubleshooting", ["Customer Reviews", "Installation Instructions", "Questions and Answers"])
    return {
        "type": "product",
        "url": page.get("url"),
        "title": title[:180],
        "description": description[:1800],
        "installation_instructions": install[:1800],
        "troubleshooting": troubleshooting[:1500],
        "videos": videos[:5],
        "text_excerpt": text[:2500],
    }


def summarize_model_page(page):
    text = page.get("text", "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = next((line for line in lines if " - Overview" in line or "OEM Parts" in line), "")
    symptoms = extract_between(text, "Common Symptoms", ["Videos related", "Manuals", "Back to Top"])
    qa = extract_between(text, "Questions And Answers", ["Common Symptoms", "Ask a Question"])
    return {
        "type": "model",
        "url": page.get("url"),
        "title": title[:180],
        "symptoms": symptoms[:1800],
        "qa": qa[:1800],
        "text_excerpt": text[:3000],
    }


def summarize_repair_page(page):
    text = page.get("text", "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = next((line for line in lines if "Refrigerator" in line or "Dishwasher" in line or "not" in line.lower()), "")
    causes = []
    for line in lines:
        if re.search(r"(valve|filter|assembly|tube|pump|motor|switch|gasket|seal|inlet|water|ice)", line, re.I):
            if 20 <= len(line) <= 220 and line not in causes:
                causes.append(line)
        if len(causes) >= 8:
            break
    return {
        "type": "repair",
        "url": page.get("url"),
        "title": title[:180],
        "likely_causes": causes,
        "text_excerpt": text[:4000],
    }
