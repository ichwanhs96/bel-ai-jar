"""
CLI interface for bel-ai-jar library
"""
import argparse
import sys
from typing import Optional
from .config import Config
from .git_hooks import setup_git_hooks, remove_git_hooks


def init_command():
    """Initialize bel-ai-jar configuration"""
    print("🚀 Initializing bel-ai-jar configuration...")
    
    # Get user inputs
    num_questions = input("Number of questions to ask (default 3, min 1, max 10): ") or "3"
    num_options = input("Number of answer options per question (default 4, min 2, max 8): ") or "4"
    
    # AI Model selection
    print("\nAI Model Selection:")
    print("1. Mistral AI (default)")
    print("2. OpenAI GPT-3.5")
    print("3. OpenAI GPT-4")
    print("4. Local Llama instance")
    
    model_choice = input("Select AI model (1-4, default 1): ") or "1"
    
    if model_choice == "1":
        ai_model = "mistral"
    elif model_choice == "2":
        ai_model = "openai-gpt3.5"
    elif model_choice == "3":
        ai_model = "openai-gpt4"
    elif model_choice == "4":
        ai_model = "local-llama"
    else:
        ai_model = "mistral"
    
    # API Key for cloud models
    api_key = None
    if ai_model == "mistral":
        api_key = input("Enter Mistral API key (or press Enter to use MISTRAL_API_KEY env var): ") or None
    elif ai_model.startswith("openai"):
        api_key = input("Enter OpenAI API key (or press Enter to use OPENAI_API_KEY env var): ") or None
        
    if api_key and api_key.strip():
        # Simple validation
        if len(api_key.strip()) < 20:
            print("⚠️  API key seems too short. Make sure it's correct.")
    elif ai_model == "local-llama":
        llama_url = input("Enter Local Llama API URL (default http://localhost:8080/completion): ") or "http://localhost:8080/completion"
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
    
    # Create config
    config = Config(
        total_questions=num_questions,
        passing_grade=passing_grade if not strict_mode else 100,
        answer_options=num_options,
        additional_prompt=additional_prompt if additional_prompt.strip() else None,
        strict_mode=strict_mode,
        ai_model=ai_model,
        api_key=api_key if api_key and api_key.strip() else None,
        model_params=model_params if ai_model == "local-llama" else None
    )
    
    # Save config
    config.save()
    
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


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="bel-ai-jar - Git hooks for understanding AI-generated code changes"
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
    
    args = parser.parse_args()
    
    if hasattr(args, "func"):
        args.func()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()