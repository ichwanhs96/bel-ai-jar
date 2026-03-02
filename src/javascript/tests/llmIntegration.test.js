'use strict';

const { AI_MODELS, fallbackQuestions, buildPrompt } = require('../src/llmIntegration');

const SAMPLE_CONFIG = { total_questions: 2, answer_options: 4, additional_prompt: '' };

const SAMPLE_DIFF = `
+function add(a, b) {
+  return a + b;
+}
+class Calculator {}
`;

describe('fallbackQuestions', () => {
  test('generates questions from function/class lines', () => {
    const qs = fallbackQuestions(SAMPLE_DIFF, SAMPLE_CONFIG);
    expect(Array.isArray(qs)).toBe(true);
    expect(qs.length).toBeGreaterThan(0);
  });

  test('does not exceed total_questions', () => {
    const qs = fallbackQuestions(SAMPLE_DIFF, { ...SAMPLE_CONFIG, total_questions: 1 });
    expect(qs.length).toBeLessThanOrEqual(1);
  });

  test('returns empty array for empty diff', () => {
    expect(fallbackQuestions('', SAMPLE_CONFIG)).toEqual([]);
  });

  test('each question has required fields', () => {
    const qs = fallbackQuestions(SAMPLE_DIFF, SAMPLE_CONFIG);
    for (const q of qs) {
      expect(q).toHaveProperty('question');
      expect(q).toHaveProperty('options');
      expect(q).toHaveProperty('correct_answer');
      expect(Array.isArray(q.options)).toBe(true);
    }
  });
});

describe('buildPrompt', () => {
  test('includes the diff content', () => {
    const prompt = buildPrompt('def foo(): pass', SAMPLE_CONFIG);
    expect(prompt).toContain('def foo(): pass');
  });

  test('mentions the configured number of questions', () => {
    const prompt = buildPrompt('diff', { ...SAMPLE_CONFIG, total_questions: 5 });
    expect(prompt).toContain('5');
  });
});

describe('AI_MODELS constants', () => {
  test('defines expected models', () => {
    expect(AI_MODELS.MISTRAL).toBe('mistral');
    expect(AI_MODELS.OPENAI_GPT35).toBe('openai-gpt3.5');
    expect(AI_MODELS.OPENAI_GPT4).toBe('openai-gpt4');
    expect(AI_MODELS.LOCAL_LLAMA).toBe('local-llama');
  });
});
