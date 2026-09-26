""" Discord payload validator

adapted from https://discord-webhook.com/en/blog/discord-webhook-embed-limits/
"""

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


class EmbedLimitError(ValueError):
    """ validation error """


# Per-field limits, in chars
LIMITS = {
    "title": 256,
    "description": 4096,
    "field.name": 256,
    "field.value": 1024,
    "footer.text": 2048,
    "author.name": 256,
    "username": 80,
    "content": 2000,
}

TOTAL_EMBED_CHARS = 6000
MAX_FIELDS = 25
MAX_EMBEDS = 10


def _len(s: Any) -> int:
    return len(s) if isinstance(s, str) else 0


def validate_embed(e: dict, idx: int = 0) -> int:
    """Validate one embed; return its char total."""
    total = 0

    if _len(e.get("title")) > LIMITS["title"]:
        raise EmbedLimitError(f"embeds[{idx}].title > {LIMITS['title']}")
    total += _len(e.get("title"))

    if _len(e.get("description")) > LIMITS["description"]:
        raise EmbedLimitError(
            f"embeds[{idx}].description > {LIMITS['description']}")
    total += _len(e.get("description"))

    fields = e.get("fields", [])
    if len(fields) > MAX_FIELDS:
        raise EmbedLimitError(f"embeds[{idx}].fields > {MAX_FIELDS} entries")
    for fi, f in enumerate(fields):
        if _len(f.get("name")) > LIMITS["field.name"]:
            raise EmbedLimitError(
                f"embeds[{idx}].fields[{fi}].name > {LIMITS['field.name']}")
        if _len(f.get("value")) > LIMITS["field.value"]:
            raise EmbedLimitError(
                f"embeds[{idx}].fields[{fi}].value > {LIMITS['field.value']}")
        total += _len(f.get("name")) + _len(f.get("value"))

    footer = e.get("footer", {})
    if _len(footer.get("text")) > LIMITS["footer.text"]:
        raise EmbedLimitError(
            f"embeds[{idx}].footer.text > {LIMITS['footer.text']}")
    total += _len(footer.get("text"))

    author = e.get("author", {})
    if _len(author.get("name")) > LIMITS["author.name"]:
        raise EmbedLimitError(
            f"embeds[{idx}].author.name > {LIMITS['author.name']}")
    total += _len(author.get("name"))

    return total


def validate_payload(payload: dict) -> None:
    """Raise EmbedLimitError if any limit is broken."""
    if _len(payload.get("content")) > LIMITS["content"]:
        raise EmbedLimitError(f"content > {LIMITS['content']}")
    if _len(payload.get("username")) > LIMITS["username"]:
        raise EmbedLimitError(f"username > {LIMITS['username']}")

    embeds = payload.get("embeds", [])
    if len(embeds) > MAX_EMBEDS:
        raise EmbedLimitError(f"embeds > {MAX_EMBEDS}")

    grand_total = sum(validate_embed(e, i) for i, e in enumerate(embeds))
    if grand_total > TOTAL_EMBED_CHARS:
        raise EmbedLimitError(
            f"total embed chars {grand_total} > {TOTAL_EMBED_CHARS}")
