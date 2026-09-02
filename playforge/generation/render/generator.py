from __future__ import annotations

from pathlib import Path

from playforge.logger.logger import get_logger
from playforge.workflow.manager import WorkflowManager
from playforge.workflow.models import Action
from playforge.workflow.sanitizer import LocatorSanitizer


class CodeGenerator:
    """Render workflows into a generated Playwright page object."""

    # Priority of genuine DOM attributes used to build a stable locator.
    # ("id" is handled separately since it uses a CSS id-selector, not an
    # attribute-value selector.)
    ATTRIBUTE_PRIORITY = ("id", "test_id", "aria_label", "name", "placeholder")
    ATTRIBUTE_CSS_NAME = {
        "test_id": "data-testid",
        "aria_label": "aria-label",
        "name": "name",
        "placeholder": "placeholder",
    }

    def __init__(self, workflow_manager: WorkflowManager):
        self.workflow_manager = workflow_manager
        self.logger = get_logger(component="generator")

    @staticmethod
    def _identifying_attr(act: Action) -> tuple[str, str] | None:
        """Return the highest-priority genuine attribute present on ``act``.

        Falls back to ``None`` when none of the real DOM attributes were
        captured, so callers can fall back to text-based matching instead of
        mistaking display text for an attribute value.
        """
        for attr in CodeGenerator.ATTRIBUTE_PRIORITY:
            value = getattr(act, attr, "")
            if value:
                return attr, value
        return None

    @staticmethod
    def _locator_expr_for_action(act: Action) -> str:
        if act.class_name and act.type == "get":
            classes = "." + ".".join([c for c in act.class_name.split() if c])
            return f'page.locator("{classes}")'
        identifying = CodeGenerator._identifying_attr(act)
        if identifying:
            kind, value = identifying
            tag = act.tag_name or "*"
            if kind == "id":
                return f'page.locator("{tag}#{LocatorSanitizer.escape_selector_value(value)}")'
            css_attr = CodeGenerator.ATTRIBUTE_CSS_NAME[kind]
            safe_value = LocatorSanitizer.escape_attr_value(value)
            return f'page.locator(\'{tag}[{css_attr}="{safe_value}"]\')'
        if act.text:
            safe_text = LocatorSanitizer.normalize_text(act.text)
            return f"page.get_by_text({safe_text!r}, exact=True)"
        return f'page.locator("{act.tag_name}")'

    @staticmethod
    def _radio_group_locator_expr(act: Action) -> str:
        """Build a value-parameterized locator for radio/checkbox inputs.

        Radio buttons (and multi-value checkboxes) are commonly grouped by a
        shared ``name`` attribute, so ``input[name="..."]`` alone can resolve
        to several elements and trip Playwright's strict-mode check. Folding
        the option's ``value`` into the selector keeps it unique regardless
        of how many siblings share the same name.
        """
        tag = act.tag_name or "input"
        identifying = CodeGenerator._identifying_attr(act)
        if identifying:
            kind, attr_value = identifying
            if kind == "id":
                base = f"{tag}#{LocatorSanitizer.escape_selector_value(attr_value)}"
            else:
                css_attr = CodeGenerator.ATTRIBUTE_CSS_NAME[kind]
                safe_value = LocatorSanitizer.escape_attr_value(attr_value)
                base = f'{tag}[{css_attr}="{safe_value}"]'
        else:
            base = tag
        selector = base + '[value="{value}"]'
        return f"lambda value: page.locator(f'{selector}')"

    @staticmethod
    def _reserve_param_name(candidate: str, used_param_names: set[str]) -> str:
        if candidate in used_param_names:
            suffix = 2
            while f"{candidate}_{suffix}" in used_param_names:
                suffix += 1
            candidate = f"{candidate}_{suffix}"
        used_param_names.add(candidate)
        return candidate

    def generate(self, output_path: str, with_playback: bool = False) -> None:
        global_locators = {}
        functions_output = []
        workflow_main_calls = []
        workflows = self.workflow_manager.get_workflows()
        used_names: set[str] = set()

        for idx, workflow in enumerate(workflows):
            func_name = WorkflowManager.deduce_workflow_name(workflow.actions, idx + 1)
            method_steps = []
            param_list = []
            used_param_names: set[str] = set()
            recorded_values: dict[str, str] = {}

            for act_idx, act in enumerate(workflow.actions):
                is_lambda = False
                is_radio_group = act.type == "fill" and act.input_type in {
                    "radio",
                    "checkbox",
                }
                if act.is_lambda_role:
                    is_lambda = True
                    base_var_name = "ACTION_TYPE"
                    # normalize-space(.) is required because the real markup
                    # indents/wraps each <a> label across multiple lines, so
                    # its raw text() node never equals the trimmed item text.
                    loc_expr = "lambda item_text: page.locator(f\"//li[@role]/a[normalize-space(.)='{item_text}']\")"
                    param_name = "job_type"
                elif is_radio_group:
                    is_lambda = True
                    identifying = self._identifying_attr(act)
                    naming_source = identifying[1] if identifying else act.tag_name
                    base_var_name = LocatorSanitizer.sanitize_var_name(naming_source)
                    loc_expr = self._radio_group_locator_expr(act)
                    param_name = LocatorSanitizer.sanitize_param_name(naming_source)
                elif act.type == "get" and act.class_name:
                    base_var_name = LocatorSanitizer.sanitize_var_name(
                        f"{act.class_name}_{act.tag_name}"
                    )
                    loc_expr = self._locator_expr_for_action(act)
                    param_name = f"text_{act_idx}"
                elif identifying := self._identifying_attr(act):
                    _, attr_value = identifying
                    base_var_name = LocatorSanitizer.sanitize_var_name(attr_value)
                    loc_expr = self._locator_expr_for_action(act)
                    param_name = LocatorSanitizer.sanitize_param_name(attr_value)
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
                        candidate = self._reserve_param_name(param_name, used_param_names)
                        param_list.append(f"{candidate}: str")
                        recorded_values[candidate] = act.text or act.value or ""
                        method_steps.append(
                            f'self.{var_name}({candidate}).wait_for(state="visible", timeout=30000)'
                        )
                        method_steps.append(f"self.{var_name}({candidate}).click()")
                    else:
                        method_steps.append(f"self.{var_name}.click()")
                elif act.type in {"fill", "select"}:
                    candidate = self._reserve_param_name(param_name, used_param_names)
                    param_list.append(f"{candidate}: str")
                    recorded_values[candidate] = act.value or act.text or ""
                    if is_radio_group:
                        # Radio/checkbox inputs are not fillable; .check()
                        # is the correct Playwright action, and the locator
                        # itself is parameterized by value (see
                        # _radio_group_locator_expr), so no extra select-style
                        # dispatch is needed here.
                        method_steps.append(
                            f'self.{var_name}({candidate}).wait_for(state="visible", timeout=30000)'
                        )
                        method_steps.append(f"self.{var_name}({candidate}).check()")
                    elif act.type == "fill":
                        method_steps.append(
                            f'self.{var_name}.wait_for(state="visible", timeout=30000)'
                        )
                        method_steps.append(f"self.{var_name}.fill({candidate})")
                    else:
                        # Select options are matched by their HTML "value" attribute
                        # (act.value), never by visible label text: <select> textContent
                        # concatenates every option, so "label" would never match.
                        method_steps.append(
                            f"self.{var_name}.select_option(value={candidate})"
                        )
                        method_steps.append(
                            f'self.{var_name}.dispatch_event("change")'
                        )
                elif act.type == "get":
                    if act.class_name:
                        param_list.append("n: int")
                        method_steps.append(f"locator = self.{var_name}.nth(n)")
                        method_steps.append(
                            f'locator.wait_for(state="visible", timeout=30000)'
                        )
                        method_steps.append("return locator")
                    else:
                        method_steps.append(
                            f'self.{var_name}.wait_for(state="visible", timeout=30000)'
                        )
                        method_steps.append(f"return self.{var_name}")

            params_str = ", ".join(["self"] + param_list)
            func_def = [f"    def {func_name}({params_str}):"]
            for step in method_steps:
                func_def.append(f"        {step}")
            functions_output.append("\n".join(func_def))

            main_args = [
                repr(recorded_values[p_name])
                for p in param_list
                if (p_name := p.split(":")[0]) in recorded_values
            ]
            if main_args:
                workflow_main_calls.append(
                    f"        generated_page.{func_name}({', '.join(main_args)})"
                )
            else:
                workflow_main_calls.append(f"        generated_page.{func_name}()")

        code_lines = [
            "from playwright.sync_api import Page, sync_playwright",
            "",
            "",
            "class GeneratedPage:",
            "    def __init__(self, page: Page):",
            "        self.page = page",
        ]
        for var, expr in global_locators.items():
            code_lines.append(f"        self.{var} = {expr}")
        code_lines.append("")
        code_lines.extend(functions_output)

        if with_playback:
            code_lines.append("")
            code_lines.append("def main():")
            code_lines.append("    with sync_playwright() as playwright:")
            code_lines.append("        browser = playwright.chromium.launch(headless=False)")
            code_lines.append("        context = browser.new_context(ignore_https_errors=True)")
            code_lines.append("        page = context.new_page()")
            start_url = self.workflow_manager.get_start_url()
            if start_url:
                code_lines.append("        try:")
                code_lines.append(f"            page.goto({start_url!r}, wait_until='domcontentloaded')")
                code_lines.append("        except Exception:")
                code_lines.append("            pass")
            code_lines.append("        generated_page = GeneratedPage(page)")
            code_lines.extend(workflow_main_calls)
            code_lines.append("        context.close()")
            code_lines.append("        browser.close()")
            code_lines.append("")
            code_lines.append("if __name__ == \"__main__\":")
            code_lines.append("    main()")

        Path(output_path).write_text("\n".join(code_lines), encoding="utf-8")
        self.logger.info("generated_page_written", output_path=output_path)

