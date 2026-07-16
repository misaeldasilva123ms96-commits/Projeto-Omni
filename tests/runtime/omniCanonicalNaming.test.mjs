import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const root = process.cwd();
const require = createRequire(import.meta.url);
const { loadRuntimeConfig } = require(path.join(root, 'configs', 'runtimeConfig.js'));

const previousCanonical = process.env.OMNI_MAX_STEPS;
const previousLegacy = process.env.OMINI_MAX_STEPS;
try {
  process.env.OMNI_MAX_STEPS = '9';
  process.env.OMINI_MAX_STEPS = '3';
  assert.equal(loadRuntimeConfig().maxSteps, 9, 'canonical configuration must be used');

  delete process.env.OMNI_MAX_STEPS;
  assert.notEqual(loadRuntimeConfig().maxSteps, 3, 'obsolete-only configuration must be ignored');
} finally {
  if (previousCanonical === undefined) delete process.env.OMNI_MAX_STEPS;
  else process.env.OMNI_MAX_STEPS = previousCanonical;
  if (previousLegacy === undefined) delete process.env.OMINI_MAX_STEPS;
  else process.env.OMINI_MAX_STEPS = previousLegacy;
}

const rootPackage = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const webPackage = JSON.parse(fs.readFileSync(path.join(root, 'frontend', 'package.json'), 'utf8'));
const mobilePackage = JSON.parse(fs.readFileSync(path.join(root, 'frontend', 'mobile', 'package.json'), 'utf8'));
assert.equal(rootPackage.name, 'omni-runner');
assert.equal(webPackage.name, 'omni-web');
assert.equal(mobilePackage.name, 'omni-mobile');

const androidGradle = fs.readFileSync(path.join(root, 'frontend', 'mobile', 'android', 'app', 'build.gradle'), 'utf8');
const capacitorConfig = fs.readFileSync(path.join(root, 'frontend', 'mobile', 'capacitor.config.ts'), 'utf8');
assert.match(androidGradle, /namespace "com\.omni\.app"/);
assert.match(androidGradle, /applicationId "com\.omni\.app"/);
assert.match(capacitorConfig, /appId: 'com\.omni\.app'/);
assert.ok(fs.existsSync(path.join(root, 'frontend', 'mobile', 'android', 'app', 'src', 'main', 'java', 'com', 'omni', 'app', 'MainActivity.java')));

console.log('canonical-only Omni naming tests: ok');
