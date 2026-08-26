from __future__ import annotations

from .models import Action, Workflow


class WorkflowManager:
    """Collect and shape recorded actions into workflows."""

    def __init__(self) -> None:
        self._workflows: list[Workflow] = [Workflow()]

    def add_action(self, action: dict) -> None:
        normalized = Action.from_mapping(action)
        if not normalized.type:
            return
        if normalized.type not in {"click", "fill", "select", "get"}:
            return
        if (
            normalized.type == "click"
            and not normalized.id
            and not normalized.text
            and not normalized.class_name
            and normalized.tag_name in {"span", "div", "i", "b", "p"}
        ):
            return

        current = self._workflows[-1].actions
        if current:
            last = current[-1]
            if (
                last.type == normalized.type
                and last.id == normalized.id
                and last.tag_name == normalized.tag_name
                and last.text == normalized.text
            ):
                return
            if normalized.type in {"fill", "select"} and last.type == "click":
                if (
                    last.id == normalized.id and last.tag_name == normalized.tag_name
                ) or (not normalized.id and last.tag_name == normalized.tag_name):
                    current.pop()

        current.append(normalized)

    def split_workflow(self) -> None:
        self._workflows.append(Workflow())

    def clear_last_action(self) -> None:
        current = self._workflows[-1].actions
        if current:
            current.pop()

    def get_workflows(self) -> list[Workflow]:
        return [workflow for workflow in self._workflows if workflow.actions]

    @staticmethod
    def deduce_workflow_name(actions: list[Action], index: int) -> str:
        if not actions:
            return f"sequence_{index}"
        block_text = " ".join(f"{act.text} {act.id}" for act in actions).lower()
        if "log" in block_text or "signin" in block_text:
            return "log_in"
        if "add" in block_text or "create" in block_text:
            if (
                "job" in block_text
                or "backup" in block_text
                or "retention" in block_text
            ):
                return "create_backup_job"
            return "create_item"
        for act in reversed(actions):
            if act.type == "click":
                raw_name = act.text.strip() or act.id.strip()
                if raw_name:
                    cleaned = "".join(
                        c if c.isalnum() else "_" for c in raw_name
                    ).lower()
                    return "_".join(filter(None, cleaned.split("_")))[:30]
        return f"sequence_{index}"
