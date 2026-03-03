'use strict';

/**
 * LLM Integration for bel-ai-jar (JavaScript)
 * Handles communication with various AI models for question generation.
 */

const AI_MODELS = {
  MISTRAL: 'mistral',
  OPENAI_GPT35: 'openai-gpt3.5',
  OPENAI_GPT4: 'openai-gpt4',
  GEMINI: 'gemini',
  LOCAL_LLAMA: 'local-llama',
};

/**
 * Build the question-generation prompt.
 */
function buildPrompt(codeDiff, config) {
  const numQuestions = config.total_questions ?? 3;
  const numOptions = config.answer_options ?? 4;
  const additionalPrompt = config.additional_prompt ?? '';

  return `You are a coding educator. Analyze the following code changes and generate ${numQuestions} multiple-choice questions to help the developer understand what the code does.

Code changes:
${codeDiff}

${additionalPrompt}

Requirements:
1. Generate exactly ${numQuestions} questions
2. Each question should have exactly ${numOptions} answer options
3. Only one option should be correct
4. Questions should test understanding of the code changes
5. Return ONLY valid JSON, nothing else
6. The JSON must be parseable and follow this exact format:
[
  {
    "question": "Your question here",
    "options": ["option1", "option2", "option3", "option4"],
    "correct_answer": "The correct option"
  }
]

IMPORTANT: Respond with ONLY the JSON array, no explanations, no markdown, just valid JSON.`;
}

/**
 * Heuristic fallback questions derived from the diff without calling an LLM.
 */
function fallbackQuestions(codeDiff, config) {
  const numQuestions = config.total_questions ?? 3;
  const questions = [];
  const lines = codeDiff.split('\n');

  for (const line of lines) {
    if (
      line.startsWith('+') &&
      (line.includes('function ') || line.includes('class ') || line.includes('const ') || line.includes('def '))
    ) {
      const name = line.replace(/^[+\s]*(function|class|const|def)\s+/, '').split(/[\s(={]/)[0];
      questions.push({
        question: `What does this code do: ${line.slice(1).trim()}`,
        options: [
          `It defines ${name}`,
          'It creates a new variable',
          'It imports a module',
          'It removes existing code',
        ],
        correct_answer: `It defines ${name}`,
      });
      if (questions.length >= numQuestions) break;
    }
  }
  return questions;
}

/**
 * Resolve API key from environment for the given model.
 * Priority: BEL_AI_JAR_LLM_API_KEY > legacy model-specific vars.
 */
function resolveApiKey(model) {
  const generic = process.env.BEL_AI_JAR_LLM_API_KEY;
  if (generic) return generic;
  if (model === AI_MODELS.MISTRAL) return process.env.MISTRAL_API_KEY || null;
  if (model.startsWith('openai')) return process.env.OPENAI_API_KEY || null;
  if (model === AI_MODELS.GEMINI) return process.env.GOOGLE_API_KEY || null;
  return null;
}

/**
 * Call the OpenAI-compatible chat completions endpoint (used for Mistral and OpenAI).
 */
async function callOpenAICompatible(codeDiff, config, model, apiKey) {
  // Dynamic import so the package works without bundling fetch polyfills
  const fetch = (await import('node-fetch')).default;

  let baseUrl;
  let modelName;
  if (model === AI_MODELS.MISTRAL) {
    baseUrl = 'https://api.mistral.ai/v1';
    modelName = 'mistral-tiny';
  } else if (model === AI_MODELS.OPENAI_GPT35) {
    baseUrl = 'https://api.openai.com/v1';
    modelName = 'gpt-3.5-turbo';
  } else {
    baseUrl = 'https://api.openai.com/v1';
    modelName = 'gpt-4';
  }

  const prompt = buildPrompt(codeDiff, config);

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: modelName,
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.7,
      max_tokens: 1000,
    }),
    signal: AbortSignal.timeout(30_000),
  });

  response.ok || (() => { throw new Error(`HTTP ${response.status}`); })();
  const result = await response.json();
  let raw =
    result?.choices?.[0]?.message?.content ||
    result?.outputs?.[0]?.text ||
    JSON.stringify(result);

  raw = raw.trim();
  if (raw.startsWith('```json')) raw = raw.slice(7).trim();
  if (raw.endsWith('```')) raw = raw.slice(0, -3).trim();

  return JSON.parse(raw);
}

/**
 * Call a local Llama.cpp instance.
 */
async function callLocalLlama(codeDiff, config, apiUrl = 'http://localhost:8080/completion') {
  const fetch = (await import('node-fetch')).default;

  const prompt = buildPrompt(codeDiff, config);
  const response = await fetch(apiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, temperature: 0.7, max_tokens: 1000 }),
    signal: AbortSignal.timeout(30_000),
  });

  response.ok || (() => { throw new Error(`HTTP ${response.status}`); })();
  const result = await response.json();
  return JSON.parse(result.content);
}

/**
 * Call the Google Gemini API.
 */
async function callGemini(codeDiff, config, apiKey) {
  const fetch = (await import('node-fetch')).default;

  const prompt = buildPrompt(codeDiff, config);
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.7, maxOutputTokens: 1000 },
    }),
    signal: AbortSignal.timeout(30_000),
  });

  response.ok || (() => { throw new Error(`HTTP ${response.status}`); })();
  const result = await response.json();
  let raw = result?.candidates?.[0]?.content?.parts?.[0]?.text || '';

  raw = raw.trim();
  if (raw.startsWith('```json')) raw = raw.slice(7).trim();
  if (raw.endsWith('```')) raw = raw.slice(0, -3).trim();

  return JSON.parse(raw);
}

/**
 * Generate questions using the configured LLM, with fallback on failure.
 *
 * @param {string} codeDiff
 * @param {object} config
 * @returns {Promise<Array>}
 */
async function generateQuestionsWithLLM(codeDiff, config) {
  const model = config.ai_model ?? AI_MODELS.MISTRAL;
  const apiKey = resolveApiKey(model);

  try {
    if (model === AI_MODELS.LOCAL_LLAMA) {
      const apiUrl = config.model_params?.api_url;
      return await callLocalLlama(codeDiff, config, apiUrl);
    }
    if (!apiKey) {
      console.error(`[bel-ai-jar] No API key found for model "${model}". Using fallback questions.`);
      return fallbackQuestions(codeDiff, config);
    }
    if (model === AI_MODELS.GEMINI) {
      return await callGemini(codeDiff, config, apiKey);
    }
    return await callOpenAICompatible(codeDiff, config, model, apiKey);
  } catch (err) {
    console.error(`[bel-ai-jar] LLM generation failed: ${err.message}. Using fallback questions.`);
    return fallbackQuestions(codeDiff, config);
  }
}

module.exports = { AI_MODELS, generateQuestionsWithLLM, fallbackQuestions, buildPrompt };
