"""
Markdown rendering and HTML sanitization for Distill.

Cards are authored in Markdown (with fenced code and tables), then converted to
HTML and sanitized against a strict allow-list of tags and attributes before
being embedded into Anki notes.
"""

import bleach
import markdown

# Whitelist of allowed HTML tags and attributes as per §6.3
ALLOWED_TAGS = [
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
    "img",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class"],
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "title"],
}


def normalize_tag(value: str) -> str:
    """Normalizes tag value by stripping all whitespace characters."""
    if not isinstance(value, str):
        return ""
    # Strip all whitespace characters to conform to Anki's space-separated tags format
    import re

    return re.sub(r"\s+", "", value)


def render_markdown(text: str, inline: bool = False) -> str:
    """
    Converts markdown text to HTML, then sanitizes it against the allowed whitelist.
    If inline is True, strips wrapping <p> tags from the output.
    """
    if not isinstance(text, str):
        return ""

    # Convert markdown to HTML using fenced_code and tables extensions
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])

    # Sanitize HTML using bleach
    sanitized = bleach.clean(
        html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True
    )

    if inline:
        # Strip wrapping <p> and </p> tags only if it is a single paragraph,
        # preventing slicing off outer tags from multi-paragraph structures.
        s = sanitized.strip()
        if s.startswith("<p>") and s.endswith("</p>") and s.count("<p>") == 1:
            s = s[3:-4].strip()
        return s

    return sanitized
