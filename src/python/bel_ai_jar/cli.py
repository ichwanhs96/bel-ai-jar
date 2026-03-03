"""
CLI interface for bel-ai-jar library
"""
import argparse
import os
import sys
from typing import Optional
from pathlib import Path
from .config import Config, DEFAULT_EXCLUDED_FILES
from .git_hooks import setup_git_hooks, remove_git_hooks


def init_command():
    """Initialize bel-ai-jar configuration"""
    print("🚀 Initializing bel-ai-jar configuration...")
    
    def _update_gitignore(config_path: Path) -> None:
        """Add config file to .gitignore if not already present"""
        gitignore_path = Path(".gitignore")
        config_filename = config_path.name
        
        # Create .gitignore if it doesn't exist
        if not gitignore_path.exists():
            gitignore_path.write_text(f"{config_filename}\n")
            return
        
        # Read existing .gitignore
        with open(gitignore_path, "r") as f:
            gitignore_content = f.read()
        
        # Check if config file is already in .gitignore
        if config_filename not in gitignore_content:
            # Add config file to .gitignore
            with open(gitignore_path, "a") as f:
                f.write(f"\n{config_filename}\n")
            print(f"📝 Added {config_filename} to .gitignore")
    
    # Get user inputs
    num_questions = input("Number of questions to ask (default 3, min 1, max 10): ") or "3"
    num_options = input("Number of answer options per question (default 4, min 2, max 8): ") or "4"
    
    # AI Model selection
    print("\nAI Model Selection:")
    print("1. Mistral AI (default)")
    print("2. OpenAI GPT-3.5")
    print("3. OpenAI GPT-4")
    print("4. Google Gemini")
    print("5. Local Llama instance")

    model_choice = input("Select AI model (1-5, default 1): ") or "1"

    if model_choice == "1":
        ai_model = "mistral"
    elif model_choice == "2":
        ai_model = "openai-gpt3.5"
    elif model_choice == "3":
        ai_model = "openai-gpt4"
    elif model_choice == "4":
        ai_model = "gemini"
    elif model_choice == "5":
        ai_model = "local-llama"
    else:
        ai_model = "mistral"

    # API Key guidance — keys are never stored in the config file
    api_key = None
    if ai_model != "local-llama":
        generic_key = os.environ.get("BEL_AI_JAR_LLM_API_KEY")
        if generic_key:
            print("✅ BEL_AI_JAR_LLM_API_KEY environment variable detected.")
        else:
            print(f"\n🔐 Security notice: API keys are NOT stored in the config file.")
            print(f"   Set your key as an environment variable:")
            print(f"   export BEL_AI_JAR_LLM_API_KEY='your-api-key-here'")
            print(f"   (add this to your shell profile, e.g. ~/.zshrc or ~/.bashrc)\n")

    if ai_model == "local-llama":
        llama_url = (
            input("Enter Local Llama API URL (default http://localhost:8080/completion): ")
            or "http://localhost:8080/completion"
        )
        model_params = {"api_url": llama_url}
    else:
        model_params = {}
    
    # Strict mode
    strict_mode = input("Enable strict mode? (Y/n, default Y): ").lower() or "y"
    strict_mode = strict_mode.startswith("y")
    
    passing_grade = None
    if not strict_mode:
        passing_grade = input("Minimum passing grade percentage (e.g., 50 for 50%): ") or "100"
    
    additional_prompt = input("Additional prompt for question generation (press Enter to skip): ")
    
    # Validate inputs
    try:
        num_questions = int(num_questions)
        num_options = int(num_options)
        if not strict_mode:
            passing_grade = int(passing_grade)
        
        if not (1 <= num_questions <= 10):
            raise ValueError("Number of questions must be between 1 and 10")
        if not (2 <= num_options <= 8):
            raise ValueError("Number of options must be between 2 and 8")
        if not strict_mode and not (0 <= passing_grade <= 100):
            raise ValueError("Passing grade must be between 0 and 100")
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    # Create config (api_key is never stored — resolved from env vars at runtime)
    config = Config(
        total_questions=num_questions,
        passing_grade=passing_grade if not strict_mode else 100,
        answer_options=num_options,
        additional_prompt=additional_prompt if additional_prompt.strip() else None,
        strict_mode=strict_mode,
        ai_model=ai_model,
        model_params=model_params if ai_model == "local-llama" else None
    )
    
    # Save config
    config.save()
    
    # Add config file to .gitignore
    _update_gitignore(config.config_path)
    
    # Setup git hooks
    setup_git_hooks()
    
    print("✅ bel-ai-jar initialized successfully!")
    print(f"Configuration saved to {config.config_path}")


