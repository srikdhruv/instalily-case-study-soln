# PartSelect Chat Agent Architecture

## Goal

Build a simple, accurate, functional chat agent for PartSelect refrigerator and dishwasher support. The agent helps with troubleshooting, part/model information, compatibility, installation help, and purchase/self-service linkouts while refusing unrelated requests.

## Stack

- React frontend using the provided chat template.
- Python FastAPI backend.
- Direct OpenAI API integration through `OPENAI_API_KEY`.
- Product URL resolver through seeded known examples plus OpenAI web search using `OPENAI_API_KEY`.
- Per-turn Python flow controller that re-checks intent, context switching, known slots, missing slots, and retrieval needs.
- Standard-library PartSelect page fetcher/parser for V1.
- No LangChain or LangGraph in the initial build.

## Request Flow

1. React sends `session_id`, full `messages` conversation history, and the current flow to `POST /chat`.
2. FastAPI passes the request to the flow controller.
3. The controller applies guardrails, detects identifiers from the full conversation, routes the current turn, asks for missing required information, runs allowed PartSelect tools, and composes a grounded response.
4. If `OPENAI_API_KEY` is available, OpenAI rewrites/summarizes from supplied evidence. If not, deterministic fallback responses are returned.
5. The frontend renders the assistant message, sources, and suggested replies.

## Major Flows

- Troubleshooting: collect appliance type and symptom, optionally model number, then use real PartSelect repair/model/parts pages.
- Information-seeking: answer part, model, installation, video, compatibility, and model-number locator questions.
- Part purchase/search: resolve part/model/manufacturer numbers and return real product/search links for purchase on PartSelect.

## Grounded PartSelect Links

- Home: https://www.partselect.com/
- Repair Help: https://www.partselect.com/Repair/
- Instant Repairman: https://www.partselect.com/Instant-Repairman/
- Model Number Locator: https://www.partselect.com/Find-Your-Model-Number/
- Self-Service / Order Status: https://www.partselect.com/user/self-service/
- Dishwasher Parts: https://www.partselect.com/Dishwasher-Parts.htm
- Refrigerator Parts: https://www.partselect.com/Refrigerator-Parts.htm

## Guardrails

- Only support PartSelect product, repair, installation, compatibility, purchase, and self-service questions.
- Only support refrigerator and dishwasher as the primary appliance categories.
- Never guess compatibility. Return `cannot_verify` when product/model evidence is insufficient.
- Fetch only approved PartSelect URLs.
- Ask for one missing field at a time.
- Allow context switching and restart commands.
- Broad Repair Help pages are internal discovery/fallback links; specific symptom, product, model, locator, self-service, and Instant Repairman links are preferred for user-facing sources.

## Product URL Resolver

PartSelect product URLs include slug data that is not known from the PartSelect number alone, such as brand, manufacturer part number, and product name. V1 resolves product numbers through seeded known examples plus OpenAI web search:

1. Check a tiny verified seed map for evaluator-critical parts.
2. Query OpenAI web search for the official PartSelect product page.
3. Keep only PartSelect product URLs matching `/PS\d+-.*\.htm`.
4. Fetch each candidate page.
5. Trust it only if the page contains the exact requested identifier.
6. Ask for a direct product link when search is unavailable or no verified candidate is found.

## Planned Later

- Product cards, images, price/stock UI, and non-text buttons.
- Embedded videos.
- UI polish and PartSelect branding.
- Browser automation.
- Scrape/result caching.
- RAG/catalog indexing.
- Authenticated order lookup.
- Add-to-cart from chat.
- Streaming responses.
- Human handoff.
- Evaluation and analytics.
