import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = f => readFileSync(new URL(`../${f}`, import.meta.url), 'utf8')
const legible = read('src/legible.css')
const phone = read('src/phone.css')

test('9px and 10px inline text is raised to 11px at every width', () => {
  assert.match(legible, /\[style\*="font-size: 9px"\],\s*\[style\*="font-size: 10px"\]\s*\{[^}]*font-size: 11px !important;/)
  assert.ok(!legible.includes('@media'), 'the floor applies on desktop too')
  assert.match(legible, /th:not\(\[style\*="font-size"\]\)\s*\{[^}]*font-size: 11px;/)
})

test('everything tapped on a phone is at least 34px each way, links included', () => {
  assert.match(phone, /@media \(max-width: 600px\)/)
  assert.match(phone, /button, select, a\[href\], \[role="button"\],\s*input:not\(\[type="checkbox"\]\):not\(\[type="radio"\]\):not\(\[type="hidden"\]\)\s*\{[^}]*min-height: 34px;[^}]*min-width: 34px;/)
})

test('nothing in phone.css leaks outside the phone media query', () => {
  const src = phone.replace(/\/\*[\s\S]*?\*\//g, '')
  const outside = src.replace(/@media[^{]*\{([^{}]*\{[^{}]*\})*[^{}]*\}/g, '')
  assert.equal(outside.trim(), '')
})

test('both stylesheets load after index.css', () => {
  const m = read('src/main.jsx'), idx = m.indexOf("import './index.css'")
  assert.ok(idx > -1)
  for (const f of ['phone.css', 'legible.css']) assert.ok(m.indexOf(`import './${f}'`) > idx, f)
})

test('colours on dark pages are never dimmer than the crawler allows', () => {
  assert.match(read('src/pages/Universe.jsx'), /muted: '#94a3b8'/)
  assert.ok(!read('src/lib/flagInfo.js').includes('#8b1a1a'), 'dark red on a dark page (contrast 2.1)')
  assert.match(read('src/lib/flagInfo.js'), /label: 'Extreme',\s+color: '#ff5c5c'/)
})
