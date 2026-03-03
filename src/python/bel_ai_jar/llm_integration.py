"""
LLM Integration for bel-ai-jar
Handles communication with various AI models for question generation
"""
import os
import json
import requests
from typing import List, Dict, Any, Optional
from enum import Enum
import logging


class AIModel(Enum):
    """Supported AI models"""
    MISTRAL = "mistral"
    OPENAI_GPT35 = "openai-gpt3.5"
    OPENAI_GPT4 = "openai-gpt4"
    GEMINI = "gemini"
    LOCAL_LLAMA = "local-llama"


def _resolve_api_key(model: "AIModel", explicit_key: Optional[str] = None) -> Optional[str]:
    """Resolve the API key with priority:
      1. Explicitly passed key
      2. BEL_AI_JAR_LLM_API_KEY (generic, model-agnostic)
      3. Legacy model-specific env vars (backward-compatible fallback)
    """
    if explicit_key:
        return explicit_key
    generic = os.environ.get("BEL_AI_JAR_LLM_API_KEY")
    if generic:
        return generic
    # Legacy fallbacks
    if model == AIModel.MISTRAL:
        return os.environ.get("MISTRAL_API_KEY")
    if model in (AIModel.OPENAI_GPT35, AIModel.OPENAI_GPT4):
        return os.environ.get("OPENAI_API_KEY")
    if model == AIModel.GEMINI:
        return os.environ.get("GOOGLE_API_KEY")
    return None


