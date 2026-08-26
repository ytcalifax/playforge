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
        return value.replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def quote_text_selector(value: str) -> str:
        return f"text='{LocatorSanitizer.escape_selector_value(value)}'"

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
