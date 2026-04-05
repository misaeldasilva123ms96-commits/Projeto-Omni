const fs = require('fs');
const path = require('path');

const IGNORED_SEGMENTS = new Set([
  '.git',
  '.logs',
  'node_modules',
  'dist',
  'target',
  '__pycache__',
  '.venv',
  'venv',
]);

const LANGUAGE_BY_EXTENSION = {
  '.js': 'javascript',
  '.cjs': 'javascript',
  '.mjs': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.jsx': 'javascript',
  '.py': 'python',
  '.rs': 'rust',
  '.json': 'json',
  '.toml': 'toml',
  '.md': 'markdown',
  '.yml': 'yaml',
  '.yaml': 'yaml',
};

const ENTRYPOINT_CANDIDATES = [
  'package.json',
  'backend/python/main.py',
  'backend/python/brain/runtime/main.py',
  'backend/rust/src/main.rs',
  'frontend/src/main.tsx',
  'frontend/src/main.jsx',
  'src/main.ts',
  'src/main.js',
  'src/index.ts',
  'src/index.js',
];

function shouldIgnore(relativePath) {
  const normalized = String(relativePath || '').replace(/\\/g, '/');
  return normalized.split('/').some(segment => IGNORED_SEGMENTS.has(segment));
}

function safeRead(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch {
    return '';
  }
}

function detectFrameworks(rootPath, dependencyFiles) {
  const frameworks = new Set();
  const packageJsonPath = dependencyFiles.find(file => file.path === 'package.json');
  if (packageJsonPath) {
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(rootPath, packageJsonPath.path), 'utf8'));
      const deps = {
        ...(pkg.dependencies || {}),
        ...(pkg.devDependencies || {}),
      };
      if (deps.react || deps.vite) frameworks.add('react-vite');
      if (deps['@supabase/supabase-js']) frameworks.add('supabase');
      if (deps.vitest || deps.jest) frameworks.add('javascript-testing');
    } catch {
      // ignore malformed package metadata
    }
  }

  if (dependencyFiles.some(file => file.path.endsWith('Cargo.toml'))) frameworks.add('rust-cargo');
  if (dependencyFiles.some(file => file.path.endsWith('requirements.txt') || file.path.endsWith('pyproject.toml'))) frameworks.add('python-runtime');
  if (fs.existsSync(path.join(rootPath, 'netlify.toml'))) frameworks.add('netlify');
  return Array.from(frameworks);
}

function extractImports(relativePath, content) {
  const imports = new Set();
  const extension = path.extname(relativePath).toLowerCase();
  if (['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'].includes(extension)) {
    const regexes = [
      /import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]/g,
      /require\(\s*['"]([^'"]+)['"]\s*\)/g,
    ];
    for (const regex of regexes) {
      let match;
      while ((match = regex.exec(content))) {
        imports.add(match[1]);
      }
    }
  } else if (extension === '.py') {
    const regexes = [
      /from\s+([A-Za-z0-9_\.]+)\s+import/g,
      /import\s+([A-Za-z0-9_\.]+)/g,
    ];
    for (const regex of regexes) {
      let match;
      while ((match = regex.exec(content))) {
        imports.add(match[1]);
      }
    }
  } else if (extension === '.rs') {
    const regex = /use\s+([A-Za-z0-9_:]+)/g;
    let match;
    while ((match = regex.exec(content))) {
      imports.add(match[1]);
    }
  }
  return Array.from(imports);
}

function analyzeRepository(rootPath, options = {}) {
  const maxFiles = Math.max(50, Number(options.maxFiles || 1500));
  const stack = ['.'];
  const fileIndex = [];
  const dependencyFiles = [];
  const languageCounts = {};
  const dependencyGraph = [];

  while (stack.length > 0 && fileIndex.length < maxFiles) {
    const currentRelative = stack.pop();
    const absolute = path.join(rootPath, currentRelative);
    let entries = [];
    try {
      entries = fs.readdirSync(absolute, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of entries) {
      const entryRelative = path.join(currentRelative, entry.name).replace(/\\/g, '/').replace(/^\.\//, '');
      if (shouldIgnore(entryRelative)) continue;
      const entryAbsolute = path.join(rootPath, entryRelative);
      if (entry.isDirectory()) {
        stack.push(entryRelative);
        continue;
      }

      const extension = path.extname(entry.name).toLowerCase();
      const language = LANGUAGE_BY_EXTENSION[extension] || 'other';
      languageCounts[language] = (languageCounts[language] || 0) + 1;
      const stat = fs.statSync(entryAbsolute);
      const content = ['.js', '.jsx', '.ts', '.tsx', '.py', '.rs', '.json', '.toml'].includes(extension)
        ? safeRead(entryAbsolute)
        : '';
      const imports = content ? extractImports(entryRelative, content) : [];

      fileIndex.push({
        path: entryRelative,
        language,
        extension,
        size: stat.size,
        imports,
      });
      if (['package.json', 'package-lock.json', 'requirements.txt', 'pyproject.toml', 'Cargo.toml'].includes(entry.name)) {
        dependencyFiles.push({
          path: entryRelative,
          kind: entry.name,
        });
      }
      if (imports.length > 0) {
        dependencyGraph.push({
          file: entryRelative,
          imports,
        });
      }
    }
  }

  const frameworks = detectFrameworks(rootPath, dependencyFiles);
  const entryPoints = ENTRYPOINT_CANDIDATES.filter(candidate => fs.existsSync(path.join(rootPath, candidate)));
  const dominantLanguage = Object.entries(languageCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'unknown';

  return {
    version: 1,
    root: rootPath,
    repository_map: {
      file_count: fileIndex.length,
      dependency_files: dependencyFiles.map(file => file.path),
      entry_points: entryPoints,
      frameworks,
      dominant_language: dominantLanguage,
    },
    file_index: fileIndex.slice(0, maxFiles),
    dependency_graph: dependencyGraph.slice(0, maxFiles),
    language_profile: {
      dominant_language: dominantLanguage,
      counts: languageCounts,
    },
    detected_frameworks: frameworks,
    generated_at: new Date().toISOString(),
  };
}

module.exports = {
  analyzeRepository,
};
