'use strict';

const os = require('os');
const fs = require('fs');
const path = require('path');

// Run each test in a unique temp directory so config files don't bleed across tests.
let tmpDir;
let originalCwd;

beforeEach(() => {
  originalCwd = process.cwd();
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bel-ai-jar-test-'));
  process.chdir(tmpDir);
});

afterEach(() => {
  process.chdir(originalCwd);
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

const { Config, DEFAULT_CONFIG } = require('../src/config');

describe('Config – defaults', () => {
  test('default values match DEFAULT_CONFIG', () => {
    const c = new Config();
    expect(c.total_questions).toBe(3);
    expect(c.passing_grade).toBe(100);
    expect(c.answer_options).toBe(4);
    expect(c.additional_prompt).toBeNull();
    expect(c.strict_mode).toBe(true);
    expect(c.ai_model).toBe('mistral');
    expect(c.model_params).toEqual({});
  });
});

describe('Config – save / load', () => {
  test('save() creates the config file', () => {
    const c = new Config({ total_questions: 5 });
    c.save();
    expect(fs.existsSync('.bel-ai-jar.json')).toBe(true);
  });

  test('save() does NOT write api_key to disk', () => {
    const c = new Config({ total_questions: 3 });
    // Simulate legacy usage where api_key was passed
    c.api_key = 'super-secret';
    c.save();
    const raw = JSON.parse(fs.readFileSync('.bel-ai-jar.json', 'utf8'));
    expect(raw).not.toHaveProperty('api_key');
  });

  test('load() returns defaults when no file exists', () => {
    const c = new Config();
    expect(c.load()).toMatchObject(DEFAULT_CONFIG);
  });

  test('load() strips legacy api_key from disk', () => {
    fs.writeFileSync('.bel-ai-jar.json', JSON.stringify({ total_questions: 3, api_key: 'leaked' }));
    const c = new Config();
    const data = c.load();
    expect(data).not.toHaveProperty('api_key');
  });

  test('fromFile() round-trips all supported fields', () => {
    new Config({
      total_questions: 7,
      passing_grade: 80,
      answer_options: 3,
      additional_prompt: 'Focus on security',
      strict_mode: false,
      ai_model: 'openai-gpt4',
    }).save();

    const loaded = Config.fromFile();
    expect(loaded.total_questions).toBe(7);
    expect(loaded.passing_grade).toBe(80);
    expect(loaded.answer_options).toBe(3);
    expect(loaded.additional_prompt).toBe('Focus on security');
    expect(loaded.strict_mode).toBe(false);
    expect(loaded.ai_model).toBe('openai-gpt4');
  });
});

describe('Config – deleteConfig', () => {
  test('removes the config file', () => {
    const c = new Config();
    c.save();
    c.deleteConfig();
    expect(fs.existsSync('.bel-ai-jar.json')).toBe(false);
  });

  test('no-op when file does not exist', () => {
    expect(() => new Config().deleteConfig()).not.toThrow();
  });
});
