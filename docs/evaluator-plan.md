# PartSelect Chat Agent Evaluator Plan

## Summary

This case study builds a scoped PartSelect chat agent for refrigerator and dishwasher support. The assistant helps users troubleshoot appliance issues, look up product/model information, check compatibility, get installation guidance, and navigate order self-service. The system prioritizes simple, accurate, source-grounded answers over broad autonomous browsing.

## Architecture

- Frontend: React chat interface using the provided template.
- Backend: Python FastAPI service.
- LLM: Direct OpenAI API for grounded answer generation.
- Flow control: human-designed policy engine with per-turn intent detection and slot checking.
- Retrieval: PartSelect page fetchers plus seeded examples and OpenAI web search for resolving product URLs from part numbers.
- Config: `.env` for `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_SEARCH_MODEL`.

## Core Design Choice

Flows are not rigid scripts. On every user turn, the backend re-evaluates:

- current user intent
- whether the user context-switched
- known information from conversation history
- missing required information
- available retrieval tools
- whether enough evidence exists to answer

If required information is missing, the agent asks one focused clarification. If enough information exists, it retrieves evidence and answers immediately.

## Main Flows

- Troubleshooting / repair diagnosis: collect appliance, symptom, brand/model if available; clarify model number; use model-specific symptom pages when possible and general symptom pages when the user proceeds without model.
- Product information: resolve product page, extract product details, symptoms fixed, manufacturer number, videos, and install information.
- Installation help: resolve product page, extract instructions/videos, summarize installation steps, and offer compatibility check.
- Compatibility check: require part identifier and model number; fetch product and model evidence; never claim compatibility unless verified.
- Part search / purchase guidance: help users find parts by product number, manufacturer number, model, symptom, appliance, or brand; route purchase to PartSelect product pages.
- Model information: use `https://www.partselect.com/Models/{MODEL_NUMBER}/`.
- Model number locator: link to `https://www.partselect.com/Find-Your-Model-Number/`.
- Self-service / order support: link to `https://www.partselect.com/user/self-service/`.
- Instant Repairman: link to `https://www.partselect.com/Instant-Repairman/`.
- Guardrails / restart: refuse unrelated requests and support “start over,” “new issue,” or context switching.

## URL Strategy

- Hardcoded stable links:
  - Home: `https://www.partselect.com/`
  - Self-service: `https://www.partselect.com/user/self-service/`
  - Instant Repairman: `https://www.partselect.com/Instant-Repairman/`
  - Model locator: `https://www.partselect.com/Find-Your-Model-Number/`
- Constructed model URLs:
  - `https://www.partselect.com/Models/{MODEL_NUMBER}/`
- Specific repair/symptom URLs:
  - used when found, for example `https://www.partselect.com/Repair/Refrigerator/Not-Making-Ice/`
- Broad Repair Help URLs:
  - used internally for discovery only; not shown unless no specific source is found.
- Product URLs:
  - not constructed directly from part number.
  - resolved through a verified seed map first, then OpenAI web search.
  - accepted only after URL pattern and page-content verification.

## Acceptance Targets

Primary manual prompts:

- “How can I install part number PS11752778?”
- “Is this part compatible with my WDT780SAEM1 model?”
- “The ice maker on my Whirlpool fridge is not working. How can I fix it?”

Expected behavior:

- installation prompt resolves the real product page and answers from install evidence.
- compatibility prompt uses prior context if needed, fetches product/model evidence, and is conservative.
- troubleshooting prompt asks about model number first, offers locator/continue-without-model, then uses specific symptom evidence.
