import pytest

from textab.compiler import parse_variables, compile_content, compile_note


# ── parse_variables ───────────────────────────────────────────────────────────

def test_no_block_returns_none():
    content = "Just a regular note without any AI Variables block."
    variables, body = parse_variables(content)
    assert variables is None
    assert body is None

def test_basic_block_parsed():
    content = """\
AI Variables
: - [x] {{ name }} = Alice
: - [ ] {{ age }}

Hello {{ name }}, you are {{ age }} years old."""
    variables, body = parse_variables(content)
    assert variables == {"name": "Alice", "age": None}
    assert "Hello {{ name }}" in body

def test_unchecked_variable_is_none():
    content = """\
AI Variables
: - [ ] {{ unset_var }}

Body text."""
    variables, body = parse_variables(content)
    assert variables["unset_var"] is None

def test_checked_variable_with_value():
    content = """\
AI Variables
: - [x] {{ city }} = Paris

Welcome to {{ city }}."""
    variables, body = parse_variables(content)
    assert variables["city"] == "Paris"

def test_body_excludes_block():
    content = """\
Preamble

AI Variables
: - [x] {{ x }} = 1

Footer"""
    variables, body = parse_variables(content)
    assert "AI Variables" not in body
    assert ": - [x]" not in body
    assert "Preamble" in body
    assert "Footer" in body

def test_empty_block_no_variables():
    content = """\
AI Variables

Some content."""
    variables, body = parse_variables(content)
    assert variables == {}
    assert "Some content." in body

def test_block_at_end_of_file():
    content = """\
AI Variables
: - [x] {{ key }} = value"""
    variables, body = parse_variables(content)
    assert variables == {"key": "value"}


# ── compile_content ───────────────────────────────────────────────────────────

def test_replaces_known_variable():
    variables = {"name": "Bob"}
    compiled, unresolved = compile_content(variables, "Hello {{ name }}!")
    assert compiled == "Hello Bob!"
    assert unresolved == []

def test_unresolved_variable_preserved():
    variables = {"name": None}
    compiled, unresolved = compile_content(variables, "Hello {{ name }}!")
    assert "{{ name }}" in compiled
    assert "name" in unresolved

def test_missing_variable_treated_as_unresolved():
    variables = {}
    compiled, unresolved = compile_content(variables, "{{ missing }}")
    assert "{{ missing }}" in compiled
    assert "missing" in unresolved

def test_multiple_placeholders():
    variables = {"a": "1", "b": "2"}
    compiled, unresolved = compile_content(variables, "{{ a }} and {{ b }}")
    assert compiled == "1 and 2"
    assert unresolved == []

def test_duplicate_unresolved_deduped():
    variables = {}
    compiled, unresolved = compile_content(variables, "{{ x }} {{ x }} {{ x }}")
    assert unresolved == ["x"]

def test_partial_substitution():
    variables = {"known": "yes", "unknown": None}
    compiled, unresolved = compile_content(variables, "{{ known }} {{ unknown }}")
    assert "yes" in compiled
    assert "{{ unknown }}" in compiled
    assert unresolved == ["unknown"]


# ── compile_note (high-level) ─────────────────────────────────────────────────

def test_compile_note_no_block():
    content = "Plain note, no block."
    compiled, unresolved, had_block = compile_note(content)
    assert compiled == content
    assert unresolved == []
    assert had_block is False

def test_compile_note_with_block():
    content = """\
AI Variables
: - [x] {{ greeting }} = Hi

{{ greeting }}, world!"""
    compiled, unresolved, had_block = compile_note(content)
    assert "Hi, world!" in compiled
    assert unresolved == []
    assert had_block is True

def test_compile_note_unresolved():
    content = """\
AI Variables
: - [ ] {{ missing }}

Hello {{ missing }}."""
    compiled, unresolved, had_block = compile_note(content)
    assert "missing" in unresolved
    assert had_block is True

def test_compile_note_empty_string():
    compiled, unresolved, had_block = compile_note("")
    assert compiled == ""
    assert had_block is False
