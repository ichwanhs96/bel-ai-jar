<p align="center">
  <img src="logo.webp" alt="bel-ai-jar logo" width="160" />
</p>

<h1 align="center">bel-ai-jar</h1>

<p align="center">
  Git hooks for understanding AI-generated code changes.
</p>

<p align="center">
  <a href="https://pypi.org/project/bel-ai-jar/"><img src="https://img.shields.io/pypi/v/bel-ai-jar?label=PyPI&color=blue" alt="PyPI version"></a>
  <a href="https://www.npmjs.com/package/bel-ai-jar"><img src="https://img.shields.io/npm/v/bel-ai-jar?label=npm&color=red" alt="npm version"></a>
  <a href="https://pypi.org/project/bel-ai-jar/"><img src="https://img.shields.io/pypi/pyversions/bel-ai-jar" alt="Python versions"></a>
  <img src="https://img.shields.io/node/v/bel-ai-jar?label=Node.js" alt="Node.js version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/ichwanhs96/bel-ai-jar/issues"><img src="https://img.shields.io/badge/contributions-welcome-brightgreen.svg" alt="Contributions welcome"></a>
</p>

---

## Problem

When working with AI-generated code, developers often face the challenge of understanding the changes made by AI agents. This can lead to a lack of cognitive understanding and ownership of the code, making it difficult to maintain and debug in the future.

## Solution

Bel-ai-jar is an open-source library that helps developers understand AI-generated code changes by asking questions before committing the code. This ensures that developers truly understand what has been implemented by the AI agent, maintaining cognitive ability and ownership of the code.

## User Flow

### Installation and Configuration Flow

```mermaid
flowchart TD
    A1[Install bel-ai-jar library] --> A2[Configure bel-ai-jar using terminal]
    A2 --> A3[Configure total number of question]
    A3 --> A4[Configure number of answer options on each question]
    A4 --> A5[Configure passing grade]
    A5 --> A6[Configure additional prompt to enhance question generation]
```

### Evaluation and Git Hooks Flow

```mermaid
flowchart TD
    A1[User made code changes] --> A2[User runs git commit]
    A2 --> A3[bel-ai-jar pre-commit hook triggers]
    A3 --> A4{ai_coauthored_only enabled?}
    A4 --> |No - default| A5[bel-ai-jar analyzes staged changes and generates questions]
    A4 --> |Yes| A4b{AI co-author detected?}
    A4b --> |No| A9[Commit proceeds immediately]
    A4b --> |Yes| A5
    A5 --> A6[User answers each question]
    A6 --> |pass| A7[Code successfully committed]
    A6 --> |fail| A8[Commit rejected — user must review the changes]
    A8 --> A2
```

## Architecture Flow

1. When you run `git commit`, the pre-commit hook triggers.
2. By default, bel-ai-jar evaluates **every commit** regardless of who wrote the code.
3. If `ai_coauthored_only: true` is set in the config, bel-ai-jar first checks whether the commit is **co-authored by an AI tool** (e.g. Claude, Copilot). If no AI co-author is detected, the commit proceeds immediately — no quiz needed.
4. Bel-ai-jar analyzes your staged changes and generates multiple-choice questions using an LLM.
5. You answer the questions in your terminal.
6. If you pass, the commit proceeds. If you fail, the commit is rejected and you must review the changes before trying again.

## Tech Stack

- **Python ≥ 3.8** / **Node.js ≥ 16**: Supported runtimes.
- **Mistral / OpenAI / Gemini / Local Llama**: Pluggable AI backends for question generation.

---

## Installation

### Python (pip)

```bash
pip install bel-ai-jar
```

### JavaScript (npm)

```bash
npm install -g bel-ai-jar
```

---

## Usage

### Initialize Configuration

**Python:**
```bash
bel-ai-jar init
```

**JavaScript:**
```bash
bel-ai-jar init
```

This will guide you through setting up:
- Number of questions to ask (default: 3)
- Number of answer options per question (default: 4)
- AI model selection (Mistral, OpenAI GPT-3.5/4, Google Gemini, or Local Llama)
- Strict mode (default: enabled — must answer all questions correctly)
- Passing grade (if strict mode disabled)
- Additional prompt for question generation

### Disable bel-ai-jar

```bash
bel-ai-jar disable
```

---

## How AI Co-author Detection Works

Bel-ai-jar only runs the evaluation quiz when a commit is **co-authored by an AI tool**. Pure human commits are always passed through without interruption.

### Automatic detection

When you commit with `git commit -m "..."`, git writes the message to `.git/COMMIT_EDITMSG` before the hook runs. Bel-ai-jar scans that file for `Co-Authored-By:` trailers and matches against known AI tool signatures:

