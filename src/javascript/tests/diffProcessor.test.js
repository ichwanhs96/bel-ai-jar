'use strict';

const { processDiff, matchesExcluded, parseDiffIntoFiles, stripToAdditions } = require('../src/diffProcessor');
const { Config } = require('../src/config');

const SAMPLE_DIFF = `diff --git a/app.js b/app.js
index 000000..111111 100644
--- a/app.js
+++ b/app.js
@@ -1,5 +1,7 @@
 const os = require('os');
-const old = 1;
+const newVal = 1;
+
+function greet(name) {
+  return \`Hello \${name}\`;
+}
diff --git a/package-lock.json b/package-lock.json
index 000000..222222 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,3 +1,3 @@
-{"version": "1"}
+{"version": "2"}
`;

describe('matchesExcluded', () => {
  test('matches exact filename', () => {
    expect(matchesExcluded('package-lock.json', ['package-lock.json'])).toBe(true);
  });

  test('matches glob extension', () => {
    expect(matchesExcluded('path/to/file.lock', ['*.lock'])).toBe(true);
  });

  test('matches file inside directory pattern', () => {
    expect(matchesExcluded('dist/bundle.js', ['dist/*'])).toBe(true);
  });

  test('matches basename in nested path', () => {
    expect(matchesExcluded('some/nested/yarn.lock', ['yarn.lock'])).toBe(true);
  });

  test('returns false for non-matching file', () => {
    expect(matchesExcluded('src/app.js', ['*.lock', 'dist/*'])).toBe(false);
  });

  test('matches .md files', () => {
    expect(matchesExcluded('README.md', ['*.md'])).toBe(true);
    expect(matchesExcluded('docs/guide.md', ['*.md'])).toBe(true);
  });
});

describe('parseDiffIntoFiles', () => {
  test('splits into correct number of file sections', () => {
    const sections = parseDiffIntoFiles(SAMPLE_DIFF);
    expect(sections).toHaveLength(2);
    expect(sections[0].path).toBe('app.js');
    expect(sections[1].path).toBe('package-lock.json');
  });

  test('returns empty array for empty diff', () => {
    expect(parseDiffIntoFiles('')).toEqual([]);
  });

  test('each section starts with diff header', () => {
    for (const section of parseDiffIntoFiles(SAMPLE_DIFF)) {
      expect(section.lines[0]).toMatch(/^diff --git/);
    }
  });
});

describe('stripToAdditions', () => {
  test('keeps addition lines', () => {
    const lines = ['+newVal = 1', '+function greet() {}'];
    expect(stripToAdditions(lines)).toEqual(lines);
  });

  test('drops context lines', () => {
    const lines = [" const os = require('os');", '+newVal = 1', ' other context'];
    const result = stripToAdditions(lines);
    expect(result).not.toContain(" const os = require('os');");
    expect(result).toContain('+newVal = 1');
  });

  test('drops deletion lines', () => {
    const lines = ['-const old = 1;', '+const newVal = 1;'];
    const result = stripToAdditions(lines);
    expect(result).not.toContain('-const old = 1;');
    expect(result).toContain('+const newVal = 1;');
  });

  test('keeps file and hunk headers', () => {
    const lines = ['diff --git a/f b/f', '--- a/f', '+++ b/f', '@@ -1,2 +1,3 @@'];
    expect(stripToAdditions(lines)).toEqual(lines);
  });
});

describe('processDiff', () => {
  test('filters out excluded files', () => {
    const config = new Config();
    const { processedDiff, stats } = processDiff(SAMPLE_DIFF, config);
    expect(processedDiff).not.toContain('package-lock.json');
    expect(stats.filteredFiles).toBe(1);
  });

  test('keeps non-excluded files', () => {
    const config = new Config();
    const { processedDiff } = processDiff(SAMPLE_DIFF, config);
    expect(processedDiff).toContain('app.js');
  });

  test('strips deletions and context', () => {
    const config = new Config();
    const { processedDiff } = processDiff(SAMPLE_DIFF, config);
    expect(processedDiff).not.toContain('-const old');
    expect(processedDiff).not.toContain(" const os");
  });

  test('keeps additions', () => {
    const config = new Config();
    const { processedDiff } = processDiff(SAMPLE_DIFF, config);
    expect(processedDiff).toContain('+const newVal');
    expect(processedDiff).toContain('+function greet');
  });

  test('returns empty for empty diff', () => {
    const { processedDiff, stats } = processDiff('', new Config());
    expect(processedDiff).toBe('');
    expect(stats.finalLines).toBe(0);
  });

  test('returns empty when all files are excluded', () => {
    const config = new Config({ excluded_files: ['*.js', '*.json'] });
    const { processedDiff, stats } = processDiff(SAMPLE_DIFF, config);
    expect(processedDiff).toBe('');
    expect(stats.filteredFiles).toBe(2);
  });

  test('truncates to max_diff_lines', () => {
    const lines = Array.from({ length: 200 }, (_, i) => `+line_${i}`).join('\n');
    const bigDiff = `diff --git a/big.js b/big.js\n--- a/big.js\n+++ b/big.js\n@@ -1 +1 @@\n${lines}`;
    const config = new Config({ max_diff_lines: 50, excluded_files: [] });
    const { stats } = processDiff(bigDiff, config);
    expect(stats.finalLines).toBeLessThanOrEqual(50);
  });

  test('stats reflect original vs final lines', () => {
    const config = new Config();
    const { stats } = processDiff(SAMPLE_DIFF, config);
    expect(stats.originalLines).toBeGreaterThan(stats.finalLines);
  });

  test('no excluded config keeps all files', () => {
    const config = new Config({ excluded_files: [] });
    const { stats } = processDiff(SAMPLE_DIFF, config);
    expect(stats.filteredFiles).toBe(0);
  });
});
