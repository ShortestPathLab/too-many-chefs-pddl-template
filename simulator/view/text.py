from __future__ import annotations


def sentence_case(text: str) -> str:
    """Uppercase the first character without changing the rest.

    ``str.capitalize`` lowercases the rest of the string.
    """
    return text[:1].upper() + text[1:]


def and_list(words: list[str]) -> str:
    """Format a list as ``A``, ``A & B``, or ``A, B & C``."""
    if len(words) < 2:
        return "".join(words)
    return f"{', '.join(words[:-1])} & {words[-1]}"
