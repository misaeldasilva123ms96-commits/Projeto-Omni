'use strict';

const { main } = require('../backend/python/js-runner/queryEngineRunner.js');

if (require.main === module) {
  main().catch(() => {
    process.stdout.write('');
  });
}

module.exports = {
  main,
};
