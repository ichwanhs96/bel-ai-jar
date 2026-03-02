'use strict';

const readline = require('readline');
const { generateQuestionsWithLLM, fallbackQuestions } = require('./llmIntegration');

/**
 * Generate questions from a git diff, falling back to heuristics when the LLM
 * returns fewer questions than configured.
 *
 * @param {string} diffContent
 * @param {import('./config').Config} config
 * @returns {Promise<Array>}
 */
async function generateQuestionsFromDiff(diffContent, config) {
  const configObj = {
    total_questions: config.total_questions,
    answer_options: config.answer_options,
    additional_prompt: config.additional_prompt,
    strict_mode: config.strict_mode,
    ai_model: config.ai_model,
    model_params: config.model_params,
  };

  let questions = await generateQuestionsWithLLM(diffContent, configObj);

  if (questions.length < config.total_questions) {
    const extra = fallbackQuestions(diffContent, configObj);
    questions = questions.concat(extra).slice(0, config.total_questions);
  }

  return questions.slice(0, config.total_questions);
}

/**
 * Shuffle an array in-place (Fisher-Yates).
 */
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/**
 * Ask the user a single question interactively.
 *
 * @param {object} question
 * @param {number} index  1-based question number
 * @param {number} total  total questions
 * @param {readline.Interface} rl
 * @returns {Promise<boolean>}  true if answer was correct
 */
function askQuestion(question, index, total, rl) {
  return new Promise((resolve) => {
    const options = shuffle([...question.options]);

    console.log(`\nQuestion ${index}/${total}:`);
    console.log(question.question);
    options.forEach((opt, i) => console.log(`${i + 1}. ${opt}`));

    const prompt = () => {
      rl.question(`Your answer (1-${options.length}): `, (answer) => {
        const idx = parseInt(answer, 10) - 1;
        if (isNaN(idx) || idx < 0 || idx >= options.length) {
          console.log(`Please enter a number between 1 and ${options.length}`);
          return prompt();
        }
        const chosen = options[idx];
        if (chosen === question.correct_answer) {
          console.log('✅ Correct!');
          resolve(true);
        } else {
          console.log('❌ Incorrect!');
          console.log(`The correct answer was: ${question.correct_answer}`);
          resolve(false);
        }
      });
    };

    prompt();
  });
}

/**
 * Run the interactive evaluation session.
 *
 * @param {Array} questions
 * @returns {Promise<number>} number of correct answers
 */
async function askQuestions(questions) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  let correct = 0;

  console.log('\n🧠 Code Understanding Evaluation');
  console.log('='.repeat(50));

  try {
    for (let i = 0; i < questions.length; i++) {
      const isCorrect = await askQuestion(questions[i], i + 1, questions.length, rl);
      if (isCorrect) correct++;
    }
  } finally {
    rl.close();
  }

  return correct;
}

/**
 * Evaluate code changes and return whether the user passed.
 *
 * @param {string} diffContent
 * @param {import('./config').Config} config
 * @returns {Promise<boolean>}
 */
async function evaluateCodeChanges(diffContent, config) {
  console.log('🔍 Analyzing code changes...');

  const questions = await generateQuestionsFromDiff(diffContent, config);

  if (questions.length === 0) {
    console.log('📝 No questions generated from code changes');
    return true;
  }

  const correctAnswers = await askQuestions(questions);
  const total = questions.length;
  const score = (correctAnswers / total) * 100;

  console.log(`\n📊 Results: ${correctAnswers}/${total} correct (${score.toFixed(1)}%)`);

  if (score >= config.passing_grade) {
    console.log('🎉 Congratulations! You passed the evaluation.');
    return true;
  } else {
    console.log(`💡 Please review the code changes. Minimum passing grade is ${config.passing_grade}%`);
    return false;
  }
}

module.exports = { generateQuestionsFromDiff, askQuestions, evaluateCodeChanges };
