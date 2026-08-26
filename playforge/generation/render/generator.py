from __future__ import annotations

from pathlib import Path

from playforge.logger.logger import get_logger
from playforge.workflow.manager import WorkflowManager
from playforge.workflow.models import Action
from playforge.workflow.sanitizer import LocatorSanitizer


class CodeGenerator:
    """Render workflows into a generated Playwright page object."""

    def __init__(self, workflow_manager: WorkflowManager):
        self.workflow_manager = workflow_manager
        self.logger = get_logger(component="generator")

    @staticmethod
    def _locator_expr_for_action(act: Action) -> str:
        if act.class_name and act.type == "get":
            classes = "." + ".".join([c for c in act.class_name.split() if c])
            return f'page.locator("{classes}").nth({getattr(act, "position", 0)})'
        if act.id:
            if act.class_name:
                classes = "." + ".".join([c for c in act.class_name.split() if c])
                return f"page.locator(\"{classes} [id='{LocatorSanitizer.escape_selector_value(act.id)}']\")"
            return f"page.locator(\"[id='{LocatorSanitizer.escape_selector_value(act.id)}']\")"
        if act.text:
            safe_text = LocatorSanitizer.escape_selector_value(
                LocatorSanitizer.normalize_text(act.text)
            )
            return f'page.locator("{LocatorSanitizer.quote_text_selector(safe_text)}")'
        return f'page.locator("{act.tag_name}")'

    def generate(self, output_path: str) -> None:
        global_locators = {}
        functions_output = []
        workflows = self.workflow_manager.get_workflows()
        used_names: set[str] = set()

        for idx, workflow in enumerate(workflows):
            func_name = WorkflowManager.deduce_workflow_name(workflow.actions, idx + 1)
            method_steps = []
            param_list = []
            param_counts = {}

            for act_idx, act in enumerate(workflow.actions):
                is_lambda = False
                if act.is_lambda_role:
                    is_lambda = True
                    base_var_name = "ACTION_TYPE"
                    loc_expr = "lambda item_text: page.locator(f\"//li[@role]/a[text()='{item_text}']\")"
                    param_name = "job_type"
                elif act.type == "get" and act.class_name:
                    base_var_name = LocatorSanitizer.sanitize_var_name(
                        f"{act.class_name}_{act.tag_name}_{getattr(act, 'position', 0) + 1}"
                    )
                    loc_expr = self._locator_expr_for_action(act)
                    param_name = f"text_{act_idx}"
                elif act.id:
                    base_var_name = LocatorSanitizer.sanitize_var_name(act.id)
                    loc_expr = self._locator_expr_for_action(act)
                    param_name = LocatorSanitizer.sanitize_param_name(act.id)
                elif act.text:
                    base_var_name = LocatorSanitizer.sanitize_var_name(
                        f"{act.tag_name}_{act.text[:25]}"
                    )
                    loc_expr = self._locator_expr_for_action(act)
                    param_name = f"text_{act_idx}"
                else:
                    base_var_name = f"ELEMENT_{act_idx}"
                    loc_expr = self._locator_expr_for_action(act)
                    param_name = f"val_{act_idx}"

                var_name = LocatorSanitizer.unique_name(base_var_name, used_names)
                global_locators[var_name] = loc_expr

                if act.type == "click":
                    if is_lambda:
                        if param_name not in [p.split(":")[0] for p in param_list]:
                            param_list.append(f"{param_name}: str")
                        method_steps.append(
                            f'self.{var_name}({param_name}).wait_for(state="visible", timeout=30000)'
                        )
                        method_steps.append(f"self.{var_name}({param_name}).click()")
                    else:
                        method_steps.append(f"self.{var_name}.click()")
                elif act.type in {"fill", "select"}:
                    if param_name not in [p.split(":")[0] for p in param_list]:
                        param_counts[param_name] = 1
                        curr_param = param_name
                    else:
                        param_counts[param_name] = param_counts.get(param_name, 1) + 1
                        curr_param = f"{param_name}_{param_counts[param_name]}"
                    param_list.append(f"{curr_param}: str")
                    if act.type == "fill":
                        method_steps.append(
                            f'self.{var_name}.wait_for(state="visible", timeout=30000)'
                        )
                        method_steps.append(f"self.{var_name}.fill({curr_param})")
                    else:
                        method_steps.append(
                            f"self.{var_name}.select_option({curr_param})"
                        )
                elif act.type == "get":
                    method_steps.append(
                        f'self.{var_name}.wait_for(state="visible", timeout=30000)'
                    )
                    method_steps.append(
                        f"return self.{var_name}.inner_text().strip() or self.{var_name}.text_content() or ''"
                    )

            unique_params = []
            seen = set()
            for p in param_list:
                p_name = p.split(":")[0]
                if p_name not in seen:
                    seen.add(p_name)
                    unique_params.append(p)

            params_str = ", ".join(["self"] + unique_params)
            func_def = [f"    def {func_name}({params_str}):"]
            for step in method_steps:
                func_def.append(f"        {step}")
            functions_output.append("\n".join(func_def))

        code_lines = [
            "from playwright.sync_api import Page",
            "",
            "class GeneratedPage:",
            "    def __init__(self, page: Page):",
            "        self.page = page",
        ]
        for var, expr in global_locators.items():
            code_lines.append(f"        self.{var} = {expr}")
        code_lines.append("")
        code_lines.extend(functions_output)
        Path(output_path).write_text("\n".join(code_lines), encoding="utf-8")
        self.logger.info("generated_page_written", output_path=output_path)
