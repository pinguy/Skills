#!/usr/bin/env python3
"""Lightweight repository checks for the public Skills collection."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
README = ROOT / "README.md"
LICENSE = ROOT / "LICENSE"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def frontmatter(text: str, path: Path) -> str:
    if not text.startswith("---\n"):
        fail(f"{path} does not start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        fail(f"{path} has unterminated YAML frontmatter")
    return text[4:end]


def field(block: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:\s*(.+?)\s*$", block, flags=re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'\"', "'"}:
        value = value[1:-1]
    return value.strip()


def readme_skill_names(text: str) -> set[str]:
    match = re.search(r"^## Included skills\s*$([\s\S]*?)(?=^## |\Z)", text, flags=re.MULTILINE)
    if not match:
        fail("README.md has no 'Included skills' section")
    return set(re.findall(r"^\|\s*`([^`]+)`\s*\|", match.group(1), flags=re.MULTILINE))


def main() -> None:
    if not SKILLS.is_dir():
        fail("skills/ directory is missing")
    if not README.is_file():
        fail("README.md is missing")
    if not LICENSE.is_file():
        fail("LICENSE is missing")

    license_text = LICENSE.read_text(encoding="utf-8")
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        fail("LICENSE does not look like Apache-2.0")

    skill_dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not skill_dirs:
        fail("no skill directories found")

    names: set[str] = set()
    for directory in skill_dirs:
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            fail(f"{directory.relative_to(ROOT)} has no SKILL.md")

        text = skill_file.read_text(encoding="utf-8")
        fm = frontmatter(text, skill_file.relative_to(ROOT))
        name = field(fm, "name")
        description = field(fm, "description")

        if not name:
            fail(f"{skill_file.relative_to(ROOT)} has no frontmatter name")
        if name != directory.name:
            fail(
                f"{skill_file.relative_to(ROOT)} name '{name}' does not match directory '{directory.name}'"
            )
        if not description:
            fail(f"{skill_file.relative_to(ROOT)} has no frontmatter description")
        if name in names:
            fail(f"duplicate skill name: {name}")
        names.add(name)

    indexed = readme_skill_names(README.read_text(encoding="utf-8"))
    missing = sorted(names - indexed)
    stale = sorted(indexed - names)
    if missing:
        fail("README is missing skill(s): " + ", ".join(missing))
    if stale:
        fail("README lists nonexistent skill(s): " + ", ".join(stale))

    forbidden_runtime_names = {".env", "sessions.json", "BOARD.json"}
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.name in forbidden_runtime_names:
            fail(f"runtime/private file should not be tracked: {path.relative_to(ROOT)}")

    print(f"PASS: {len(names)} skills indexed, frontmatter valid, Apache-2.0 present")


if __name__ == "__main__":
    main()
