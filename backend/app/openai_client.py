import json
import os

from . import config  # noqa: F401


SYSTEM_PROMPT = """You are a scoped PartSelect chat assistant for refrigerator and dishwasher parts.
Use the supplied evidence and links to answer clearly and helpfully.
For product information, describe what the product is, known part numbers, appliance category, likely use, and available install notes from evidence.
If evidence is missing, say what you can verify and ask for the next needed detail.
Do not answer unrelated questions.
For compatibility questions, give a clear Decision: Yes, No, or I can't verify.
Say No when retrieved evidence shows an appliance/category mismatch.
Say I can't verify when evidence is insufficient or unavailable.
If exact compatible parts require a model number, say that plainly."""


TASK_INSTRUCTIONS = {
    "compatibility": (
        "Answer in this shape: Decision: Yes / No / I can't verify. Then list Product checked and Model checked, "
        "including names/numbers available in evidence. Explain why in 1-3 sentences. Use No for clear appliance/category mismatch."
    ),
    "installation": (
        "Give practical installation guidance from evidence. If evidence is seeded or limited, say it is general and recommend confirming model fit."
    ),
    "information": (
        "Describe the product naturally from evidence. Include what it is, part numbers, appliance category, likely use, and source."
    ),
    "purchase_search": (
        "Summarize the product/search result and direct purchase to PartSelect. Recommend model verification before ordering."
    ),
    "troubleshooting": (
        "Give actionable troubleshooting guidance from retrieved repair evidence. If model is missing, keep exact part compatibility caveated."
    ),
}


def call_openai(messages, evidence, fallback, task="grounded_answer"):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback

    try:
        from openai import OpenAI
    except Exception:
        return fallback

    client = OpenAI(api_key=api_key)
    payload = {
        "conversation": messages[-10:],
        "evidence": evidence,
        "task": task,
        "instruction": TASK_INSTRUCTIONS.get(task, "") + " " + (
            "Return a grounded chat response. Use the evidence first, ask for missing critical info when needed, "
            "and include only the source links supplied in evidence."
        ),
    }

    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
                ],
                temperature=0.2,
            )
            return response.output_text.strip() or fallback

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip() or fallback
    except Exception:
        return fallback
