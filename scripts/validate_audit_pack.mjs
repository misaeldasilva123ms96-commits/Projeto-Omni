import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

const requiredDocs = [
  'docs/audit/REMEDIATION_SUMMARY.md',
  'docs/audit/SECURITY_FIXES.md',
  'docs/audit/RUNTIME_TRUTH_CONTRACT.md',
  'docs/audit/TEST_EVIDENCE.md',
  'docs/audit/KNOWN_LIMITATIONS.md',
  'docs/release/PUBLISHING_CHECKLIST.md',
  'docs/audit/PHASE_15_AUDIT_PACK_RELEASE_GATE.md',
]

const requiredSections = {
  'docs/audit/REMEDIATION_SUMMARY.md': [
    '## Roadmap Version',
    '## Phases Completed',
    '## Branches And Commits',
    '## Current Release Status',
    '## No Merge Into Main',
  ],
  'docs/audit/SECURITY_FIXES.md': [
    '## Shell Hardening',
    '## Tool Governance',
    '## Secrets And Config',
    '## Security Regression Suite',
  ],
  'docs/audit/RUNTIME_TRUTH_CONTRACT.md': [
    '## Runtime Modes',
    '## Provider Tracking',
    '## Tool Tracking',
    '## Classifier Source And Mode',
    '## Never Full Runtime',
  ],
  'docs/audit/TEST_EVIDENCE.md': [
    '## Command Matrix',
    '## Docker Status',
    '## Non-Blocking Issues',
  ],
  'docs/audit/KNOWN_LIMITATIONS.md': [
    '## Docker Validation',
    '## Public Traffic',
    '## Runtime Scope',
    '## Training',
  ],
  'docs/release/PUBLISHING_CHECKLIST.md': [
    '## Pre-Public-Demo Checklist',
    '## Required Commands',
    '## Environment Checklist',
    '## Rollback Steps',
  ],
  'docs/audit/PHASE_15_AUDIT_PACK_RELEASE_GATE.md': [
    '## Files Changed',
    '## Audit Docs Created',
    '## Commands And Results',
    '## Gate 15',
  ],
}

const secretPatterns = [
  /\bsk-(proj-)?[A-Za-z0-9_-]{12,}/,
  /\bsk-ant-[A-Za-z0-9_-]{12,}/,
  /\bsk-groq-[A-Za-z0-9_-]{12,}/,
  /\bBearer\s+[A-Za-z0-9._-]{16,}/i,
  /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/,
  /\bghp_[A-Za-z0-9_]{12,}/,
  /\bxox[baprs]-[A-Za-z0-9-]{12,}/,
]

function readText(relativePath) {
  return fs.readFileSync(path.join(projectRoot, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function validateDocsExist() {
  for (const relativePath of requiredDocs) {
    assert(fs.existsSync(path.join(projectRoot, relativePath)), `missing required audit doc: ${relativePath}`)
  }
}

function validateSections() {
  for (const [relativePath, sections] of Object.entries(requiredSections)) {
    const text = readText(relativePath)
    for (const section of sections) {
      assert(text.includes(section), `${relativePath} missing section ${section}`)
    }
  }
}

function validateNoObviousSecrets() {
  for (const relativePath of requiredDocs) {
    const text = readText(relativePath)
    for (const pattern of secretPatterns) {
      assert(!pattern.test(text), `${relativePath} contains real-looking secret pattern`)
    }
  }
}

function validateRequiredLimitations() {
  const limitations = readText('docs/audit/KNOWN_LIMITATIONS.md')
  assert(/Docker image build still needs daemon-backed validation/i.test(limitations), 'known limitations must mention Docker build pending')
  assert(/edge\/platform rate limiting/i.test(limitations), 'known limitations must mention edge/platform rate limiting')
  assert(/no production release/i.test(limitations), 'known limitations must mention no production release')
}

function validatePublishingChecklist() {
  const checklist = readText('docs/release/PUBLISHING_CHECKLIST.md')
  assert(/no automatic release/i.test(checklist), 'publishing checklist must prohibit automatic release')
  assert(/no automatic merge/i.test(checklist), 'publishing checklist must prohibit automatic merge')
  assert(/Docker build/i.test(checklist), 'publishing checklist must require Docker build')
  assert(/rollback/i.test(checklist), 'publishing checklist must include rollback')
}

function main() {
  validateDocsExist()
  validateSections()
  validateNoObviousSecrets()
  validateRequiredLimitations()
  validatePublishingChecklist()
  process.stdout.write(JSON.stringify({
    ok: true,
    docs_checked: requiredDocs.length,
    sections_checked: Object.values(requiredSections).reduce((sum, sections) => sum + sections.length, 0),
  }, null, 2))
  process.stdout.write('\n')
}

main()
