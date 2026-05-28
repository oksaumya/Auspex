"""Whitespace-tolerant code patching with bounded blast radius.

The reviewer LLM often returns ``original_code`` with slightly different
indentation than the source file. ``str.replace`` matches on the first
occurrence (which may be wrong) and silently fails when whitespace differs.
This helper does three passes, preferring the safest match each time:

1. **Exact** — ``original_code`` appears verbatim exactly once.
2. **Whitespace-normalized** — strip leading whitespace per line on both
   sides; require exactly one match; re-indent the proposed code to the
   level of the matched block.
3. **Fuzzy line-block** — slide a window of equal line count over the
   source and accept only if the best ``SequenceMatcher`` ratio is >=0.92
   and is unique within 0.05 of the runner-up.

Returns ``(patched_text, info)`` or ``(None, reason)``. Multiple matches
or no match aborts the patch with ``None``.
"""
import difflib
from typing import Optional, Tuple


_FUZZY_THRESHOLD = 0.92
_FUZZY_MARGIN = 0.05


def _dedent(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines())


def _leading_ws(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _reindent(snippet: str, indent: str) -> str:
    lines = snippet.splitlines()
    if not lines:
        return snippet
    out = [lines[0]]
    for line in lines[1:]:
        out.append((indent + line) if line.strip() else line)
    return "\n".join(out)


def apply_patch(
    source: str, original: str, proposed: str
) -> Tuple[Optional[str], str]:
    if not original.strip():
        return None, "empty original_code"

    # Pass 1: exact match
    count = source.count(original)
    if count == 1:
        return source.replace(original, proposed), "exact match"
    if count > 1:
        return None, f"original_code appears {count}x — ambiguous"

    # Pass 2: whitespace-normalized match on full lines
    src_lines = source.splitlines()
    orig_lines = original.splitlines()
    norm_orig = [l.strip() for l in orig_lines if l.strip()]
    if not norm_orig:
        return None, "original_code is whitespace-only"

    matches = []
    for i in range(len(src_lines) - len(orig_lines) + 1):
        window = src_lines[i : i + len(orig_lines)]
        norm_window = [l.strip() for l in window if l.strip()]
        if norm_window == norm_orig:
            matches.append(i)
    if len(matches) == 1:
        start = matches[0]
        indent = _leading_ws(src_lines[start])
        reindented = _reindent(proposed, indent)
        new_lines = src_lines[:start] + reindented.splitlines() + src_lines[start + len(orig_lines) :]
        return "\n".join(new_lines) + ("\n" if source.endswith("\n") else ""), (
            f"whitespace-normalized match at line {start + 1}"
        )
    if len(matches) > 1:
        return None, f"whitespace-normalized match is ambiguous ({len(matches)} candidates)"

    # Pass 3: fuzzy line-block via SequenceMatcher
    norm_orig_text = _dedent(original)
    best_ratio = 0.0
    runner_up = 0.0
    best_start = -1
    for i in range(len(src_lines) - len(orig_lines) + 1):
        window = "\n".join(l.strip() for l in src_lines[i : i + len(orig_lines)])
        ratio = difflib.SequenceMatcher(None, norm_orig_text, window).ratio()
        if ratio > best_ratio:
            runner_up = best_ratio
            best_ratio = ratio
            best_start = i
        elif ratio > runner_up:
            runner_up = ratio

    if best_ratio >= _FUZZY_THRESHOLD and (best_ratio - runner_up) >= _FUZZY_MARGIN:
        indent = _leading_ws(src_lines[best_start])
        reindented = _reindent(proposed, indent)
        new_lines = (
            src_lines[:best_start] + reindented.splitlines() + src_lines[best_start + len(orig_lines) :]
        )
        return "\n".join(new_lines) + ("\n" if source.endswith("\n") else ""), (
            f"fuzzy match at line {best_start + 1} (ratio={best_ratio:.2f})"
        )

    return None, f"no usable match (best fuzzy ratio={best_ratio:.2f})"
