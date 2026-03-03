'use strict';

const fs = require('fs');
const path = require('path');
const { execSync, spawnSync } = require('child_process');
const { Config } = require('./config');
const { evaluateCodeChanges } = require('./evaluation');

// Known AI tool names/domains found in Co-Authored-By trailers
const AI_COAUTHOR_PATTERNS = [
  'anthropic', 'claude', 'copilot', 'chatgpt',
  'openai', 'gemini', 'cursor', 'codeium', 'tabnine',
];

/**
 * Return true if the staged commit appears to be co-authored by an AI tool.
 *
 * Detection strategy (in order):
 * 1. BEL_AI_JAR_INTERACTIVE_COMMIT env var — set to '1' / 'true' to force-enable.
 * 2. .git/COMMIT_EDITMSG — git writes this before the pre-commit hook runs
 *    when the user passes -m "..." so Co-Authored-By lines are visible here.
 */
function isAiCoauthored() {
  const envOverride = (process.env.BEL_AI_JAR_INTERACTIVE_COMMIT || '').toLowerCase();
  if (['1', 'true', 'yes'].includes(envOverride)) return true;

  const commitMsgPath = path.join('.git', 'COMMIT_EDITMSG');
  if (fs.existsSync(commitMsgPath)) {
    const content = fs.readFileSync(commitMsgPath, 'utf8').toLowerCase();
    for (const line of content.split('\n')) {
      if (line.includes('co-authored-by:')) {
        if (AI_COAUTHOR_PATTERNS.some((p) => line.includes(p))) return true;
      }
    }
  }

  return false;
}

const PRE_COMMIT_HOOK = `#!/bin/bash
# bel-ai-jar pre-commit hook

# Reconnect stdin to the terminal so the user can answer questions
exec < /dev/tty

if command -v node >/dev/null 2>&1; then
    node -e "
const { evaluatePreCommit } = require('$(npm root -g)/bel-ai-jar/src/gitHooks');
evaluatePreCommit().then(ok => process.exit(ok ? 0 : 1)).catch(e => {
  console.error('❌ bel-ai-jar error:', e.message);
  console.error('Run with --no-verify to skip or bel-ai-jar disable to disable hooks');
  process.exit(1);
});
" || exit 1
else
    echo "Error: Node.js not found" >&2
    exit 1
fi
`;

function hooksDir() {
  return path.join('.git', 'hooks');
}

function preCommitPath() {
  return path.join(hooksDir(), 'pre-commit');
}

/**
 * Install the bel-ai-jar pre-commit hook into .git/hooks/.
 */
function setupGitHooks() {
  if (!fs.existsSync(hooksDir())) {
    console.log('⚠️  Git hooks directory not found. Are you in a git repository?');
    return;
  }

  fs.writeFileSync(preCommitPath(), PRE_COMMIT_HOOK, { encoding: 'utf8', mode: 0o755 });
  console.log(`✅ Git hook created at ${preCommitPath()}`);
}

/**
 * Remove the bel-ai-jar pre-commit hook (only if it is ours).
 */
function removeGitHooks() {
  if (!fs.existsSync(hooksDir())) return;

  const hookPath = preCommitPath();
  if (!fs.existsSync(hookPath)) return;

  const content = fs.readFileSync(hookPath, 'utf8');
  if (content.includes('bel-ai-jar')) {
    fs.unlinkSync(hookPath);
    console.log(`✅ Removed git hook at ${hookPath}`);
  }
}

/**
 * Return the list of staged files.
 * @returns {string[]}
 */
function getStagedFiles() {
  try {
    const result = spawnSync('git', ['diff', '--cached', '--name-only'], { encoding: 'utf8' });
    if (result.status !== 0) return [];
    return result.stdout
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

/**
 * Return the unified diff for the staged versions of the given files.
 * @param {string[]} files
 * @returns {string}
 */
function getGitDiff(files) {
  if (!files.length) return '';
  try {
    const result = spawnSync('git', ['diff', '--cached', ...files], { encoding: 'utf8' });
    return result.status === 0 ? result.stdout : '';
  } catch {
    return '';
  }
}

/**
 * Entry point called by the pre-commit hook.
 * Evaluation only runs when the commit is co-authored by an AI tool.
 * Pure human commits are passed through immediately.
 * @returns {Promise<boolean>}
 */
async function evaluatePreCommit() {
  try {
    if (!isAiCoauthored()) {
      console.log('✅ No AI co-author detected — skipping bel-ai-jar evaluation.');
      console.log('   Tip: set BEL_AI_JAR_INTERACTIVE_COMMIT=1 to force evaluation.');
      return true;
    }

    const config = Config.fromFile();
    const staged = getStagedFiles();

    if (!staged.length) {
      console.log('📝 No staged files to evaluate');
      return true;
    }

    const diff = getGitDiff(staged);
    if (!diff) {
      console.log('📝 No changes to evaluate');
      return true;
    }

    return await evaluateCodeChanges(diff, config);
  } catch (err) {
    console.error(`❌ Error during evaluation: ${err.message}`);
    return false;
  }
}

module.exports = { setupGitHooks, removeGitHooks, getStagedFiles, getGitDiff, evaluatePreCommit, isAiCoauthored };
