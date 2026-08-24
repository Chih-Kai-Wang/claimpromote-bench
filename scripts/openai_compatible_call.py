"""Minimal OpenAI-compatible transport that retains only final text and safe metadata."""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from typing import Any

Json = dict[str, Any]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _http_json(url: str, body: Json, api_key: str, timeout: float) -> Json:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ClaimPromoteBench-UpstreamRepetition/1",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise RuntimeError(f"transport failure: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("provider returned non-JSON HTTP content") from exc
    if not isinstance(value, dict):
        raise RuntimeError("provider response must be a JSON object")
    if value.get("error") is not None:
        raise RuntimeError(f"provider returned an error: {value['error']}")
    return value


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def call_openai_compatible(
    lane: Json, body: Json, api_key: str, timeout: float
) -> tuple[Json, str | None, Json]:
    """Call one route once, discarding response IDs and hidden-reasoning fields."""

    response = _http_json(
        str(lane["base_url"]).rstrip("/") + "/chat/completions",
        body,
        api_key,
        timeout,
    )
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("provider response lacks choices[0].message")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("provider response lacks choices[0].message")
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise RuntimeError("provider final content is not text")
    usage_raw = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    prompt_details = usage_raw.get("prompt_tokens_details")
    completion_details = usage_raw.get("completion_tokens_details")
    usage = {
        "input_tokens": _integer(usage_raw.get("prompt_tokens")),
        "cached_input_tokens": _integer(
            prompt_details.get("cached_tokens") if isinstance(prompt_details, dict) else None
        ),
        "output_tokens": _integer(usage_raw.get("completion_tokens")),
        "reasoning_tokens": _integer(
            completion_details.get("reasoning_tokens")
            if isinstance(completion_details, dict)
            else None
        ),
        "total_tokens": _integer(usage_raw.get("total_tokens")),
    }
    metadata = {
        "model_returned": response.get("model") if isinstance(response.get("model"), str) else None,
        "routed_provider": (
            response.get("provider") if isinstance(response.get("provider"), str) else None
        ),
        "finish_reason": (
            choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) else None
        ),
    }
    return metadata, content, usage
