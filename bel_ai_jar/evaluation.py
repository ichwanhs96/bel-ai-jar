"""
Evaluation and question generation logic for bel-ai-jar
"""
import random
from typing import List, Dict, Tuple, Any
from .config import Config
from .llm_integration import generate_questions_with_llm, AIModel


def generate_questions_from_diff(diff_content: str, config: Config) -> List[Dict[str, Any]]:
    """
    Generate questions from git diff content using LLM
    """
    # Convert config to dict for LLM integration
    config_dict = {
        "total_questions": config.total_questions,
        "answer_options": config.answer_options,
        "additional_prompt": config.additional_prompt,
        "strict_mode": config.strict_mode
    }
    
    # Get the AI model from config
    try:
        ai_model = AIModel(config.ai_model)
    except ValueError:
        # Fallback to default if model is not recognized
        ai_model = AIModel.OPENAI_GPT35
    
    # Generate questions using LLM
    questions = generate_questions_with_llm(
        code_diff=diff_content,
        config=config_dict,
        model=ai_model,
        api_key=config.api_key
    )
    
    # Ensure we have the right number of questions
    if len(questions) < config.total_questions:
        # Fallback: add some heuristic questions if LLM didn't generate enough
        heuristic_questions = _generate_fallback_questions(diff_content, config)
        questions.extend(heuristic_questions[:config.total_questions - len(questions)])
    
    return questions[:config.total_questions]


def _generate_fallback_questions(diff_content: str, config: Config) -> List[Dict[str, Any]]:
    """Generate fallback questions using simple heuristics"""
    questions = []
    lines = diff_content.split('\n')
    
    for i, line in enumerate(lines):
        if line.startswith('+') and ('def ' in line or 'class ' in line):
            question = {
                'question': f"What does this code do: {line[1:]}",
                'options': [
                    f"It defines {line.split(' ')[1].split('(')[0]}",
                    "It creates a new variable",
                    "It imports a module",
                    "It removes existing code"
                ],
                'correct_answer': f"It defines {line.split(' ')[1].split('(')[0]}"
            }
            questions.append(question)
            
            if len(questions) >= config.total_questions:
                break
    
    return questions


def ask_questions(questions: List[Dict[str, Any]]) -> int:
    """Ask questions to the user and return number of correct answers"""
    import sys
    correct_count = 0
    
    print("\n🧠 Code Understanding Evaluation")
    print("=" * 50)
    
    for i, question in enumerate(questions, 1):
        print(f"\nQuestion {i}/{len(questions)}:")
        print(f"{question['question']}")
        
        # Shuffle options
        options = question['options'].copy()
        random.shuffle(options)
        
        # Display options
        for j, option in enumerate(options, 1):
            print(f"{j}. {option}")
        
        # Get user answer with robust input handling
        while True:
            try:
                # Flush output to ensure prompt is shown
                sys.stdout.flush()
                
                # Try multiple input methods
                answer = None
                input_sources = [
                    lambda: input(f"Your answer (1-{len(options)}): "),  # Standard input
                    lambda: sys.stdin.readline().strip(),  # Direct stdin read
                    lambda: open('/dev/tty').readline().strip(),  # Fallback for git hook environment
                ]
                
                for input_method in input_sources:
                    try:
                        answer = input_method()
                        if answer:
                            break
                    except EOFError:
                        continue
                    except (IOError, OSError):  # /dev/tty might not be available
                        continue
                    except Exception:
                        continue
                
                if not answer:
                    print("\n❌ Cannot read input - this typically happens when:")
                    print("  • Running in a non-interactive shell (e.g., scripts, CI/CD)")
                    print("  • Using input redirection or pipes")
                    print("\nSolutions:")
                    print("  • Run 'git commit' directly in your terminal")
                    print("  • Use 'git commit --no-verify' to skip evaluation")
                    print("  • Run 'bel-ai-jar disable' to disable hooks permanently")
                    return 0
                
                answer_idx = int(answer) - 1
                
                if 0 <= answer_idx < len(options):
                    break
                else:
                    print(f"Please enter a number between 1 and {len(options)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n❌ Evaluation cancelled by user")
                return 0
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                return 0
        
        # Check if correct
        user_answer = options[answer_idx]
        if user_answer == question['correct_answer']:
            print("✅ Correct!")
            correct_count += 1
        else:
            print("❌ Incorrect!")
            print(f"The correct answer was: {question['correct_answer']}")
    
    return correct_count


def evaluate_code_changes(diff_content: str, config: Config) -> bool:
    """Evaluate code changes and return whether user passed"""
    print("🔍 Analyzing code changes...")
    
    # Generate questions from diff
    questions = generate_questions_from_diff(diff_content, config)
    
    if not questions:
        print("📝 No questions generated from code changes")
        return True
    
    # Ask questions
    correct_answers = ask_questions(questions)
    
    # Calculate score
    total_questions = len(questions)
    score = (correct_answers / total_questions) * 100
    
    print(f"\n📊 Results: {correct_answers}/{total_questions} correct ({score:.1f}%)")
    
    # Check if passed
    if score >= config.passing_grade:
        print("🎉 Congratulations! You passed the evaluation.")
        return True
    else:
        print(f"💡 Please review the code changes. Minimum passing grade is {config.passing_grade}%")
        return False