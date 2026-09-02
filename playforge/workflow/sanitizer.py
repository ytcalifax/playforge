from __future__ import annotations

from typing import Any
import re


class LocatorSanitizer:
    """Normalize text and build safe Python identifiers."""

    READABLE_TAGS = {
        "label",
        "p",
        "span",
        "div",
        "li",
        "td",
        "th",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "small",
    }

    @staticmethod
    def normalize_text(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).replace("\xa0", " ").strip()
        return " ".join(text.split())

    @staticmethod
    def escape_selector_value(value: str) -> str:
        text = str(value)
        if not text:
            return ""
        escaped = []
        for char in text:
            if char.isalnum() or char in {"-", "_"}:
                escaped.append(char)
            else:
                escaped.append(f"\\{char}")
        return "".join(escaped)

    @staticmethod
    def escape_attr_value(value: str) -> str:
        """Escape a value for embedding in a quoted CSS attribute selector.

        Unlike an identifier (``#id``), an attribute value sits inside a CSS
        string literal, so only backslashes and the quote character itself
        need escaping (no need to backslash-escape every space or symbol).
        """
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def sanitize_var_name(text: str) -> str:
        cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", str(text).strip())
        cleaned = "_".join(filter(None, cleaned.split("_"))).upper()
        if not cleaned:
            cleaned = "ELEMENT"
        if cleaned[0].isdigit():
            cleaned = f"EL_{cleaned}"
        return cleaned

    @staticmethod
    def sanitize_param_name(id_str: str) -> str:
        if "." in id_str:
            id_str = id_str.split(".")[-1]
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", id_str)
        cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        cleaned = "".join([c if c.isalnum() else "_" for c in cleaned])
        return "_".join(filter(None, cleaned.split("_"))) or "val"

    @staticmethod
    def unique_name(base_name: str, used_names: set[str]) -> str:
        candidate = base_name
        suffix = 2
        while candidate in used_names:
            candidate = f"{base_name}_{suffix}"
            suffix += 1
        used_names.add(candidate)
        return candidate
