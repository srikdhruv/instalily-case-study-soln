import re
from dataclasses import dataclass

from .openai_client import call_openai
from .partselect import (
    DISHWASHER_PARTS_URL,
    INSTANT_REPAIRMAN_URL,
    MODEL_LOCATOR_URL,
    REFRIGERATOR_PARTS_URL,
    SELF_SERVICE_URL,
    fetch_partselect_page,
    model_symptom_url,
    model_url,
    repair_appliance_url,
    repair_symptom_url,
    summarize_model_page,
    summarize_product_page,
    summarize_repair_page,
)
from .product_resolver import resolve_product_url, seeded_product_evidence


PARTSELECT_RE = re.compile(r"\bPS\d{5,}\b", re.I)
MODEL_RE = re.compile(r"\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{6,16}\b", re.I)
MFG_PART_RE = re.compile(r"\b(?:WP)?W?\d{6,}|[A-Z]{1,4}\d{5,}[A-Z0-9]*\b", re.I)
URL_RE = re.compile(r"https?://(?:www\.)?partselect\.com/[^\s)]+", re.I)


@dataclass
class AgentResult:
    role: str
    content: str
    flow: str
    sources: list
    suggested_replies: list

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "flow": self.flow,
            "sources": self.sources,
            "suggested_replies": self.suggested_replies,
        }


def source(label, url):
    return {"label": label, "url": url}


