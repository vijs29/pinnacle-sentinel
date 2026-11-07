import test from 'node:test'
import assert from 'node:assert/strict'
import { shouldRedirectToLogin, authHeaders } from '../src/lib/authGate.js'

test('on the live site (production build) a visitor with no login is sent to /login', () => {
  assert.equal(shouldRedirectToLogin(null, false), true)
  assert.equal(shouldRedirectToLogin('', false), true)
  assert.equal(shouldRedirectToLogin(undefined, false), true)
})

test('a visitor with a login is never redirected', () => {
  assert.equal(shouldRedirectToLogin('abc.def.ghi', false), false)
  assert.equal(shouldRedirectToLogin('abc.def.ghi', true), false)
})

test('only the local dev server lets a visitor with no login through', () => {
  assert.equal(shouldRedirectToLogin(null, true), false)
  assert.equal(shouldRedirectToLogin('', true), false)
})

test('authHeaders sends the token when there is one and nothing otherwise', () => {
  assert.deepEqual(authHeaders('tok'), { Authorization: 'Bearer tok' })
  assert.deepEqual(authHeaders(null), {})
  assert.deepEqual(authHeaders(''), {})
})
