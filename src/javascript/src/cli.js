#!/usr/bin/env node
'use strict';

/**
 * CLI entry point for bel-ai-jar (JavaScript/npm)
 */

const readline = require('readline');
const fs = require('fs');
const path = require('path');
const { Config, DEFAULT_EXCLUDED_FILES } = require('./config');
const { setupGitHooks, removeGitHooks } = require('./gitHooks');

const CONFIG_FILENAME = '.bel-ai-jar.json';

function ask(rl, question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

function updateGitignore(configFilename) {
  const gitignorePath = '.gitignore';
  if (!fs.existsSync(gitignorePath)) {
    fs.writeFileSync(gitignorePath, `${configFilename}\n`, 'utf8');
    return;
  }
  const content = fs.readFileSync(gitignorePath, 'utf8');
  if (!content.includes(configFilename)) {
    fs.appendFileSync(gitignorePath, `\n${configFilename}\n`, 'utf8');
    console.log(`📝 Added ${configFilename} to .gitignore`);
  }
}

async function initCommand() {
  console.log('🚀 Initializing bel-ai-jar configuration...');

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  try {
    const numQuestionsRaw = (await ask(rl, 'Number of questions to ask (default 3, min 1, max 10): ')) || '3';
    const numOptionsRaw = (await ask(rl, 'Number of answer options per question (default 4, min 2, max 8): ')) || '4';

    console.log('\nAI Model Selection:');
    console.log('1. Mistral AI (default)');
    console.log('2. OpenAI GPT-3.5');
    console.log('3. OpenAI GPT-4');
    console.log('4. Google Gemini');
    console.log('5. Local Llama instance');
    const modelChoice = (await ask(rl, 'Select AI model (1-5, default 1): ')) || '1';

    const modelMap = {
      '1': 'mistral',
      '2': 'openai-gpt3.5',
      '3': 'openai-gpt4',
      '4': 'gemini',
      '5': 'local-llama',
    };
    const aiModel = modelMap[modelChoice] || 'mistral';

    // API keys are never stored — guide user to use environment variables
    if (aiModel !== 'local-llama') {
      if (process.env.BEL_AI_JAR_LLM_API_KEY) {
        console.log('✅ BEL_AI_JAR_LLM_API_KEY environment variable detected.');
      } else {
        console.log('\n🔐 Security notice: API keys are NOT stored in the config file.');
        console.log('   Set your key as an environment variable:');
        console.log('   export BEL_AI_JAR_LLM_API_KEY=\'your-api-key-here\'');
        console.log('   (add this to your shell profile, e.g. ~/.zshrc or ~/.bashrc)\n');
      }
    }

    let modelParams = {};
    if (aiModel === 'local-llama') {
      const llamaUrl =
        (await ask(rl, 'Enter Local Llama API URL (default http://localhost:8080/completion): ')) ||
        'http://localhost:8080/completion';
      modelParams = { api_url: llamaUrl };
    }


    const strictRaw = ((await ask(rl, 'Enable strict mode? (Y/n, default Y): ')) || 'y').toLowerCase();
    const strictMode = strictRaw.startsWith('y');

    let passingGrade = 100;
    if (!strictMode) {
      passingGrade = parseInt((await ask(rl, 'Minimum passing grade percentage (e.g. 50 for 50%): ')) || '100', 10);
    }

    const additionalPrompt = (await ask(rl, 'Additional prompt for question generation (press Enter to skip): ')) || null;

    // Validate
    const numQuestions = parseInt(numQuestionsRaw, 10);
    const numOptions = parseInt(numOptionsRaw, 10);
    if (!(numQuestions >= 1 && numQuestions <= 10)) {
      console.error('❌ Number of questions must be between 1 and 10');
      process.exit(1);
    }
    if (!(numOptions >= 2 && numOptions <= 8)) {
      console.error('❌ Number of options must be between 2 and 8');
      process.exit(1);
    }
    if (!strictMode && !(passingGrade >= 0 && passingGrade <= 100)) {
      console.error('❌ Passing grade must be between 0 and 100');
      process.exit(1);
    }

    const config = new Config({
      total_questions: numQuestions,
      passing_grade: strictMode ? 100 : passingGrade,
      answer_options: numOptions,
      additional_prompt: additionalPrompt?.trim() || null,
      strict_mode: strictMode,
      ai_model: aiModel,
      model_params: aiModel === 'local-llama' ? modelParams : {},
    });

    config.save();
    updateGitignore(CONFIG_FILENAME);
    setupGitHooks();

    console.log('✅ bel-ai-jar initialized successfully!');
    console.log(`Configuration saved to ${config.config_path}`);
  } finally {
    rl.close();
  }
}

async function disableCommand() {
  console.log('🔧 Disabling bel-ai-jar...');
  removeGitHooks();
  const config = new Config();
  config.deleteConfig();
  console.log('✅ bel-ai-jar disabled successfully!');
}

async function evaluateCommand() {
  const { evaluatePreCommit } = require('./gitHooks');
  const ok = await evaluatePreCommit();
  process.exit(ok ? 0 : 1);
}

function helpCommand() {
  const config = new Config();
  const excludedPreview = DEFAULT_EXCLUDED_FILES.map((p) => `      ${p}`).join('\n');
  console.log(`
bel-ai-jar — Git hooks for understanding AI-generated code changes
Config file: ${path.resolve(config.config_path)} (created by 'init')

COMMANDS
  init       Initialize bel-ai-jar in the current git repository
  disable    Remove git hooks and delete the config file
  evaluate   Run evaluation manually (also called internally by the git hook)
  help       Show this help message

CONFIG OPTIONS (.bel-ai-jar.json)
  total_questions    number   Questions asked per evaluation          (default: 3)
  answer_options     number   Answer choices per question             (default: 4)
  strict_mode        boolean  Require 100% score to pass             (default: true)
  passing_grade      number   Passing % when strict_mode is false    (default: 100)
  ai_model           string   LLM backend to use                     (default: "mistral")
                              Options: mistral | openai-gpt3.5 | openai-gpt4 | gemini | local-llama
  ai_coauthored_only boolean  Only evaluate AI co-authored commits   (default: false)
                              false = evaluate every commit (recommended)
                              true  = skip commits without an AI Co-Authored-By trailer
  additional_prompt  string   Extra instructions for question gen    (default: null)
  max_diff_lines     number   Max diff lines sent to LLM             (default: 1000)
                              Larger diffs are trimmed to this limit before prompting.
  excluded_files     array    Glob patterns of files to skip         (default: see below)
${excludedPreview}
  model_params       object   Extra params for local-llama backend   (default: {})
                              Example: {"api_url": "http://localhost:8080/completion"}

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
`);
}

async function main() {
  const [, , command] = process.argv;

  switch (command) {
    case 'init':
      await initCommand();
      break;
    case 'disable':
      await disableCommand();
      break;
    case 'evaluate':
      await evaluateCommand();
      break;
    case 'help':
    case '--help':
    case '-h':
      helpCommand();
      break;
    default:
      console.log('bel-ai-jar - Git hooks for understanding AI-generated code changes');
      console.log('\nUsage: bel-ai-jar <command>');
      console.log('\nCommands:');
      console.log('  init       Initialize bel-ai-jar configuration');
      console.log('  disable    Disable bel-ai-jar');
      console.log('  evaluate   Evaluate code changes (used by git hooks)');
      console.log('  help       Show detailed help and config documentation');
  }
}

main().catch((err) => {
  console.error(`❌ ${err.message}`);
  process.exit(1);
});
