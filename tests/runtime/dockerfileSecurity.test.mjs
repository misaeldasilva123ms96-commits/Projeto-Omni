import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const dockerfile = fs.readFileSync(path.join(projectRoot, 'Dockerfile'), 'utf8');

assert.match(dockerfile, /groupadd\s+--system\s+omni/, 'Dockerfile must create omni system group');
assert.match(
  dockerfile,
  /useradd\s+--system\s+--gid\s+omni\s+--home-dir\s+\/app\s+--shell\s+\/usr\/sbin\/nologin\s+omni/,
  'Dockerfile must create non-login omni system user',
);
assert.match(dockerfile, /chown\s+-R\s+omni:omni\s+\/app\s+\/opt\/venv/, 'Dockerfile must assign app and venv ownership');
assert.match(dockerfile, /chmod\s+0755\s+\/usr\/local\/bin\/omini-api/, 'omini-api binary must stay executable');
const userIndex = dockerfile.indexOf('\nUSER omni');
const exposeIndex = dockerfile.indexOf('\nEXPOSE 3001');
const cmdIndex = dockerfile.indexOf('\nCMD ["omini-api"]');
assert.ok(userIndex > -1, 'Dockerfile must declare USER omni');
assert.ok(exposeIndex > userIndex, 'runtime must switch to non-root before EXPOSE');
assert.ok(cmdIndex > exposeIndex, 'CMD must remain after EXPOSE');
assert.equal(/\nUSER\s+root\b/.test(dockerfile), false, 'Dockerfile must not switch back to root');

console.log('dockerfile security validation: ok');
