# Design Decisions And Future Expansion

## Product URL Resolution

Initial issue: product URLs looked predictable, but they cannot be constructed from a PartSelect number alone because the slug also includes brand, manufacturer part number, and part name.

Decision: use a verified seed map for evaluator-critical parts, then OpenAI web search as the V1 product URL resolver:

1. check known verified demo mappings
2. query OpenAI web search for the official PartSelect product page
3. filter results to PartSelect product URLs matching `/PS\d+-.*\.htm`
4. fetch candidate page
5. verify that the exact identifier appears on the page
6. return resolved, ambiguous, not found, unavailable, or fetch error

Future production recommendation: replace external search with internal PartSelect catalog/product DB access or an official product search API for exact URL, price, inventory, compatibility, and product metadata.

## OpenAI Usage

OpenAI should:

- classify messy user language through the conversation context
- summarize retrieved PartSelect evidence
- write final answers conversationally

OpenAI should not:

- invent compatibility
- invent product details
- browse freely
- cite broad Repair Help pages unless fallback requires it

## Clarification Policy

For troubleshooting:

- If no model number is known, ask whether the user has it.
- If not, provide the model locator link and ask whether they want to continue without model.
- If they continue without model, provide general troubleshooting and state that exact compatible parts require model number.

For compatibility:

- If model is missing, ask for model number and offer locator link.
- If part is missing, ask for PartSelect number, manufacturer number, or product link.

For product/install:

- If part identifier is missing, ask for PartSelect number, manufacturer number, or product link.

## Future Expansion

- Internal product DB/catalog integration.
- Official PartSelect search API if available.
- Product cards with image, price, stock, and CTA.
- Embedded installation videos.
- RAG over repair guides, Q&A, and manuals.
- Browser automation fallback for dynamic pages.
- Caching for search and product fetches.
- Authenticated order lookup.
- Add-to-cart flow.
- Human handoff.
- Streaming responses.
- Analytics for failed searches, missing data, and unresolved queries.
