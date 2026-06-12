from olx_finder.analyzer import parse_json


def test_plain_json():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    assert parse_json("```json\n[1, 2]\n```") == [1, 2]


def test_fence_without_language():
    assert parse_json('```\n{"a": true}\n```') == {"a": True}


def test_json_inside_prose():
    assert parse_json('Here you go:\n{"items": [1, 2]}\nHope it helps!') == {"items": [1, 2]}


def test_plain_text_returns_none():
    assert parse_json("no json here") is None
