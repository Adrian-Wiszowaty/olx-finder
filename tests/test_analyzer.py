import json

from conftest import FakeLLM

from olx_finder.analyzer import OfferAnalyzer
from olx_finder.models import AnalysisPlan


def test_build_plan_reads_json_in_a_code_fence():
    fake = FakeLLM(['```json\n{"attributes": ["CPU", "GPU"], "guidance": "Prefer newer."}\n```'])
    plan = OfferAnalyzer(fake).build_plan("best gaming pc", "https://www.olx.pl/x")

    assert plan.attributes == ["CPU", "GPU"]
    assert plan.guidance == "Prefer newer."


def test_build_plan_falls_back_when_response_is_not_json():
    plan = OfferAnalyzer(FakeLLM(["no json here"])).build_plan("goal", "https://www.olx.pl/x")
    assert plan == AnalysisPlan()


def test_plan_prompt_mentions_goal_and_url():
    fake = FakeLLM(['{"attributes": [], "guidance": ""}'])
    OfferAnalyzer(fake).build_plan("cheap warm jacket", "https://www.olx.pl/jackets")

    prompt = fake.calls[0][0].content
    assert "cheap warm jacket" in prompt
    assert "https://www.olx.pl/jackets" in prompt


def test_extract_specs_batches_and_maps_results_by_id(make_offer):
    offers = [make_offer(i) for i in range(1, 6)]
    fake = FakeLLM([
        json.dumps([{"id": 1, "cpu": "i5"}, {"id": 2, "cpu": "i7"}]),
        json.dumps([{"id": "3", "cpu": "i3"}, {"id": 4, "cpu": None}]),
        "not json",
    ])
    progress = []

    analyzed = OfferAnalyzer(fake, batch_size=2).extract_specs(
        offers, AnalysisPlan(["cpu"]), on_progress=lambda d, t: progress.append((d, t))
    )

    assert len(fake.calls) == 3
    assert analyzed is offers
    assert offers[0].spec == {"cpu": "i5"}
    assert offers[2].spec == {"cpu": "i3"}
    assert offers[4].spec == {}
    assert progress == [(1, 3), (2, 3), (3, 3)]
