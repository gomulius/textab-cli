"""
Client-side port of the AI Variables compilation pipeline.

Faithfully mirrors the _parse() and _compile() functions in:
  plugins/user_plugins/ai_variables/backend.py

Used as a fallback when:
  - The server compile endpoint returns NO_VARIABLES_BLOCK (422)
  - The user passes --no-compile to textab sync
"""

from __future__ import annotations

import re
from typing import Optional

_BLOCK_HEADER = "AI Variables"
_VAR_LINE = re.compile(
    r"^: - \[([ x])\] \{\{ ([a-zA-Z_][a-zA-Z0-9_]*) \}\}(?: = (.+))?$"
)
_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def parse_variables(
    content: str,
) -> tuple[Optional[dict[str, Optional[str]]], Optional[str]]:
    """
    Locate the AI Variables block, extract variable values, and return
    (variables_dict, body_without_block).

    Returns (None, None) if no AI Variables block is found.
    variables_dict maps name -> value (str) or None (not yet filled).
    """
    lines = content.splitlines()
    block_start = None

    for i, line in enumerate(lines):
        if line.strip() == _BLOCK_HEADER:
            block_start = i
            break

    if block_start is None:
        return None, None

    variables: dict[str, Optional[str]] = {}
    block_end = block_start

    for i in range(block_start + 1, len(lines)):
        m = _VAR_LINE.match(lines[i])
        if not m:
            break
        checked, name, raw_value = m.groups()
        variables[name] = raw_value.strip() if (checked == "x" and raw_value) else None
        block_end = i

    pre_body = "\n".join(lines[:block_start]).strip()
    body = "\n".join(lines[block_end + 1:]).strip()
    full_body = "\n\n".join(part for part in [pre_body, body] if part)

    return variables, full_body


def compile_content(
    variables: dict[str, Optional[str]], body: str
) -> tuple[str, list[str]]:
    """
    Replace {{ name }} placeholders in body using variables dict.

    Returns (compiled_str, unresolved_list).
    Placeholders with no value are left as-is and listed in unresolved.
    """
    unresolved: list[str] = []

    def _replace(m: re.Match) -> str:
        name = m.group(1)
        val = variables.get(name)
        if val:
            return val
        unresolved.append(name)
        return m.group(0)

    compiled = _PLACEHOLDER.sub(_replace, body)
    # Deduplicate while preserving first-occurrence order
    seen: set[str] = set()
    unique_unresolved = [x for x in unresolved if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]
    return compiled, unique_unresolved


def compile_note(content: str) -> tuple[str, list[str], bool]:
    """
    High-level helper: parse + compile in one call.

    Returns (compiled_content, unresolved_vars, had_variables_block).
    If no block found, returns (original_content, [], False).
    """
    variables, body = parse_variables(content)
    if variables is None:
        return content, [], False
    compiled, unresolved = compile_content(variables, body or "")
    return compiled, unresolved, True
