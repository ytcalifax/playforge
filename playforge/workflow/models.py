from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Action:
    """Normalized action captured from the browser."""

    type: str
    tag_name: str = ""
    id: str = ""
    class_name: str = ""
    text: str = ""
    is_lambda_role: bool = False
    value: str = ""
    position: int = 0
    test_id: str = ""
    aria_label: str = ""
    name: str = ""
    placeholder: str = ""
    input_type: str = ""

    @classmethod
    def from_mapping(cls, action: dict[str, Any]) -> "Action":
        """Build an action from raw recorder payload data.

        ``id`` holds only a genuine DOM ``id`` attribute. Other identifying
        attributes (``data-testid``/``data-test``/``data-qa``, ``aria-label``,
        ``name``, ``placeholder``) are kept in their own fields so the
        generator never mistakes one attribute (or fallback display text)
        for another when building selectors. ``input_type`` holds the raw
        HTML ``<input type="...">`` value (e.g. "radio"/"checkbox") so the
        generator can pick ``.check()`` over ``.fill()`` and disambiguate
        same-``name`` radio groups by their ``value``.
        """

        return cls(
            type=str(action.get("type", "")).strip().lower(),
            tag_name=str(action.get("tagName", "") or "").strip().lower(),
            id=str(action.get("id", "") or "").strip(),
            class_name=str(action.get("className", "") or "").strip(),
            text=str(action.get("text", "") or "").replace("\xa0", " ").strip(),
            is_lambda_role=bool(action.get("isLambdaRole", False)),
            value=str(action.get("value", "") or ""),
            position=int(action.get("position", 0) or 0),
            test_id=str(action.get("testId", "") or "").strip(),
            aria_label=str(action.get("ariaLabel", "") or "").strip(),
            name=str(action.get("name", "") or "").strip(),
            placeholder=str(action.get("placeholder", "") or "").strip(),
            input_type=str(action.get("inputType", "") or "").strip().lower(),
        )


@dataclass(slots=True)
class Workflow:
    """Ordered actions that belong to one generated workflow."""

    actions: list[Action] = field(default_factory=list)
