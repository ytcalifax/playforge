from __future__ import annotations

import json
import threading
from typing import Any

from playwright.sync_api import Error, Page, sync_playwright

from playforge.logger.logger import get_logger
from playforge.workflow.manager import WorkflowManager


class InteractiveRecorder:
    """Capture browser interactions and append them to workflows."""

    def __init__(
        self, url: str, workflow_manager: WorkflowManager, headless: bool = False
    ):
        self.url = url
        self.workflow_manager = workflow_manager
        self.headless = headless
        self.stop_recording = False
        self.logger = get_logger(component="recorder")

    def _on_console(self, msg: Any) -> None:
        if not msg.text.startswith("RECORD_ACTION:"):
            return
        try:
            action = json.loads(msg.text.split("RECORD_ACTION:", 1)[1])
            self.workflow_manager.add_action(action)
            self.logger.info(
                "recorded_action",
                action_type=action.get("type"),
                tag_name=action.get("tagName"),
                element_id=action.get("id"),
            )
        except (ValueError, TypeError, KeyError):
            self.logger.warning("record_action_parse_failed")

    def _attach_recorder(self, page: Page) -> None:
        page.on("console", self._on_console)
        page.add_init_script(r"""
            (() => {
                const sendAction = (data) => console.log("RECORD_ACTION:" + JSON.stringify(data));
                const getText = (el) => {
                    if (!el) return '';
                    return (el.textContent || '').replace(/\s+/g, ' ').trim();
                };
                const getElementId = (el) => {
                    if (!el) return '';
                    if (el.id) return el.id;
                    const labeledBy = el.getAttribute && el.getAttribute('aria-label');
                    if (labeledBy) return labeledBy.trim();
                    if ('name' in el && typeof el.name === 'string' && el.name.trim()) return el.name.trim();
                    if ('placeholder' in el && typeof el.placeholder === 'string' && el.placeholder.trim()) return el.placeholder.trim();
                    if (el.getAttribute) {
                        const testId = el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-qa');
                        if (testId) return testId.trim();
                    }
                    const text = getText(el);
                    if (text) return text;
                    return el.tagName ? el.tagName.toLowerCase() : '';
                };
                const isInteractive = (el) => {
                    if (!el || !el.tagName) return false;
                    const tag = el.tagName.toLowerCase();
                    return ['input', 'textarea', 'select', 'button', 'a'].includes(tag) || tag === 'label';
                };
                window.addEventListener('DOMContentLoaded', () => {
                    document.addEventListener('click', (e) => {
                        const el = e.target;
                        if (!el || !isInteractive(el)) return;
                        sendAction({
                            type: 'click',
                            tagName: el.tagName ? el.tagName.toLowerCase() : '',
                            id: getElementId(el),
                            className: typeof el.className === 'string' ? el.className.trim() : '',
                            text: getText(el),
                            isLambdaRole: Boolean(el.tagName && el.tagName.toLowerCase() === 'a' && el.parentElement && el.parentElement.getAttribute('role')),
                            value: el.value || ''
                        });
                    }, true);
                    document.addEventListener('dblclick', (e) => {
                        const el = e.target;
                        if (!el) return;
                        const tag = el.tagName ? el.tagName.toLowerCase() : '';
                        if (!['label', 'p', 'span', 'div', 'li', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'small'].includes(tag)) return;
                        const textVal = getText(el);
                        if (!textVal) return;
                        sendAction({ type: 'get', tagName: tag, id: getElementId(el), className: typeof el.className === 'string' ? el.className.trim() : '', text: textVal, isLambdaRole: false, value: '' });
                    }, true);
                    document.addEventListener('change', (e) => {
                        const el = e.target;
                        if (!el) return;
                        const isSelect = el.tagName && el.tagName.toLowerCase() === 'select';
                        sendAction({ type: isSelect ? 'select' : 'fill', tagName: el.tagName ? el.tagName.toLowerCase() : '', id: getElementId(el), className: typeof el.className === 'string' ? el.className.trim() : '', text: getText(el), isLambdaRole: false, value: el.value || '' });
                    }, true);
                });
            })();
        """)

    def run(self) -> bool:
        self.logger.info("recorder_started", url=self.url, headless=self.headless)
        interrupted = False
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(ignore_https_errors=True)
                context.on("page", self._attach_recorder)
                page = context.new_page()
                self._attach_recorder(page)
                try:
                    page.goto(self.url, wait_until="domcontentloaded")
                except Error:
                    self.logger.warning("initial_navigation_failed", url=self.url)

                self.logger.info(
                    "recorder_ready",
                    commands="split: new function block, clear: remove last action, quit: stop and generate",
                )

                def terminal_listener() -> None:
                    while not self.stop_recording:
                        try:
                            cmd = input().strip().lower()
                            if cmd in {"quit", ""}:
                                self.stop_recording = True
                                break
                            if cmd == "split":
                                self.workflow_manager.split_workflow()
                                self.logger.info("workflow_split")
                            elif cmd == "clear":
                                self.workflow_manager.clear_last_action()
                                self.logger.info("workflow_action_cleared")
                            else:
                                self.logger.warning("unknown_command", command=cmd)
                        except (KeyboardInterrupt, EOFError):
                            self.stop_recording = True
                            break

                threading.Thread(target=terminal_listener, daemon=True).start()
                while not self.stop_recording:
                    try:
                        page.wait_for_timeout(100)
                    except Error:
                        break
                try:
                    context.close()
                    browser.close()
                except Error:
                    self.logger.warning("browser_close_failed")
        except KeyboardInterrupt:
            interrupted = True
            self.stop_recording = True
            self.logger.info("recorder_interrupted", url=self.url)

        self.logger.info("recorder_stopped", url=self.url, interrupted=interrupted)
        return not interrupted
