# bel-ai-jar

Git hooks for understanding AI-generated code changes.

## Installation

```bash
pip install bel-ai-jar
```

## Usage

### Initialize configuration

```bash
bel-ai-jar init
```

This will guide you through setting up:
- Number of questions to ask (default: 3)
- Number of answer options per question (default: 4)
- Strict mode (default: enabled)
- Passing grade (if strict mode disabled)
- Additional prompt for question generation

### Disable bel-ai-jar

```bash
bel-ai-jar disable
```

## How it works

1. When you run `git commit`, the pre-commit hook will trigger
2. bel-ai-jar analyzes your staged changes
3. It generates questions about the code changes
4. You answer the questions
5. If you pass the evaluation, your commit proceeds
6. If you fail, you need to review the changes and try again

## Configuration

Configuration is stored in `.bel-ai-jar.json` in your project root.

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest
```