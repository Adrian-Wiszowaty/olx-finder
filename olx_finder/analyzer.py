import json
import logging
import re

from olx_finder import prompts
from olx_finder.ai import Message
from olx_finder.models import AnalysisPlan

log = logging.getLogger(__name__)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_json(text):
    candidates = [m.strip() for m in _FENCE.findall(text)]
    candidates.append(text.strip())
    stripped = text.strip()
    slices = []
    for opener, closer in (("[", "]"), ("{", "}")):
        start, end = stripped.find(opener), stripped.rfind(closer)
        if start != -1 and end > start:
            slices.append((start, stripped[start : end + 1]))
    candidates += [s for _, s in sorted(slices)]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


class OfferAnalyzer:
    def __init__(self, llm, batch_size=5):
        self.llm = llm
        self.batch_size = batch_size

    def build_plan(self, goal, search_url):
        reply = self.llm.complete([Message("user", prompts.plan_prompt(goal, search_url))])
        data = parse_json(reply)
        if not isinstance(data, dict):
            log.warning("Could not parse the analysis plan; using a generic one.")
            return AnalysisPlan()
        attributes = [str(a).strip() for a in data.get("attributes", []) if str(a).strip()]
        return AnalysisPlan(attributes[:10], str(data.get("guidance") or "").strip())

    def extract_specs(self, offers, plan, on_progress=None):
        indexed = list(enumerate(offers, 1))
        batches = [indexed[i : i + self.batch_size] for i in range(0, len(indexed), self.batch_size)]
        specs = {}
        for done, batch in enumerate(batches, 1):
            specs.update(self._extract_batch(batch, plan))
            if on_progress:
                on_progress(done, len(batches))
        for i, offer in indexed:
            offer.spec = specs.get(i, {})
        return offers

    def _extract_batch(self, batch, plan):
        reply = self.llm.complete(
            [Message("user", prompts.extraction_prompt(plan, batch))], temperature=0.0
        )
        data = parse_json(reply)
        if not isinstance(data, list):
            log.warning("Could not parse an extraction batch; leaving those offers blank.")
            return {}
        specs = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            offer_id = item.get("id")
            if isinstance(offer_id, str) and offer_id.isdigit():
                offer_id = int(offer_id)
            if isinstance(offer_id, int):
                specs[offer_id] = {k: v for k, v in item.items() if k != "id"}
        return specs

    def start_session(self, goal, plan, offers):
        return AnalysisSession(self.llm, prompts.session_prompt(goal, plan, offers))


class AnalysisSession:
    def __init__(self, llm, system_prompt):
        self.llm = llm
        self.messages = [Message("system", system_prompt)]

    def ranking(self, top_n=5):
        return self.ask(prompts.ranking_prompt(top_n))

    def ask(self, question):
        self.messages.append(Message("user", question))
        try:
            answer = self.llm.complete(self.messages, temperature=0.4)
        except Exception:
            self.messages.pop()
            raise
        self.messages.append(Message("assistant", answer))
        return answer
