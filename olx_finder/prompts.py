import json

from olx_finder.models import AnalysisPlan, Offer

DESCRIPTION_LIMIT = 1500
DATASET_LIMIT = 600


def plan_prompt(goal: str, search_url: str) -> str:
    return f"""\
The user is browsing marketplace offers and wants to compare them.
Search URL (may hint at the category): {search_url}
Their goal, in their own words:
\"\"\"{goal}\"\"\"

List the attributes worth extracting from every offer description so the offers
can be compared against this goal (e.g. for a gaming PC: CPU, GPU, RAM, storage).
Pick only what matters for the goal, at most 10 attributes.

Answer with JSON only:
{{"attributes": ["...", "..."], "guidance": "one short sentence on how to judge them"}}
Use the user's language for the attributes and guidance."""


def extraction_prompt(plan: AnalysisPlan, batch: list[tuple[int, Offer]]) -> str:
    if plan.attributes:
        wanted = "\n".join(f"- {a}" for a in plan.attributes)
        instruction = f"Extract these attributes from every offer below:\n{wanted}"
    else:
        instruction = "Extract the attributes most useful for comparing the offers below."
    blocks = []
    for offer_id, offer in batch:
        description = offer.description[:DESCRIPTION_LIMIT] or "(no description)"
        blocks.append(
            f"### Offer {offer_id}\nTitle: {offer.title}\nPrice: {offer.price}\n"
            f"Description:\n{description}"
        )
    offers = "\n\n".join(blocks)
    return f"""\
{instruction}

Rules:
- Use null when an offer does not mention an attribute. Never guess.
- Keep values short (a few words).
- Answer with JSON only: one object per offer, e.g. [{{"id": 1, "<attribute>": "<value>"}}]

{offers}"""


def session_prompt(goal: str, plan: AnalysisPlan, offers: list[Offer]) -> str:
    dataset = [
        {
            "id": index,
            "title": offer.title,
            "price": offer.price,
            "url": offer.url,
            "attributes": offer.spec,
            "description_excerpt": offer.description[:DATASET_LIMIT],
        }
        for index, offer in enumerate(offers, 1)
    ]
    guidance = f"\nHow to judge them: {plan.guidance}" if plan.guidance else ""
    return f"""\
You are a careful shopping assistant. You analyzed real marketplace offers for
the user and now answer questions about them.

The user's goal: {goal}{guidance}

Offers (JSON):
{json.dumps(dataset, ensure_ascii=False)}

Rules:
- Base every answer only on the offers above. If something is missing, say so.
- The "id" field is internal bookkeeping only — never show it to the user as an
  "offer number". When you rank or list a subset of offers, number that subset
  1, 2, 3... by its own order, and refer back to those same numbers everywhere
  else in your answer (e.g. in an overall recommendation).
- When recommending offers, always include the title, price and URL.
- Answer in the user's language and be concise; use Markdown lists for rankings."""


def ranking_prompt(top_n: int) -> str:
    return (
        f"Rank the offers against my goal and show the top {top_n} (best first), "
        f"numbered 1 to {top_n} by rank — not by their id in the offers dataset. "
        "For each give the rank number, title, price, URL and a one-sentence reason.\n\n"
        "Then end with an overall recommendation of exactly 3 sentences that argues the "
        "choice in depth, using concrete details from the offers (not generic praise): "
        "explain what actually makes offer 1 the best pick, and explicitly weigh it "
        "against the runner-up — say plainly whether offer 1 clearly beats offer 2, "
        "whether they are practically tied, or whether several of the top picks are "
        "essentially equivalent and it barely matters which one the user takes. Refer "
        "back to the same rank numbers (e.g. \"offer 2\"), never the dataset id. Give "
        "the single most useful, decisive answer you can, not a vague summary."
    )