def last_user_message(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def user_history(messages):
    return "\n".join(message.get("content", "") for message in messages if message.get("role") == "user")


def classify_identifier(text):
    upper = text.upper()
    urls = URL_RE.findall(text)
    ps_numbers = [match.upper() for match in PARTSELECT_RE.findall(upper)]
    model_candidates = [match.upper() for match in MODEL_RE.findall(upper)]
    model_numbers = [
        value
        for value in model_candidates
        if value not in ps_numbers and not value.startswith("WPW") and not value.startswith("PS")
    ]
    manufacturer_numbers = [
        match.upper()
        for match in MFG_PART_RE.findall(upper)
        if match.upper() not in ps_numbers and match.upper() not in model_numbers
    ]
    lowered = text.lower()
    appliance = None
    if "dishwasher" in lowered:
        appliance = "dishwasher"
    elif "refrigerator" in lowered or "fridge" in lowered:
        appliance = "refrigerator"

    return {
        "urls": urls,
        "partselect_numbers": ps_numbers,
        "model_numbers": model_numbers,
        "manufacturer_part_numbers": manufacturer_numbers,
        "appliance_type": appliance,
    }


def merged_slots(messages):
    latest = classify_identifier(last_user_message(messages))
    history = classify_identifier(user_history(messages))
    return {
        "latest": latest,
        "history": history,
        "part_identifier": first(latest["partselect_numbers"] or latest["manufacturer_part_numbers"] or latest["urls"])
        or first(history["partselect_numbers"] or history["manufacturer_part_numbers"] or history["urls"]),
        "model_number": first(latest["model_numbers"]) or first(history["model_numbers"]),
        "appliance_type": latest["appliance_type"] or history["appliance_type"],
    }


def first(values):
    return values[0] if values else None


def route_intent(text, current_flow=None):
    lowered = text.lower()
    if any(term in lowered for term in ["start over", "restart", "new issue", "forget that"]):
        return "restart"
    if any(term in lowered for term in ["order status", "track my order", "return", "cancel an order", "shipping status"]):
        return "self_service"
    if "instant repairman" in lowered:
        return "instant_repairman"
    if any(term in lowered for term in ["find my model", "where is my model", "where do i find", "model number locator"]):
        return "model_locator"
    if any(term in lowered for term in ["compatible", "compatibility", "fit", "fits"]):
        return "compatibility"
    if any(term in lowered for term in ["install", "installation", "video", "replace", "replacing"]):
        return "installation"
    if any(term in lowered for term in ["buy", "purchase", "search", "find a part", "part for", "price", "stock", "cart"]):
        return "purchase_search"
    if any(
        term in lowered
        for term in [
            "not working",
            "leaking",
            "not draining",
            "not making ice",
            "won't",
            "wont",
            "broken",
            "repair",
            "troubleshoot",
            "diagnose",
            "symptom",
            "ice maker",
        ]
    ):
        return "troubleshoot"
    return current_flow or "information"


def is_out_of_scope(text, slots):
    lowered = text.lower()
    if wants_continue_without_model(text) and slots["history"]["appliance_type"]:
        return False
    if any(slots["latest"][key] for key in ["urls", "partselect_numbers", "model_numbers", "manufacturer_part_numbers"]):
        return False
    in_scope_terms = [
        "part",
        "model",
        "install",
        "compatible",
        "fit",
        "order",
        "return",
        "shipping",
        "track",
        "repair",
        "troubleshoot",
        "leak",
        "ice maker",
        "not working",
        "dishwasher",
        "refrigerator",
        "fridge",
        "water filter",
        "cart",
        "buy",
        "purchase",
        "partselect",
        "continue without model",
    ]
    return not any(term in lowered for term in in_scope_terms)


def wants_continue_without_model(text):
    lowered = text.lower()
    return "continue without" in lowered or "proceed without" in lowered or "without model" in lowered


def linkout_response(flow, title, url, details):
    return AgentResult(
        "assistant",
        f"{details}\n\nOfficial PartSelect link: {url}",
        flow,
        [source(title, url)],
        ["I need help finding a part", "Help me troubleshoot", "Start over"],
    )


def ask_for_missing(flow, content, suggestions=None, sources=None):
    return AgentResult("assistant", content, flow, sources or [], suggestions or ["Start over"])


def ask_for_model_number(flow, appliance=None):
    appliance_text = f" for your {appliance}" if appliance else ""
    return ask_for_missing(
        flow,
        (
            f"Do you have the model number{appliance_text}? It lets me find exact PartSelect parts and compatibility. "
            "If you do, send it here. If not, use the model-number locator below, or say \"continue without model\" "
            "and I can give general guidance."
        ),
        ["I found the model number", "Continue without model", "Where do I find my model number?"],
        [source("PartSelect model number locator", MODEL_LOCATOR_URL)],
    )


def product_resolution_failure(resolution, flow):
    if resolution.status == "search_unavailable":
        return ask_for_missing(
            flow,
            (
                "I need a verified PartSelect product page before I can answer from product evidence. "
                "Please add OPENAI_API_KEY for product lookup, or send the direct PartSelect product link."
            ),
            ["Where do I find my model number?", "Start over"],
        )
    if resolution.status == "fetch_error":
        return ask_for_missing(
            flow,
            (
                "I could not use the product search resolver right now. Please check the OpenAI key, "
                "search model access, or send the direct PartSelect product link."
            ),
            ["Try a direct product link", "Start over"],
        )
    if resolution.status == "ambiguous":
        links = "\n".join(f"- {candidate['title']}: {candidate['url']}" for candidate in resolution.candidates[:3])
        return ask_for_missing(flow, f"I found multiple matching PartSelect products. Which one do you mean?\n\n{links}")
    return ask_for_missing(
        flow,
        "I could not resolve that to a verified PartSelect product page. Please send a direct product link, PartSelect number, or manufacturer part number.",
        ["Try another part number", "Start over"],
    )


def resolve_and_fetch_product(identifier):
    resolution = resolve_product_url(identifier)
    if resolution.status != "resolved":
        return resolution, None, None
    page = fetch_partselect_page(resolution.url)
    if not page.get("ok"):
        return resolution, page, seeded_product_evidence(identifier)
    return resolution, page, summarize_product_page(page)


def build_product_answer(messages, slots, flow):
    identifier = slots["part_identifier"]
    if not identifier:
        return ask_for_missing(
            flow,
            "Please send the PartSelect number, manufacturer part number, or direct PartSelect product link.",
            ["Where do I find my model number?", "Start over"],
        )

    resolution, page, product = resolve_and_fetch_product(identifier)
    if resolution.status != "resolved":
        return product_resolution_failure(resolution, flow)
    if not product:
        product = {
            "type": "product",
            "url": resolution.url,
            "title": resolution.url.rsplit("/", 1)[-1].replace(".htm", "").replace("-", " "),
            "description": "I found the PartSelect product URL, but could not fetch the page body from this environment.",
            "installation_instructions": "",
            "troubleshooting": "",
            "videos": [],
            "text_excerpt": "Product URL resolved, page body unavailable.",
        }

    evidence = {"product_resolution": resolution.to_dict(), "product": product}
    if flow == "installation":
        fallback = (
            f"I found the verified PartSelect product page for {identifier}.\n\n"
            f"{product.get('installation_instructions') or product.get('description') or 'The page did not expose detailed installation text, but it may include install media or customer instructions.'}\n\n"
            f"Source: {resolution.url}"
        )
        suggestions = ["Check compatibility", "Find another part", "Start over"]
    else:
        fallback = (
            f"I found the verified PartSelect product page for {identifier}: {product.get('title') or resolution.url}.\n\n"
            f"{product.get('description') or product.get('text_excerpt')}\n\n"
            f"Source: {resolution.url}"
        )
        suggestions = ["Show installation help", "Check compatibility", "Find another part"]

    content = call_openai(messages, evidence, fallback, task=flow)
    return AgentResult("assistant", content, flow, [source("PartSelect product page", resolution.url)], suggestions)


def build_model_answer(messages, slots, flow="model_info"):
    model = slots["model_number"]
    if not model:
        return ask_for_model_number(flow, slots.get("appliance_type"))
    url = model_url(model)
    page = fetch_partselect_page(url)
    if not page.get("ok"):
        return ask_for_missing(flow, f"I could not fetch the PartSelect model page right now. Try this model page directly: {url}", sources=[source("PartSelect model page", url)])
    model_summary = summarize_model_page(page)
    fallback = (
        f"I found the PartSelect model page for {model}.\n\n"
        f"{model_summary.get('title') or 'The page includes model-specific parts, symptoms, videos, and instructions.'}\n\n"
        f"Source: {url}"
    )
    content = call_openai(messages, {"model": model_summary}, fallback, task=flow)
    return AgentResult("assistant", content, flow, [source("PartSelect model page", url)], ["Troubleshoot this model", "Search parts for this model"])


def category_from_text(text):
    lowered = text.lower()
    if "refrigerator" in lowered or "fridge" in lowered:
        return "refrigerator"
    if "dishwasher" in lowered:
        return "dishwasher"
    return None


def category_from_model_number(model_number):
    upper = model_number.upper()
    dishwasher_prefixes = ("WDT", "WDF", "MDB", "GDT", "KDTE", "KDTM")
    refrigerator_prefixes = ("WRF", "WRS", "WRT", "WRX", "KRFF", "KRMF")
    if upper.startswith(dishwasher_prefixes):
        return "dishwasher"
    if upper.startswith(refrigerator_prefixes):
        return "refrigerator"
    return None


def product_identity(product, identifier, url):
    product = product or {}
    return {
        "title": product.get("title") or url.rsplit("/", 1)[-1].replace(".htm", "").replace("-", " "),
        "part_identifier": identifier,
        "partselect_number": product.get("partselect_number"),
        "manufacturer_part_number": product.get("manufacturer_part_number"),
        "category": category_from_text(" ".join(str(product.get(key, "")) for key in ["title", "description", "text_excerpt"])),
        "url": url,
    }


def model_identity(model_summary, model_number):
    model_summary = model_summary or {}
    evidence_text = " ".join(str(model_summary.get(key, "")) for key in ["title", "text_excerpt", "symptoms"])
    return {
        "model_number": model_number,
        "title": model_summary.get("title") or f"Model {model_number}",
        "category": category_from_text(evidence_text) or category_from_model_number(model_number),
        "url": model_summary.get("url") or model_url(model_number),
    }


def build_compatibility_answer(messages, slots):
    if not slots["part_identifier"]:
        return ask_for_missing(
            "compatibility",
            "Which part should I check? Send a PartSelect number, manufacturer part number, or direct product link.",
            ["Start over"],
        )
    if not slots["model_number"]:
        return ask_for_model_number("compatibility", slots.get("appliance_type"))

    resolution, product_page, product = resolve_and_fetch_product(slots["part_identifier"])
    if resolution.status != "resolved":
        return product_resolution_failure(resolution, "compatibility")

    model_page_url = model_url(slots["model_number"])
    model_page = fetch_partselect_page(model_page_url)
    model_summary = summarize_model_page(model_page) if model_page.get("ok") else {"url": model_page_url, "error": model_page.get("error")}

    product_text = product_page.get("text", "").upper() if product_page else ""
    model_text = model_page.get("text", "").upper() if model_page else ""
    model = slots["model_number"].upper()
    part = slots["part_identifier"].upper()
    product_info = product_identity(product, slots["part_identifier"], resolution.url)
    model_info = model_identity(model_summary, model)

    product_category = product_info["category"] or category_from_text(product_page.get("text", "") if product_page else "")
    model_category = model_info["category"] or category_from_text(model_page.get("text", "") if model_page else "")
    if product_category and model_category and product_category != model_category:
        verdict = "no"
        explanation = f"The product is for a {product_category}, while model {model} is a {model_category}."
    elif product_page and product_page.get("ok") and model in product_text:
        verdict = "yes"
        explanation = f"The product page references model {model}."
    elif model_page and model_page.get("ok") and part in model_text:
        verdict = "yes"
        explanation = f"The model page references {part}."
    else:
        verdict = "cannot_verify"
        explanation = "I could not find direct retrieved evidence that this part fits that model."

    decision_label = {"yes": "Yes", "no": "No", "cannot_verify": "I can't verify"}[verdict]
    fallback = (
        f"Decision: **{decision_label}**.\n\n"
        f"Product checked: {product_info['title']} ({slots['part_identifier']}).\n"
        f"Model checked: {model_info['title']} ({model}).\n\n"
        f"Why: {explanation}"
        + (" I would not order until the PartSelect product/model evidence confirms the fit." if verdict == "cannot_verify" else "")
        + "\n\n"
        f"Sources:\n- {resolution.url}\n- {model_page_url}"
    )
    evidence = {
        "verdict": verdict,
        "decision": decision_label,
        "explanation": explanation,
        "product_checked": product_info,
        "model_checked": model_info,
        "product_resolution": resolution.to_dict(),
        "product": product,
        "model": model_summary,
    }
    content = fallback if verdict == "no" else call_openai(messages, evidence, fallback, task="compatibility")
    return AgentResult(
        "assistant",
        content,
        "compatibility",
        [source("PartSelect product page", resolution.url), source("PartSelect model page", model_page_url)],
        ["Help me install this part", "Find another part", "Start over"],
    )


def build_troubleshooting_answer(messages, slots):
    latest_text = last_user_message(messages)
    history_text = user_history(messages)
    symptom_text = latest_text if not wants_continue_without_model(latest_text) else history_text
    appliance = slots["appliance_type"]
    if appliance == "fridge":
        appliance = "refrigerator"
    if not appliance:
        return ask_for_missing(
            "troubleshoot",
            "Which appliance are we troubleshooting: refrigerator or dishwasher?",
            ["Refrigerator", "Dishwasher", "Start over"],
        )

    if not slots["model_number"] and not wants_continue_without_model(latest_text):
        return ask_for_model_number("troubleshoot", appliance)

    urls_to_fetch = []
    if slots["model_number"]:
        urls_to_fetch.append(model_url(slots["model_number"]))
        model_symptom = model_symptom_url(slots["model_number"], symptom_text, appliance)
        if model_symptom:
            urls_to_fetch.append(model_symptom)

    general_symptom = repair_symptom_url(appliance, symptom_text)
    if general_symptom:
        urls_to_fetch.append(general_symptom)
    if not urls_to_fetch:
        urls_to_fetch.append(repair_appliance_url(appliance))

    evidence = []
    sources = []
    used_specific_source = False
    specific_fallback_sources = []
    for url in urls_to_fetch:
        if "/Symptoms/" in url or ("/Repair/" in url and url != repair_appliance_url(appliance)):
            specific_fallback_sources.append(source("PartSelect symptom page", url))
        page = fetch_partselect_page(url)
        if not page.get("ok"):
            continue
        if "/Models/" in url and "/Symptoms/" not in url:
            evidence.append(summarize_model_page(page))
            sources.append(source("PartSelect model page", url))
        else:
            evidence.append(summarize_repair_page(page))
            label = "PartSelect symptom page" if "/Repair/" in url or "/Symptoms/" in url else "PartSelect repair page"
            sources.append(source(label, url))
            used_specific_source = "/Repair/" in url and url != repair_appliance_url(appliance) or "/Symptoms/" in url

    if not evidence:
        if specific_fallback_sources:
            sources = specific_fallback_sources
            fallback = (
                "I found the likely specific PartSelect symptom page, but could not retrieve its page text right now. "
                f"You can open it here: {specific_fallback_sources[0]['url']}"
            )
        else:
            broad_url = repair_appliance_url(appliance)
            sources = [source("PartSelect repair help", broad_url)]
            fallback = (
                f"I could not identify a specific symptom page right now. The broad PartSelect {appliance} repair page may help: {broad_url}"
            )
        return AgentResult("assistant", fallback, "troubleshoot", sources, ["Where do I find my model number?", "Start over"])

    if not used_specific_source:
        sources = [src for src in sources if "model page" in src["label"].lower()] or [source("PartSelect repair help", repair_appliance_url(appliance))]

    model_note = "" if slots["model_number"] else " Exact compatible parts require your model number."
    fallback = (
        f"I can help troubleshoot this {appliance} issue.{model_note}\n\n"
        "Based on retrieved PartSelect evidence, start with the likely causes and checks shown in the source evidence. "
        "Send your model number when you want exact compatible parts."
    )
    content = call_openai(
        messages,
        {"appliance": appliance, "symptom": symptom_text, "model_number": slots["model_number"], "evidence": evidence},
        fallback,
        task="troubleshooting",
    )
    return AgentResult(
        "assistant",
        content,
        "troubleshoot",
        sources,
        ["I found the model number", "Search likely parts", "Start over"],
    )


def handle_chat(messages, current_flow=None):
    user_text = last_user_message(messages)
    if not user_text.strip():
        return AgentResult("assistant", "Please send a question about a refrigerator or dishwasher part.", "idle", [], [])

    slots = merged_slots(messages)
    intent = route_intent(user_text, current_flow)

    if intent == "restart":
        return AgentResult(
            "assistant",
            "Sure. What can I help with: troubleshooting, part information, compatibility, installation, or order self-service?",
            "idle",
            [],
            ["Troubleshoot", "Check compatibility", "Order status"],
        )

    if is_out_of_scope(user_text, slots):
        return AgentResult(
            "assistant",
            "I can help with PartSelect refrigerator and dishwasher parts, repair help, compatibility, installation, purchase guidance, and order self-service. What appliance or part are you working on?",
            "out_of_scope",
            [source("PartSelect", "https://www.partselect.com/")],
            ["Troubleshoot a refrigerator", "Troubleshoot a dishwasher", "Check order status"],
        )

    if wants_continue_without_model(user_text) and current_flow == "troubleshoot":
        intent = "troubleshoot"

    if intent == "self_service":
        return linkout_response(
            "self_service",
            "PartSelect self-service",
            SELF_SERVICE_URL,
            "Use PartSelect self-service to check order status, track shipping, start or check a return, or cancel an order.",
        )
    if intent == "instant_repairman":
        return linkout_response(
            "instant_repairman",
            "PartSelect Instant Repairman",
            INSTANT_REPAIRMAN_URL,
            "PartSelect Instant Repairman is the official model-first flow for choosing a symptom and finding a likely repair part.",
        )
    if intent == "model_locator":
        return linkout_response(
            "model_locator",
            "PartSelect model number locator",
            MODEL_LOCATOR_URL,
            "PartSelect provides appliance-specific diagrams for locating your model number tag. Choose Refrigerator or Dishwasher on the locator page.",
        )
    if intent == "compatibility":
        return build_compatibility_answer(messages, slots)
    if intent == "troubleshoot":
        return build_troubleshooting_answer(messages, slots)
    if intent == "installation":
        return build_product_answer(messages, slots, "installation")
    if intent == "purchase_search":
        if slots["part_identifier"]:
            return build_product_answer(messages, slots, "purchase_search")
        if slots["model_number"]:
            return build_model_answer(messages, slots, "purchase_search")
        return ask_for_model_number("purchase_search", slots.get("appliance_type"))
    if slots["model_number"] and not slots["part_identifier"]:
        return build_model_answer(messages, slots, "model_info")
    return build_product_answer(messages, slots, "information")