| Tool | Detected pattern |
|---|---|
| Claude (Anthropic) | `anthropic`, `claude` |
| GitHub Copilot | `copilot` |
| ChatGPT | `chatgpt`, `openai` |
| Gemini | `gemini` |
| Cursor | `cursor` |
| Codeium | `codeium` |
| Tabnine | `tabnine` |

Example commit message that triggers evaluation:
```
feat: add user authentication

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### Interactive commit fallback

When using `git commit` without `-m` (interactive editor), the hook runs before you type the message, so the co-author trailer isn't available yet. Use the `BEL_AI_JAR_INTERACTIVE_COMMIT` env var to signal that this is an AI-assisted commit:

```bash
# Single commit
BEL_AI_JAR_INTERACTIVE_COMMIT=1 git commit

# Or export for the whole shell session if you're always pairing with AI
export BEL_AI_JAR_INTERACTIVE_COMMIT=1
```

---

## Configuration

Configuration is stored in `.bel-ai-jar.json` in your project root. This file is automatically added to `.gitignore` during `init`. Run `bel-ai-jar help` at any time to see all options and their defaults in your terminal.

| Option | Type | Default | Description |
|---|---|---|---|
| `total_questions` | int | `3` | Questions asked per evaluation |
| `answer_options` | int | `4` | Answer choices per question |
| `strict_mode` | bool | `true` | Require 100% score to pass |
| `passing_grade` | int | `100` | Passing % when `strict_mode` is false |
| `ai_model` | string | `"mistral"` | LLM backend (`mistral` / `openai-gpt3.5` / `openai-gpt4` / `gemini` / `local-llama`) |
| `ai_coauthored_only` | bool | `false` | When `false` (default), every commit triggers evaluation. Set to `true` to only evaluate commits that contain an AI `Co-Authored-By` trailer. |
| `additional_prompt` | string | `null` | Extra instructions appended to the question-generation prompt |
| `max_diff_lines` | int | `1000` | Max diff lines sent to the LLM. Larger diffs are trimmed before prompting to reduce token usage. |
| `excluded_files` | array | see below | Glob patterns of files to skip during diff analysis. |
| `model_params` | object | `{}` | Extra params for the `local-llama` backend, e.g. `{"api_url": "..."}` |

**Default `excluded_files` patterns** (lock files, build artefacts, documentation):
```
*.lock, package-lock.json, yarn.lock, poetry.lock, Pipfile.lock
*.min.js, *.min.css, *.map
dist/*, build/*, *.egg-info/*, __pycache__/*, *.pyc, *.md
```

You can override any of these by editing `.bel-ai-jar.json` directly. For example, to also skip test snapshots and increase the diff budget:

```json
{
  "max_diff_lines": 500,
  "excluded_files": [
    "*.lock", "package-lock.json", "yarn.lock",
    "dist/*", "build/*", "*.md",
    "**/__snapshots__/*"
  ]
}
```

### Security: API Keys

**API keys are never stored in the config file.**

Set your API key as an environment variable before running `bel-ai-jar init`. Use the generic variable (works for any model) or the legacy model-specific ones:

```bash
# Generic — recommended, works for all models
export BEL_AI_JAR_LLM_API_KEY='your-api-key'

# Legacy model-specific fallbacks (still supported)
export MISTRAL_API_KEY='your-mistral-api-key'   # Mistral AI
export OPENAI_API_KEY='your-openai-api-key'     # OpenAI GPT-3.5 / GPT-4
export GOOGLE_API_KEY='your-google-api-key'     # Google Gemini
```

Key resolution priority: **explicit argument** > `BEL_AI_JAR_LLM_API_KEY` > model-specific legacy variable.

Add the export to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) to persist it across sessions. bel-ai-jar will automatically read the key from the environment at runtime.

---

## Development

### Python

```bash
cd src/python

# Install in development mode (includes test dependencies)
pip install -e ".[dev]"

# Run tests
python -m pytest
```

### JavaScript

```bash
cd src/javascript
npm install

# Run tests
npm test
```

---

## Repository Structure

```
bel-ai-jar/
├── src/
│   ├── python/           # Python package (pip)
│   │   ├── bel_ai_jar/   # Source code
│   │   ├── tests/        # Pytest tests
│   │   └── pyproject.toml
│   └── javascript/       # JavaScript package (npm)
│       ├── src/          # Source code
│       ├── tests/        # Jest tests
│       └── package.json
├── documentation/
├── logo.webp
└── README.md
```

---

## Publishing

### PyPI

```bash
cd src/python
pip install build twine
python -m build
twine upload dist/*
```

### npm

```bash
cd src/javascript
npm publish
```

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/ichwanhs96/bel-ai-jar).

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (guided by bel-ai-jar itself 😄)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
