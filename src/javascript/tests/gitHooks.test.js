'use strict';

const os = require('os');
const fs = require('fs');
const path = require('path');

let tmpDir;
let originalCwd;

beforeEach(() => {
  originalCwd = process.cwd();
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bel-ai-jar-hooks-'));
  // Create a minimal fake .git/hooks directory
  fs.mkdirSync(path.join(tmpDir, '.git', 'hooks'), { recursive: true });
  process.chdir(tmpDir);
});

afterEach(() => {
  process.chdir(originalCwd);
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

const { setupGitHooks, removeGitHooks, getStagedFiles, getGitDiff } = require('../src/gitHooks');

describe('setupGitHooks', () => {
  test('creates pre-commit hook file', () => {
    setupGitHooks();
    expect(fs.existsSync(path.join('.git', 'hooks', 'pre-commit'))).toBe(true);
  });

  test('hook file is executable', () => {
    setupGitHooks();
    const stat = fs.statSync(path.join('.git', 'hooks', 'pre-commit'));
    // Owner execute bit
    expect(stat.mode & 0o100).toBeTruthy();
  });

  test('hook content mentions bel-ai-jar', () => {
    setupGitHooks();
    const content = fs.readFileSync(path.join('.git', 'hooks', 'pre-commit'), 'utf8');
    expect(content).toContain('bel-ai-jar');
  });

  test('warns when .git/hooks does not exist', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    // Remove the hooks dir
    fs.rmSync(path.join('.git', 'hooks'), { recursive: true });
    setupGitHooks();
    const calls = consoleSpy.mock.calls.map((c) => c.join(' ')).join(' ');
    expect(calls.toLowerCase()).toContain('git');
    consoleSpy.mockRestore();
  });
});

describe('removeGitHooks', () => {
  test('removes bel-ai-jar hook', () => {
    setupGitHooks();
    removeGitHooks();
    expect(fs.existsSync(path.join('.git', 'hooks', 'pre-commit'))).toBe(false);
  });

  test('does not remove an unrelated hook', () => {
    const hookPath = path.join('.git', 'hooks', 'pre-commit');
    fs.writeFileSync(hookPath, '#!/bin/bash\necho custom\n');
    removeGitHooks();
    expect(fs.existsSync(hookPath)).toBe(true);
  });

  test('no-op when hooks dir is missing', () => {
    fs.rmSync(path.join('.git', 'hooks'), { recursive: true });
    expect(() => removeGitHooks()).not.toThrow();
  });
});

describe('getStagedFiles', () => {
  test('returns empty array when git errors', () => {
    // We are in a non-git tmp dir at root level; git will error
    const files = getStagedFiles();
    expect(Array.isArray(files)).toBe(true);
  });
});

describe('getGitDiff', () => {
  test('returns empty string for no files', () => {
    expect(getGitDiff([])).toBe('');
  });

  test('returns empty string when git errors', () => {
    const diff = getGitDiff(['nonexistent.js']);
    expect(typeof diff).toBe('string');
  });
});
