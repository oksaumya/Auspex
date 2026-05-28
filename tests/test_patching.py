"""Whitespace-tolerant patch application."""
from core.patching import apply_patch


def test_exact_match_replaces_inline():
    source = "x = 1\ny = 2\nz = 3\n"
    out, info = apply_patch(source, "y = 2", "y = 22")
    assert out == "x = 1\ny = 22\nz = 3\n"
    assert "exact" in info


def test_ambiguous_exact_match_aborts():
    source = "y = 2\nprint('hi')\ny = 2\n"
    out, info = apply_patch(source, "y = 2", "y = 99")
    assert out is None
    assert "ambiguous" in info


def test_whitespace_normalized_match_reindents():
    source = "def f():\n    if x:\n        do_thing()\n        more()\n"
    original = "if x:\n    do_thing()\n    more()"
    proposed = "if x:\n    new_thing()\n    more()"
    out, info = apply_patch(source, original, proposed)
    assert out is not None
    assert "    new_thing()" in out
    assert "whitespace-normalized" in info


def test_no_match_returns_none():
    source = "def f():\n    pass\n"
    out, info = apply_patch(source, "def nonexistent():\n    pass", "def x(): pass")
    assert out is None


def test_empty_original_aborts():
    out, info = apply_patch("x = 1\n", "", "y = 2")
    assert out is None
    assert "empty" in info
