#!/usr/bin/env node
'use strict';

/**
 * CLI entry point for bel-ai-jar (JavaScript/npm)
 */

const readline = require('readline');
const fs = require('fs');
const path = require('path');
const { Config } = require('./config');
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
    console.log('4. Local Llama instance');
    const modelChoice = (await ask(rl, 'Select AI model (1-4, default 1): ')) || '1';

    const modelMap = { '1': 'mistral', '2': 'openai-gpt3.5', '3': 'openai-gpt4', '4': 'local-llama' };
    const aiModel = modelMap[modelChoice] || 'mistral';

    // API keys are never stored — guide user to use environment variables
    if (aiModel === 'mistral') {
      if (!process.env.MISTRAL_API_KEY) {
        console.log('\n🔐 Security notice: API keys are NOT stored in the config file.');
        console.log('   Set your key as an environment variable:');
        console.log('   export MISTRAL_API_KEY=\'your-api-key-here\'');
        console.log('   (add this to your shell profile, e.g. ~/.zshrc or ~/.bashrc)\n');
      } else {
        console.log('✅ MISTRAL_API_KEY environment variable detected.');
      }
    } else if (aiModel.startsWith('openai')) {
      if (!process.env.OPENAI_API_KEY) {
        console.log('\n🔐 Security notice: API keys are NOT stored in the config file.');
        console.log('   Set your key as an environment variable:');
        console.log('   export OPENAI_API_KEY=\'your-api-key-here\'');
        console.log('   (add this to your shell profile, e.g. ~/.zshrc or ~/.bashrc)\n');
      } else {
        console.log('✅ OPENAI_API_KEY environment variable detected.');
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
    default:
      console.log('bel-ai-jar - Git hooks for understanding AI-generated code changes');
      console.log('\nUsage: bel-ai-jar <command>');
      console.log('\nCommands:');
      console.log('  init       Initialize bel-ai-jar configuration');
      console.log('  disable    Disable bel-ai-jar');
      console.log('  evaluate   Evaluate code changes (used by git hooks)');
  }
}

main().catch((err) => {
  console.error(`❌ ${err.message}`);
  process.exit(1);
});
