'use strict';

const path = require('path');

/**
 * Convert a glob pattern to a RegExp.
 * Supports * (any chars except /) and ** (any chars including /).
 */
function globToRegex(pattern) {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  const regexStr = escaped
    .replace(/\*\*/g, '\x00')   // placeholder for **
    .replace(/\*/g, '[^/]*')    // * matches within a segment
    .replace(/\x00/g, '.*');    // ** matches across segments
  return new RegExp('^' + regexStr + '$');
}

/**
 * Return true if filepath matches any excluded glob pattern.
 */
function matchesExcluded(filepath, patterns) {
  const basename = path.basename(filepath);
  for (const pattern of patterns) {
    if (globToRegex(pattern).test(filepath)) return true;
    // Patterns without a slash are also matched against the basename
    if (!pattern.includes('/') && globToRegex(pattern).test(basename)) return true;
  }
  return false;
}

/**
 * Split a unified diff string into per-file sections.
 * @returns {{ path: string, lines: string[] }[]}
 */
function parseDiffIntoFiles(diff) {
  const sections = [];
  let currentPath = null;
  let currentLines = [];

  for (const line of diff.split('\n')) {
    if (line.startsWith('diff --git ')) {
      if (currentPath !== null) {
        sections.push({ path: currentPath, lines: currentLines });
      }
      const match = line.match(/^diff --git a\/(.*) b\/(.*)$/);
      currentPath = match ? match[2] : '';
      currentLines = [line];
    } else if (currentPath !== null) {
      currentLines.push(line);
    }
  }
  if (currentPath !== null) {
    sections.push({ path: currentPath, lines: currentLines });
  }
  return sections;
}

/**
 * Keep file/hunk headers and added lines; drop context and deletions.
 */
function stripToAdditions(lines) {
  return lines.filter((line) => {
    if (
      line.startsWith('diff ') ||
      line.startsWith('index ') ||
      line.startsWith('--- ') ||
      line.startsWith('+++ ') ||
      line.startsWith('@@ ')
    ) return true;
    if (line.startsWith('+')) return true;  // addition (not +++ — caught above)
    return false;  // context, deletion, meta
  });
}

/**
 * Filter and truncate a git diff to reduce LLM token consumption.
 *
 * Steps applied in order:
 *   1. Filter out files matching excluded_files patterns.
 *   2. Strip context lines and deletion lines (keep additions + headers).
 *   3. Truncate evenly across remaining files if still over max_diff_lines.
 *
 * @param {string} diff
 * @param {import('./config').Config} config
 * @returns {{ processedDiff: string, stats: { originalLines: number, filteredFiles: number, finalLines: number } }}
 */
function processDiff(diff, config) {
  const empty = { processedDiff: '', stats: { originalLines: 0, filteredFiles: 0, finalLines: 0 } };
  if (!diff) return empty;

  const sections = parseDiffIntoFiles(diff);
  const originalLines = sections.reduce((n, s) => n + s.lines.length, 0);

  // Step 1: filter excluded files
  const excludedPatterns = config.excluded_files || [];
  const included = sections.filter((s) => !matchesExcluded(s.path, excludedPatterns));
  const filteredFiles = sections.length - included.length;

  if (!included.length) {
    return { processedDiff: '', stats: { originalLines, filteredFiles, finalLines: 0 } };
  }

  // Step 2: strip to additions only
  for (const section of included) {
    section.lines = stripToAdditions(section.lines);
  }

  // Step 3: truncate to max_diff_lines, distributed evenly across files
  const maxLines = config.max_diff_lines ?? 1000;
  const total = included.reduce((n, s) => n + s.lines.length, 0);

  if (total > maxLines) {
    const linesPerFile = Math.max(10, Math.floor(maxLines / included.length));
    for (const section of included) {
      if (section.lines.length > linesPerFile) {
        section.lines = section.lines.slice(0, linesPerFile);
      }
    }
  }

  const finalLines = included.reduce((n, s) => n + s.lines.length, 0);
  const processedDiff = included.map((s) => s.lines.join('\n')).join('\n');

  return { processedDiff, stats: { originalLines, filteredFiles, finalLines } };
}

module.exports = { processDiff, matchesExcluded, parseDiffIntoFiles, stripToAdditions };
