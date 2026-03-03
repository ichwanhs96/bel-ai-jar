'use strict';

const fs = require('fs');
const path = require('path');

const CONFIG_FILENAME = '.bel-ai-jar.json';

const DEFAULT_EXCLUDED_FILES = [
  '*.lock',
  'package-lock.json',
  'yarn.lock',
  'poetry.lock',
  'Pipfile.lock',
  '*.min.js',
  '*.min.css',
  '*.map',
  'dist/*',
  'build/*',
  '*.egg-info/*',
  '__pycache__/*',
  '*.pyc',
  '*.md',
];

const DEFAULT_CONFIG = {
  total_questions: 3,
  passing_grade: 100,
  answer_options: 4,
  additional_prompt: null,
  strict_mode: true,
  ai_model: 'mistral',
  model_params: {},
  max_diff_lines: 1000,
  excluded_files: DEFAULT_EXCLUDED_FILES,
  ai_coauthored_only: false,
};

class Config {
  constructor(options = {}) {
    this.total_questions = options.total_questions ?? DEFAULT_CONFIG.total_questions;
    this.passing_grade = options.passing_grade ?? DEFAULT_CONFIG.passing_grade;
    this.answer_options = options.answer_options ?? DEFAULT_CONFIG.answer_options;
    this.additional_prompt = options.additional_prompt ?? DEFAULT_CONFIG.additional_prompt;
    this.strict_mode = options.strict_mode ?? DEFAULT_CONFIG.strict_mode;
    this.ai_model = options.ai_model ?? DEFAULT_CONFIG.ai_model;
    this.model_params = options.model_params ?? DEFAULT_CONFIG.model_params;
    this.max_diff_lines = options.max_diff_lines ?? DEFAULT_CONFIG.max_diff_lines;
    this.excluded_files = options.excluded_files ?? [...DEFAULT_EXCLUDED_FILES];
    this.ai_coauthored_only = options.ai_coauthored_only ?? DEFAULT_CONFIG.ai_coauthored_only;
    // api_key is NEVER stored — resolved from environment variables at runtime
    this.config_path = CONFIG_FILENAME;
  }

  /**
   * Save configuration to .bel-ai-jar.json.
   * NOTE: API keys are never written to disk for security reasons.
   * Use environment variables (MISTRAL_API_KEY, OPENAI_API_KEY) instead.
   */
  save() {
    const data = {
      total_questions: this.total_questions,
      passing_grade: this.passing_grade,
      answer_options: this.answer_options,
      additional_prompt: this.additional_prompt,
      strict_mode: this.strict_mode,
      ai_model: this.ai_model,
      model_params: this.model_params,
      max_diff_lines: this.max_diff_lines,
      excluded_files: this.excluded_files,
      ai_coauthored_only: this.ai_coauthored_only,
    };
    fs.writeFileSync(this.config_path, JSON.stringify(data, null, 2), 'utf8');
  }

  /** Load raw config object from file, or return defaults if not found. */
  load() {
    if (!fs.existsSync(this.config_path)) {
      return { ...DEFAULT_CONFIG };
    }
    const raw = JSON.parse(fs.readFileSync(this.config_path, 'utf8'));
    // Strip any api_key written by an older version
    delete raw.api_key;
    return raw;
  }

  /** Delete the config file. */
  deleteConfig() {
    if (fs.existsSync(this.config_path)) {
      fs.unlinkSync(this.config_path);
    }
  }

  /** Create a Config instance populated from an existing config file. */
  static fromFile() {
    const tmp = new Config();
    const data = tmp.load();
    return new Config(data);
  }
}

module.exports = { Config, DEFAULT_CONFIG, DEFAULT_EXCLUDED_FILES, CONFIG_FILENAME };
