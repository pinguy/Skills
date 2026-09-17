"""Bounded skill context and durable run receipts for Unified Cognition.

This module has no ML dependencies. It does not execute skill scripts or grant
tool permissions. The host owns model clients, tools and authenticated decisions.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import uuid
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent


def stamp():
    return datetime.now(timezone.utc).isoformat()


def words(text):
    stop = {"the", "and", "for", "with", "this", "that", "from", "into",
            "what", "how", "can", "you", "our", "are", "was", "use", "when"}
    return set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.lower())) - stop


class SkillRegistry:
    """Index frontmatter, then load whole selected entrypoints within a budget."""

    def __init__(self, root=None):
        self.root = Path(root or ROOT / "skills").resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"skill directory does not exist: {self.root}")
        self.entries = {}
        for path in sorted(self.root.glob("*/SKILL.md")):
            self._contained(path)
            lines = []
            with path.open(encoding="utf-8") as handle:
                if handle.readline().strip() != "---":
                    raise ValueError(f"missing skill frontmatter: {path}")
                for line in handle:
                    if line.strip() == "---":
                        break
                    lines.append(line)
                    if len(lines) > 100:
                        raise ValueError(f"oversized skill frontmatter: {path}")
                else:
                    raise ValueError(f"unterminated skill frontmatter: {path}")
            # Matches the repository checker: name/description are single-line scalars.
            fields = {}
            for key in ("name", "description"):
                match = re.search(rf"^{key}:\s*(.+)$", "".join(lines), re.M)
                if not match:
                    raise ValueError(f"missing {key}: {path}")
                value = match.group(1).strip()
                if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
                    value = value[1:-1]
                if not value or value in {"|", ">"}:
                    raise ValueError(f"{key} must be a non-empty single-line scalar: {path}")
                fields[key] = value
            if fields["name"] != path.parent.name:
                raise ValueError(f"skill name does not match directory: {path}")
            self.entries[fields["name"]] = {**fields, "path": str(path)}

    def _contained(self, path):
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("skill path escapes the configured registry")

    def select(self, task, names=None, limit=2, max_chars=24000):
        if names is not None:
            if isinstance(names, str):
                raise TypeError("skill_names must be a sequence of names, not a string")
            selected = list(dict.fromkeys(names))
            unknown = set(selected) - self.entries.keys()
            if unknown:
                raise ValueError(f"unknown skills: {', '.join(sorted(unknown))}")
        else:
            query = words(task)
            scores = []
            for name, entry in self.entries.items():
                terms = words(name.replace("-", " ") + " " + entry["description"])
                score = len(query & terms)
                if name in task.lower():
                    score += 10
                if score >= 2:
                    scores.append((-score, name))
            selected = [name for _, name in sorted(scores)[:limit]]
        loaded, omitted, remaining = [], [], max_chars
        for name in selected:
            path = Path(self.entries[name]["path"])
            self._contained(path)
            with path.open(encoding="utf-8") as handle:
                content = handle.read(remaining + 1)
            if len(content) > remaining:
                if names is not None:
                    raise ValueError(f"selected skill exceeds context budget: {name}")
                omitted.append(name)
                continue
            loaded.append({
                **self.entries[name], "instructions": content,
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
            })
            remaining -= len(content)
        return loaded, omitted


class RunJournal:
    """Append a run before invoking a model; preserve reports across restarts."""

    def __init__(self, memory):
        self.memory = memory
        with memory.lock, memory.conn:
            memory.conn.execute("""CREATE TABLE IF NOT EXISTS ucs_runs (
                run_id TEXT PRIMARY KEY, problem TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL,
                finished_at TEXT, context_sources TEXT NOT NULL,
                report TEXT, error TEXT
            )""")

    def begin(self, problem, sources):
        run_id = str(uuid.uuid4())
        with self.memory.lock, self.memory.conn:
            self.memory.conn.execute(
                "INSERT INTO ucs_runs VALUES (?, ?, 'running', ?, NULL, ?, NULL, NULL)",
                (run_id, problem, stamp(), json.dumps(sources)),
            )
        return run_id

    def finish(self, run_id, report=None, error=None):
        status = "failed" if error is not None else "finished"
        with self.memory.lock, self.memory.conn:
            cursor = self.memory.conn.execute(
                "UPDATE ucs_runs SET status=?, finished_at=?, report=?, error=? "
                "WHERE run_id=? AND status='running'",
                (status, stamp(), json.dumps(report) if report is not None else None,
                 error, run_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("run is missing or already finalised")

    def get(self, run_id):
        with self.memory.lock:
            row = self.memory.conn.execute(
                "SELECT * FROM ucs_runs WHERE run_id=?", (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        keys = ("run_id", "problem", "status", "started_at", "finished_at",
                "context_sources", "report", "error")
        result = dict(zip(keys, row))
        result["context_sources"] = json.loads(result["context_sources"])
        result["report"] = json.loads(result["report"]) if result["report"] else None
        return result

    def recent(self, limit=5):
        if not 1 <= limit <= 100:
            raise ValueError("run limit must be between 1 and 100")
        with self.memory.lock:
            rows = self.memory.conn.execute(
                "SELECT run_id FROM ucs_runs ORDER BY started_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [self.get(row[0]) for row in rows]


class DurableBlackboard:
    """Use the existing locked blackboard helper, including its schema checks."""

    def __init__(self, path, model="ucs/runtime"):
        self.path = Path(path).expanduser().resolve()
        self.model = model
        if not model.strip() or model.startswith("user/"):
            raise ValueError("UCS needs a non-user writer identity")
        source = ROOT / "skills/blackboard/scripts/blackboard.py"
        spec = importlib.util.spec_from_file_location("ucs_typed_blackboard", source)
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)

    def snapshot(self, max_chars=16000, for_work=True):
        with self.helper.board_lock(self.path, False):
            board = self.helper.load(self.path)
            errors = self.helper.validate(board)
            if errors:
                raise ValueError("invalid blackboard: " + "; ".join(errors))
        if for_work and board["status"] not in {"active", "needs_verification"}:
            raise ValueError(f"board does not allow UCS work: {board['status']}")
        if for_work and self.helper.target_blocked(board, str(self.path)):
            raise ValueError("DO_NOT_TOUCH blocks this blackboard target")
        result = {key: board[key] for key in (
            "task_id", "goal", "revision", "status", "policy", "hop_count", "next",
            "user_decisions",
        )}
        result["active_route"] = self.helper.active_route(board)
        # Never silently truncate authenticated constraints or current ownership.
        if len(json.dumps(result)) > max_chars:
            raise ValueError("blackboard constraints exceed context budget")
        for collection in ("facts", "test_results", "failed_attempts", "open_questions", "actions", "inferences", "evidence"):
            result[collection] = []
            for entry in reversed(board[collection][-3:]):
                result[collection].insert(0, entry)
                if len(json.dumps(result)) > max_chars:
                    result[collection].pop(0)
        return result

    def publish(self, report, expected_revision):
        return self.helper.record_ucs_report(
            self.path, report, self.model, expected_revision=expected_revision,
        )
