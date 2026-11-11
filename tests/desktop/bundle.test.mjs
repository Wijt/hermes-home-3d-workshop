// The shipped desktop/plugin.js against the Desktop plugin rules (what `hermes plugins validate` and a
// maintainer look for): only the three allowed imports, no eval / new Function / dynamic import, no script
// injection, no reaching into the app's markup or storage, no dev-only code.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const file = new URL('../../desktop/plugin.js', import.meta.url)
const src = readFileSync(file, 'utf8')

test('the bundle parses as an ES module', () => {
  execFileSync(process.execPath, ['--input-type=module', '--check'], { input: src })
})

test('only @hermes/plugin-sdk, react and react/jsx-runtime are imported', () => {
  const specs = new Set([...src.matchAll(/\bfrom\s*"([^"]+)"/g)].map(m => m[1]))
  assert.deepEqual([...specs].sort(), ['@hermes/plugin-sdk', 'react', 'react/jsx-runtime'])
  assert.doesNotMatch(src, /\bimport\s*\(/, 'dynamic import')
  assert.doesNotMatch(src, /\brequire\s*\(/, 'require')
})

test('no code generation, script injection or app reach-in', () => {
  const banned = [
    [/\beval\s*\(/, 'eval'],
    [/new\s+Function\b/, 'new Function'],
    [/createElement\(\s*["']script["']/, 'script injection'],
    [/\.innerHTML\s*=/, 'innerHTML'],
    [/querySelector(All)?\s*\(/, 'querySelector'],
    [/document\.(body|head)\b/, 'document.body/head'],
    [/MutationObserver/, 'MutationObserver'],
    [/data-slot|data-testid|data-composer/, 'app selectors'],
    [/localStorage|sessionStorage|indexedDB/, 'storage'],
    [/window\.hermesDesktop/, 'native bridge'],
    [/(Array|Object|String|Function|Element|Node|EventTarget|Promise)\.prototype\.\w+\s*=/, 'built-in prototype patch'],
    [/sdk-shim|shimControl|harness/, 'dev harness code']
  ]
  for (const [re, what] of banned) assert.doesNotMatch(src, re, what)
})

test('the plugin id matches the package', () => {
  assert.match(src, /"home-3d-workshop"/)
  assert.match(src, /"\/workshop"/)
})
