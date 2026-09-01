"""Tests for shared AI parsing utilities."""

from src.ai.utils import parse_json_response


def test_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_json_in_code_fence():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_minimax_thinking_preamble_is_stripped():
    # Captured from MiniMax-M3 via the OpenAI-compatible endpoint: the
    # reasoning text can contain braces, which breaks naive extraction.
    raw = (
        " thinkingThe user wants me to return JSON. They said return "
        '{"answer": 42} in the format. response\n\n'
        '{"title": "", "block": {"id": "summary"}}'
    )
    assert parse_json_response(raw) == {
        "title": "",
        "block": {"id": "summary"},
    }


def test_preamble_where_reasoning_mentions_response():
    # The word "response" may appear inside the reasoning; only the final
    # marker directly followed by the JSON object should be used.
    raw = (
        " thinkingThe response should be concise. Now emit the result. "
        'response\n\n{"ok": true}'
    )
    assert parse_json_response(raw) == {"ok": True}


def test_unparseable_returns_none():
    assert parse_json_response("no json here") is None
