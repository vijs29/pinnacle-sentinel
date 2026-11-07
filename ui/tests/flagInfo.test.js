import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { FLAGS, FLAG_LABELS, SEVERE_FLAG_TYPES, tierFor, flagByKey, pageFor, BENEISH_THRESHOLD, ALTMAN_THRESHOLD, SLOAN_THRESHOLD, SCORE_BANDS } from '../src/lib/flagInfo.js'

const read = rel => fs.readFileSync(new URL(rel, import.meta.url), 'utf8')

test('every flag has a unique key, a label and a description', () => {
  const keys = FLAGS.map(f => f.key)
  assert.equal(new Set(keys).size, keys.length)
  for (const f of FLAGS) {
    assert.ok(f.label && f.detail, `${f.key} is missing text`)
    assert.ok(['disclosure', 'quantitative'].includes(f.source), `${f.key} has no valid source`)
  }
})

test('severity matches the Screener rules: these eight are ALERT, the rest WATCH', () => {
  const severe = ['beneish_manipulation_risk', 'altman_distress', 'material_weakness', 'going_concern',
    'sec_subpoena', 'sec_investigation', 'whistleblower_complaint', 'financial_restatement']
  assert.deepEqual([...SEVERE_FLAG_TYPES].sort(), severe.sort())
  for (const k of severe) assert.equal(tierFor(k), 'ALERT')
  assert.equal(tierFor('late_filing'), 'WATCH')
  assert.equal(tierFor('anything_unknown'), 'WATCH')
})

test('the four flag pages in the menu each have a slug, a route and the right flag', () => {
  const app = read('../src/App.jsx')
  for (const [slug, key] of [['cfo-resignation', 'cfo_resignation'], ['material-weakness', 'material_weakness'],
    ['auditor-change', 'auditor_change'], ['late-filing', 'late_filing']]) {
    const f = flagByKey(key)
    assert.equal(f.slug, slug)
    assert.equal(pageFor(f), `/flags/${slug}`)
    assert.ok(app.includes(`<Route path="/flags/${slug}" element={<FlagPage flagKey="${key}" />} />`), `no route for ${slug}`)
  }
})

test('every flag that has its own page points at a real route', () => {
  const app = read('../src/App.jsx')
  for (const f of FLAGS.filter(x => pageFor(x))) assert.ok(app.includes(`path="${pageFor(f)}"`), `${f.key} -> ${pageFor(f)} has no route`)
})

test('labels come from the registry (the Screener and the pages cannot disagree)', () => {
  assert.equal(FLAG_LABELS.late_filing, 'Late filing')
  const screener = read('../src/pages/Screener.jsx')
  assert.ok(screener.includes("from '../lib/flagInfo'") && !screener.includes('const FLAG_LABELS'))
})

test('the thresholds match the detector in app/services/quant_flags.py', () => {
  const py = read('../../app/services/quant_flags.py')
  const num = name => Number(py.match(new RegExp(`${name}\\s*=\\s*(-?[0-9.]+)`))[1])
  assert.equal(BENEISH_THRESHOLD, num('BENEISH_THRESHOLD'))
  assert.equal(ALTMAN_THRESHOLD, num('ALTMAN_THRESHOLD'))
  assert.equal(SLOAN_THRESHOLD, num('SLOAN_THRESHOLD'))
})

test('the composite score bands cover 1 to 12 with no gaps', () => {
  const spans = SCORE_BANDS.map(b => b.range.split('-').map(Number))
  assert.equal(spans[0][0], 1)
  assert.equal(spans.at(-1)[1], 12)
  for (let i = 1; i < spans.length; i++) assert.equal(spans[i][0], spans[i - 1][1] + 1)
})
