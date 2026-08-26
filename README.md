# 🎭 PlayForge

> **A Playwright recorder that turns browser actions into reusable Page Object code.**

PlayForge records clicks, fills, selects, and reads from a browser session, then writes the result out as Python code you can keep using. It is meant for the boring part of browser automation: set up a page, click through the flow once, and get a generated page object you can reuse instead of hand-writing locators over and over.

The project is designed to run as a normal CLI after installation. Install it globally, point it at a URL, interact with the page, and let it capture the flow. When you quit, it writes the generated code to disk.

## ✨ Features

- **🎬 Browser Recording**: Capture real user actions from a live page, including clicks, fills, selects, and text reads.
- **🧩 Page Object Generation**: Turn recorded workflows into Python page objects with reusable methods.
- **🧹 Workflow Splitting**: Split one recording session into multiple generated methods when a flow gets too long.
- **🪵 Structured Logging**: Uses `structlog` for simple, consistent CLI and runtime logs.
- **⚡ CLI Ready**: Install it globally and run `playforge --help` or `playforge <url>`.

## 📥 Installation

```bash
pip install playforge
playwright install
```

Or, to install directly from source:

```bash
pip install .
playwright install
```

If you want to use it from a local checkout while developing, install it in editable mode:

```bash
pip install -e .
playwright install
```

You need `playwright install` so Playwright downloads an actual browser. Without that, the CLI can install fine but has nothing to launch.

## 🚀 Quick Start

```bash
playforge https://example.com
```

The recorder opens a browser window, waits for you to interact with the page, and collects actions until you quit. Use `split` in the terminal if you want to break the recording into another generated method.

### Help

```bash
playforge --help
```

### Output file

```bash
playforge https://example.com -o generated_page.py
```

### What gets recorded

PlayForge watches for:

- clicks on buttons, links, and other interactive elements
- fills on input fields and text areas
- select changes
- double-click reads on readable text elements

Each captured workflow becomes a method in the generated page object. Repeated actions are collapsed where possible so the output stays usable instead of turning into a wall of duplicate steps.

## 🐍 Requirements

- Python **3.10+**
- `playwright`
- `structlog`
- `ruff`

## 🤝 Contributing

Issues and pull requests are welcome. If you hit a weird recorder edge case, open an issue with the page flow and the generated output.

---
*Built for browser automation and code generation. MIT Licensed.*
