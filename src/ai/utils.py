"""Shared AI utility functions."""

import contextlib
import json


def _strip_reasoning_preamble(text: str) -> str:
    """Drop a reasoning-model preamble that precedes the JSON payload.

    Some providers (e.g. MiniMax) prefix JSON output inside `content` with a
    `thinking<reasoning>response` preamble. The reasoning text can contain
    braces, which breaks naive first-`{` extraction, so cut at the last
    `response` marker that is immediately followed by the JSON object.
    """
    marker = text.rfind("response")
    while marker != -1:
        rest = text[marker + len("response") :].lstrip()
        if rest.startswith("{"):
            return rest
        marker = text.rfind("response", 0, marker)
    return text


def parse_json_response(response: str) -> dict | None:
    """Try multiple strategies to extract a JSON object from an AI response.

    Returns the parsed dict, or None if all strategies fail.
    """
    text = _strip_reasoning_preamble(response.strip())

    # Strategy 1: direct parse
    with contextlib.suppress(json.JSONDecodeError, ValueError):
        return json.loads(text)

    # Strategy 2/3: extract the LAST fenced block. Reasoning preambles often
    # contain an earlier partial JSON sample (the model iterating); the real
    # answer is always the final code block.
    for fence in ("```json", "```"):
        if fence not in text:
            continue
        parts = text.split(fence)
        for block in reversed(parts[1:]):
            json_str = block.split("```")[0].strip()
            if not json_str:
                continue
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                continue

    # Strategy 4: brace-match from every '{', returning the LAST valid object.
    best: dict | None = None
    i = 0
    while True:
        start = text.find("{", i)
        if start == -1:
            break
        depth = 0
        for j in range(start, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        best = json.loads(text[start : j + 1])
                    except (json.JSONDecodeError, ValueError):
                        pass
                    i = j + 1
                    break
        else:
            break
    return best
