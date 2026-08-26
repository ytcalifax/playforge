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

    @classmethod
    def from_mapping(cls, action: dict[str, Any]) -> "Action":
        """Build an action from raw recorder payload data."""

        return cls(
            type=str(action.get("type", "")).strip().lower(),
            tag_name=str(action.get("tagName", "") or "").strip().lower(),
            id=str(action.get("id", "") or "").strip(),
            class_name=str(action.get("className", "") or "").strip(),
            text=str(action.get("text", "") or "").replace("\xa0", " ").strip(),
            is_lambda_role=bool(action.get("isLambdaRole", False)),
            value=str(action.get("value", "") or ""),
        )


@dataclass(slots=True)
class Workflow:
    """Ordered actions that belong to one generated workflow."""

    actions: list[Action] = field(default_factory=list)
