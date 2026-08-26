from __future__ import annotations

import argparse

from playforge.logger.logger import configure_logging, get_logger
from playforge.workflow.manager import WorkflowManager
from playforge.generation.render.generator import CodeGenerator
from playforge.recording.capture.recorder import InteractiveRecorder


logger = get_logger(component="cli")


def main() -> None:
    """Run the PlayForge CLI."""
    configure_logging()
    parser = argparse.ArgumentParser(
        description="Interactive Playwright Page Object Recorder"
    )
    parser.add_argument("url", nargs="?", help="Target URL to record against")
    parser.add_argument(
        "-o", "--output", default="generated_page.py", help="Output python file path"
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode"
    )
    args = parser.parse_args()

    if not args.url:
        parser.print_help()
        return

    logger.info("cli_started", url=args.url, output=args.output, headless=args.headless)
    workflow_manager = WorkflowManager()
    recorder = InteractiveRecorder(args.url, workflow_manager, headless=args.headless)
    try:
        completed = recorder.run()
    except KeyboardInterrupt:
        logger.info("cli_interrupted")
        return
    if not completed:
        logger.info("cli_interrupted")
        return
    CodeGenerator(workflow_manager).generate(args.output)
    logger.info("cli_finished", output=args.output)
