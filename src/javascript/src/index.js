'use strict';

const { Config } = require('./config');
const { setupGitHooks, removeGitHooks, evaluatePreCommit } = require('./gitHooks');
const { evaluateCodeChanges } = require('./evaluation');

module.exports = { Config, setupGitHooks, removeGitHooks, evaluatePreCommit, evaluateCodeChanges };
