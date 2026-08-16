#!/usr/bin/env bash
set -euo pipefail

MAX_TOKENS="${QWEN27_MAX_TOKENS:-48}"
TEMP="${QWEN27_TEMP:-0.2}"
WRAPPER="${QWEN27_WRAPPER:-${HOME}/.openclaw/workspace/scripts/qwen27_raw_chat.sh}"

if [[ "$#" -gt 0 ]]; then
  ISSUE="$*"
else
  ISSUE="$(cat)"
fi

if [[ -z "${ISSUE//[[:space:]]/}" ]]; then
  echo "usage: qwen27_ground_check.sh '<claim or issue>'" >&2
  echo "   or: printf '%s\\n' '<claim or issue>' | qwen27_ground_check.sh" >&2
  exit 2
fi

PROMPT="You are being used as a slow local grounding check for another agent, not as a cheerleader. Be blunt and cautious.

Issue:
${ISSUE}

Task:
1. Identify overconfidence, missing caveats, unsupported absolutes, or factual risks.
2. Gate the wording as ALLOW, ESCALATE, or REFUSE.
3. Give safer wording if needed.
4. Name any failure modes in your own judgement.

Return final answer only, under 220 words, no thinking process."

QWEN27_MAX_TOKENS="$MAX_TOKENS" QWEN27_TEMP="$TEMP" "$WRAPPER" "$PROMPT"
