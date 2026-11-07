import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

// Audit of Sentinel's menus against the app's real routes. Added after the menus were found offering
// ten pages that did not exist (Scoring Model, Flag Validation, the four flag pages, ...).

const read = rel => fs.readFileSync(new URL(rel, import.meta.url), 'utf8')
const routes = new Set([...read('../src/App.jsx').matchAll(/<Route path="([^"*]+)"/g)].map(m => m[1]))

const nav = read('../src/components/NavBar.jsx')
const shared = read('../src/components/PinnacleNavBar.jsx')
const infra = shared.slice(shared.indexOf('export const STANDARD_INFRA_LINKS'), shared.indexOf(']', shared.indexOf('export const STANDARD_INFRA_LINKS')))
const paths = [...nav.matchAll(/path:\s*'([^']+)'/g), ...infra.matchAll(/path:\s*'([^']+)'/g)].map(m => m[1])

test('the audit can see the routes and the menus', () => {
  assert.ok(routes.size >= 15, `only ${routes.size} routes found`)
  assert.ok(paths.length >= 20, `only ${paths.length} menu paths found`)
})

test('every menu entry points at a page that exists', () => {
  const dead = paths.filter(p => !routes.has(p.split('?')[0]))
  assert.deepEqual(dead, [])
})

test('a path that is not a page is caught', () => {
  assert.equal(routes.has('/no-such-page'), false)
})
