'use strict';

const { Config } = require('./config');
const { processDiff } = require('./diffProcessor');
const { setupGitHooks, removeGitHooks, evaluatePreCommit } = require('./gitHooks');
const { evaluateCodeChanges } = require('./evaluation');

module.exports = { Config, processDiff, setupGitHooks, removeGitHooks, evaluatePreCommit, evaluateCodeChanges };
