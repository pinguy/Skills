#!/usr/bin/env python3
"""Run UCS against an optional OpenAI-compatible chat endpoint and durable board."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def model_client(base_url, model, api_key=None, timeout=60.0, max_tokens=1024):
    """Text-only client with explicit timeout; credentials stay out of prompts."""
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("model base URL must be HTTP(S), normally ending in /v1")
    if not model or timeout <= 0 or max_tokens < 1:
        raise ValueError("model, positive timeout and positive max_tokens are required")

    def call(prompt):
        body = json.dumps({
            "model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0,
        }).encode()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = "Bearer " + api_key
        request = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions", data=body, headers=headers,
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("model endpoint did not return text content")
        return content

    return call


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", required=True, help="SQLite path; parent must exist")
    parser.add_argument("--board", help="existing typed blackboard, created with blackboard.py init")
    parser.add_argument("--task")
    parser.add_argument("--context", help="trusted JSON task context, including optional rlvr verifiers")
    parser.add_argument("--skill", action="append", help="explicit skill selection; otherwise lexical routing")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL, including /v1")
    parser.add_argument("--model")
    parser.add_argument("--api-key-env", default="UCS_API_KEY")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--handover", action="store_true", help="read recent saved runs without model calls")
    args = parser.parse_args(argv)
    if not args.handover and not args.task:
        parser.error("--task is required unless --handover is used")
    if bool(args.base_url) != bool(args.model):
        parser.error("--base-url and --model must be supplied together")
    if args.handover and not Path(args.memory).is_file():
        parser.error("handover memory database does not exist")
    context = {}
    if args.context:
        context = json.loads(Path(args.context).read_text(encoding="utf-8"))
        if not isinstance(context, dict):
            parser.error("context must be a JSON object")

    callback = model_client(
        args.base_url, args.model, os.environ.get(args.api_key_env), args.timeout, args.max_tokens,
    ) if args.base_url and not args.handover else None
    # Keep stdout as one machine-readable JSON result, with diagnostics on stderr.
    with contextlib.redirect_stdout(sys.stderr):
        # Optional runtime libraries can print notices during import too.
        from UnifiedCognitionSystem import UnifiedCognitionSystem

        ucs = UnifiedCognitionSystem(
            memory_db_path=args.memory, blackboard_path=args.board, agent_callable=callback,
            writer_id=f"ucs/{args.model}" if args.model else "ucs/offline",
        )
        try:
            if args.handover:
                result = ucs.get_handover()
                status = 0
            else:
                report = ucs.solve_with_abm(args.task, context, return_report=True, skill_names=args.skill)
                result = report.as_dict()
                # A failed real-model connection must not look like a successful CLI run.
                status = 2 if any(c.generation_source == "fallback" for c in report.contributions) else 0
                if not report.hard_verifiers_passed:
                    status = 2
        finally:
            ucs.shutdown()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
