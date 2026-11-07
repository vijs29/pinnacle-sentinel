import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const src = f => readFileSync(new URL(`../src/pages/${f}`, import.meta.url), 'utf8')

test('Platform Methodology fetches through BASE_URL, not a bare relative path', () => {
  const s = src('PlatformMethodology.jsx')
  assert.match(s, /fetch\(`\$\{BASE_URL\}\/api\/platform\/methodology`\)/)
  assert.doesNotMatch(s, /fetch\('\/api\/platform\/methodology'\)/)
})

test('Universe uses the local backend in dev and the live hub in production', () => {
  assert.match(src('Universe.jsx'), /import\.meta\.env\.DEV \? BASE_URL : 'https:\/\/platform\.pinnacletranscore\.com'/)
})

test('Platform Intelligence never bypasses the login gate, even in dev', () => {
  const s = src('PlatformIntelligence.jsx')
  assert.match(s, /shouldRedirectToLogin\(token, false\)/)
  assert.doesNotMatch(s, /shouldRedirectToLogin\(token, import\.meta\.env\.DEV\)/)
})

test('Landing hero does not accuse companies of hiding anything', () => {
  const s = src('Landing.jsx')
  assert.doesNotMatch(s, /hiding something/i)
  assert.match(s, /intelligence available in SEC filings/)
  assert.match(s, /not a conclusion about intent/)
})