class LLMClient:
    """Base LLM client class"""
    
    def __init__(self, model: AIModel, api_key: Optional[str] = None, **kwargs):
        self.model = model
        self.api_key = api_key
        self.extra_params = kwargs
        
    def generate_questions(self, code_diff: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate questions from code diff using LLM"""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI API client"""
    
    def __init__(self, model: AIModel, api_key: str, **kwargs):
        super().__init__(model, api_key, **kwargs)
        if model == AIModel.MISTRAL:
            self.base_url = kwargs.get("base_url", "https://api.mistral.ai/v1")
        else:
            self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")
        
    def generate_questions(self, code_diff: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate questions using OpenAI/Mistral API"""
        if self.model == AIModel.MISTRAL:
            model_name = "mistral-tiny"  # or other Mistral model
            base_url = self.extra_params.get("base_url", "https://api.mistral.ai/v1")
        elif self.model == AIModel.OPENAI_GPT35:
            model_name = "gpt-3.5-turbo"
            base_url = self.extra_params.get("base_url", "https://api.openai.com/v1")
        else:  # OPENAI_GPT4
            model_name = "gpt-4"
            base_url = self.extra_params.get("base_url", "https://api.openai.com/v1")
        
        # Build prompt
        prompt = self._build_prompt(code_diff, config)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Handle different response formats
            if "choices" in result and len(result["choices"]) > 0:
                questions_json = result["choices"][0]["message"]["content"]
            elif "outputs" in result and len(result["outputs"]) > 0:
                questions_json = result["outputs"][0]["text"]
            else:
                questions_json = str(result)
            
            # Clean up the response - remove markdown formatting if present
            questions_json = questions_json.strip()
            if questions_json.startswith("```json"):
                questions_json = questions_json[7:].strip()
            if questions_json.endswith("```"):
                questions_json = questions_json[:-3].strip()
            
            # Parse the JSON response with robust error handling
            try:
                # Try to parse the full response first
                questions = json.loads(questions_json)
                if isinstance(questions, list):
                    return questions
                else:
                    return [questions] if questions else []
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse LLM response as JSON: {e}")
                logging.error(f"Response content length: {len(questions_json)}")
                logging.error(f"Response preview: {questions_json[:300]}...")
                
                # Try to extract valid JSON from partial response
                try:
                    # Look for the first valid JSON array in the response
                    start = questions_json.find('[')
                    if start != -1:
                        # Try to find matching closing bracket
                        brace_count = 0
                        for i, char in enumerate(questions_json[start:]):
                            if char == '[':
                                brace_count += 1
                            elif char == ']':
                                brace_count -= 1
                                if brace_count == 0:
                                    partial_json = questions_json[start:start+i+1]
                                    questions = json.loads(partial_json)
                                    if isinstance(questions, list):
                                        return questions
                                    break
                except Exception:
                    pass
                
                logging.error("Falling back to heuristic questions")
                return self._fallback_questions(code_diff, config)
            
        except Exception as e:
            logging.error(f"OpenAI/Mistral API error: {e}")
            return self._fallback_questions(code_diff, config)
    
    def _build_prompt(self, code_diff: str, config: Dict[str, Any]) -> str:
        """Build prompt for question generation"""
        additional_prompt = config.get("additional_prompt", "")
        num_questions = config.get("total_questions", 3)
        num_options = config.get("answer_options", 4)
        
        prompt = f"""You are a coding educator. Analyze the following code changes and generate {num_questions} multiple-choice questions to help the developer understand what the code does.

Code changes:
{code_diff}

{additional_prompt}

Requirements:
1. Generate exactly {num_questions} questions
2. Each question should have exactly {num_options} answer options
3. Only one option should be correct
4. Questions should test understanding of the code changes
5. Return ONLY valid JSON, nothing else
6. The JSON must be parseable and follow this exact format:
[
  {{
    "question": "Your question here",
    "options": ["option1", "option2", "option3", "option4"],
    "correct_answer": "The correct option"
  }}
]

IMPORTANT: Respond with ONLY the JSON array, no explanations, no markdown, just valid JSON."""
        
        return prompt
    
    def _fallback_questions(self, code_diff: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fallback questions if API fails"""
        questions = []
        lines = code_diff.split('\n')
        
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
                
                if len(questions) >= config.get("total_questions", 3):
                    break
        
        return questions


class GeminiClient(LLMClient):
    """Google Gemini API client"""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODEL_NAME = "gemini-1.5-flash"

    def __init__(self, model: AIModel, api_key: Optional[str] = None, **kwargs):
        super().__init__(model, api_key, **kwargs)

    def generate_questions(self, code_diff: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate questions using Google Gemini API"""
        if not self.api_key:
            logging.error("No API key found for Gemini. Using fallback questions.")
            return self._fallback_questions(code_diff, config)

        prompt = self._build_prompt(code_diff, config)
        url = f"{self.BASE_URL}/{self.MODEL_NAME}:generateContent?key={self.api_key}"

        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000},
        }

        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            questions_json = result["candidates"][0]["content"]["parts"][0]["text"]

            questions_json = questions_json.strip()
            if questions_json.startswith("```json"):
                questions_json = questions_json[7:].strip()
            if questions_json.endswith("```"):
                questions_json = questions_json[:-3].strip()

            try:
                questions = json.loads(questions_json)
                if isinstance(questions, list):
                    return questions
                return [questions] if questions else []
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse Gemini response as JSON: {e}")
                return self._fallback_questions(code_diff, config)

        except Exception as e:
            logging.error(f"Gemini API error: {e}")
            return self._fallback_questions(code_diff, config)

    def _build_prompt(self, code_diff: str, config: Dict[str, Any]) -> str:
        """Build prompt for Gemini"""
        additional_prompt = config.get("additional_prompt", "")
        num_questions = config.get("total_questions", 3)
        num_options = config.get("answer_options", 4)

        return f"""You are a coding educator. Analyze the following code changes and generate {num_questions} multiple-choice questions to help the developer understand what the code does.

Code changes:
{code_diff}

{additional_prompt}

Requirements:
1. Generate exactly {num_questions} questions
2. Each question should have exactly {num_options} answer options
3. Only one option should be correct
4. Questions should test understanding of the code changes
5. Return ONLY valid JSON, nothing else
6. The JSON must be parseable and follow this exact format:
[
  {{
    "question": "Your question here",
    "options": ["option1", "option2", "option3", "option4"],
    "correct_answer": "The correct option"
  }}
]

IMPORTANT: Respond with ONLY the JSON array, no explanations, no markdown, just valid JSON."""

    def _fallback_questions(self, code_diff: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        return OpenAIClient(self.model, "")._fallback_questions(code_diff, config)


class LocalLlamaClient(LLMClient):
    """Local Llama.cpp client"""
    
    def __init__(self, model: AIModel, api_key: str = None, **kwargs):
        super().__init__(model, api_key, **kwargs)
        self.api_url = kwargs.get("api_url", "http://localhost:8080/completion")
        
    def generate_questions(self, code_diff: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate questions using local Llama instance"""
        prompt = self._build_prompt(code_diff, config)
        
        data = {
            "prompt": prompt,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stop": ["\n"]
        }
        
        try:
            response = requests.post(self.api_url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            questions_json = result.get("content", "")
            
            # Clean up the response
            questions_json = questions_json.strip()
            
            # Try to parse JSON
            try:
                questions = json.loads(questions_json)
                return questions
            except json.JSONDecodeError:
                # Fallback parsing
                return self._fallback_questions(code_diff, config)
                
        except Exception as e:
            logging.error(f"Local Llama API error: {e}")
            return self._fallback_questions(code_diff, config)
    
    def _build_prompt(self, code_diff: str, config: Dict[str, Any]) -> str:
        """Build prompt for local Llama"""
        additional_prompt = config.get("additional_prompt", "")
        num_questions = config.get("total_questions", 3)
        num_options = config.get("answer_options", 4)
        
        return f"<s>[INST] <<SYS>>\nYou are a coding educator. Analyze code changes and generate multiple-choice questions.\n<</SYS>>\n\nCode changes:\n{code_diff}\n\n{additional_prompt}\n\nGenerate exactly {num_questions} questions with {num_options} options each. Return only valid JSON.[/INST]"
    
    def _fallback_questions(self, code_diff: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Same fallback as OpenAI"""
        return OpenAIClient(self.model, "")._fallback_questions(code_diff, config)


def get_llm_client(model: AIModel, api_key: Optional[str] = None, **kwargs) -> LLMClient:
    """Factory function to get appropriate LLM client"""
    resolved_key = _resolve_api_key(model, api_key)
    if model == AIModel.MISTRAL:
        return OpenAIClient(model, resolved_key, **kwargs)
    elif model in [AIModel.OPENAI_GPT35, AIModel.OPENAI_GPT4]:
        return OpenAIClient(model, resolved_key, **kwargs)
    elif model == AIModel.GEMINI:
        return GeminiClient(model, resolved_key, **kwargs)
    elif model == AIModel.LOCAL_LLAMA:
        return LocalLlamaClient(model, **kwargs)
    else:
        raise ValueError(f"Unsupported model: {model}")


def generate_questions_with_llm(
    code_diff: str,
    config: Dict[str, Any],
    model: AIModel = AIModel.OPENAI_GPT35,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generate questions using LLM"""
    try:
        client = get_llm_client(model, api_key)
        return client.generate_questions(code_diff, config)
    except Exception as e:
        logging.error(f"LLM generation failed: {e}")
        # Fallback to simple heuristic
        return OpenAIClient(model, "")._fallback_questions(code_diff, config)