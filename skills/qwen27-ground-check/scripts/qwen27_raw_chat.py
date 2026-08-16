#!/usr/bin/env python3
"""Minimal raw Ollama wrapper for the Qwen ground-check skill."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def clean_response(text: str) -> str:
    value = text.strip()
    # Raw local models sometimes emit a complete hidden-reasoning block despite
    # instructions. Remove only a complete leading block; never guess where an
    # unterminated one should end.
    if value.startswith("<think>") and "</think>" in value:
        value = value.split("</think>", 1)[1].lstrip()
    if value.startswith("<analysis>") and "</analysis>" in value:
        value = value.split("</analysis>", 1)[1].lstrip()
    return value


def main() -> int:
    prompt = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else sys.stdin.read().strip()
    if not prompt:
        print("usage: qwen27_raw_chat.py '<prompt>'", file=sys.stderr)
        return 2

    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("QWEN27_MODEL", "qwen3-6-27b:latest")
    timeout = env_int("QWEN27_TIMEOUT", 180, 5, 3600)
    max_tokens = env_int("QWEN27_MAX_TOKENS", 48, 1, 4096)
    temperature = env_float("QWEN27_TEMP", 0.2, 0.0, 2.0)

    raw_prompt = (
        "<|im_start|>system\n"
        "Return only the concise final answer. Do not expose hidden reasoning or scratchpad.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"{prompt}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    payload = {
        "model": model,
        "prompt": raw_prompt,
        "raw": True,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }

    request = urllib.request.Request(
        f"{host}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[-2000:]
        print(f"Ollama HTTP {error.code}: {detail}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Ollama request failed: {error}", file=sys.stderr)
        return 1

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        print(f"Ollama returned invalid JSON: {body[-2000:]}", file=sys.stderr)
        return 1

    if result.get("error"):
        print(f"Ollama error: {result['error']}", file=sys.stderr)
        return 1

    output = clean_response(str(result.get("response", "")))
    if not output:
        print("Ollama returned an empty final response", file=sys.stderr)
        return 1
    if output.startswith("<think>") or output.startswith("<analysis>"):
        print("Ollama returned an unterminated reasoning block; refusing to treat it as a clean check", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