def disable_command():
    """Disable bel-ai-jar"""
    print("🔧 Disabling bel-ai-jar...")
    
    # Remove git hooks
    remove_git_hooks()
    
    # Remove config file
    config = Config()
    config.delete_config()
    
    print("✅ bel-ai-jar disabled successfully!")


def evaluate_command():
    """Evaluate code changes (called by git hooks)"""
    from .git_hooks import evaluate_pre_commit
    success = evaluate_pre_commit()
    exit(0 if success else 1)


def help_command():
    """Print detailed help including all config options."""
    config = Config()
    excluded_preview = "\n".join(f"      {p}" for p in DEFAULT_EXCLUDED_FILES)
    print(f"""
bel-ai-jar — Git hooks for understanding AI-generated code changes
Config file: {config.config_path.resolve()} (created by 'init')

COMMANDS
  init       Initialize bel-ai-jar in the current git repository
  disable    Remove git hooks and delete the config file
  evaluate   Run evaluation manually (also called internally by the git hook)
  help       Show this help message

CONFIG OPTIONS (.bel-ai-jar.json)
  total_questions    int    Questions asked per evaluation          (default: 3)
  answer_options     int    Answer choices per question             (default: 4)
  strict_mode        bool   Require 100% score to pass             (default: true)
  passing_grade      int    Passing % when strict_mode is false    (default: 100)
  ai_model           str    LLM backend to use                     (default: "mistral")
                            Options: mistral | openai-gpt3.5 | openai-gpt4 | gemini | local-llama
  additional_prompt  str    Extra instructions for question gen    (default: null)
  max_diff_lines     int    Max diff lines sent to LLM             (default: 1000)
                            Larger diffs are trimmed to this limit before prompting.
  excluded_files     list   Glob patterns of files to skip         (default: see below)
{excluded_preview}
  model_params       obj    Extra params for local-llama backend   (default: {{}})
                            Example: {{"api_url": "http://localhost:8080/completion"}}

API KEYS  (never stored in config — use environment variables)
  BEL_AI_JAR_LLM_API_KEY   Generic key — works for any model (recommended)
  MISTRAL_API_KEY            Legacy fallback for Mistral AI
  OPENAI_API_KEY             Legacy fallback for OpenAI
  GOOGLE_API_KEY             Legacy fallback for Google Gemini

INTERACTIVE COMMIT
  BEL_AI_JAR_INTERACTIVE_COMMIT=1
      Force evaluation when using 'git commit' without -m (interactive editor).
      Evaluation is normally triggered automatically via the Co-Authored-By
      trailer in the commit message.
""")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="bel-ai-jar - Git hooks for understanding AI-generated code changes",
        epilog="Run 'bel-ai-jar help' for detailed config documentation.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize bel-ai-jar configuration")
    init_parser.set_defaults(func=init_command)

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable bel-ai-jar")
    disable_parser.set_defaults(func=disable_command)

    # Evaluate command (for git hooks)
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate code changes (used by git hooks)")
    evaluate_parser.set_defaults(func=evaluate_command)

    # Help command
    help_parser = subparsers.add_parser("help", help="Show detailed help and config documentation")
    help_parser.set_defaults(func=help_command)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()