import assert from 'node:assert'
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { MESSAGES } from '../src/messages.js'

const { th, en } = MESSAGES
const names = text => [...text.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort()
assert.deepEqual(Object.keys(en).sort(), Object.keys(th).sort())
for (const key of Object.keys(th)) {
  assert.deepEqual(names(en[key]), names(th[key]), `placeholders differ for ${key}`)
  assert.ok(th[key] && en[key], `empty text for ${key}`)
  assert.doesNotMatch(en[key], /[฀-๿]/, `Thai text in English for ${key}`)
}

// Screens must use t(). Thai may appear only in the report text, language names, and icon matching.
const src = join(dirname(fileURLToPath(import.meta.url)), '../src')
const allowed = /\['th', 'ไทย'\]|\.test\(text\)/
const screens = ['App.vue', ...readdirSync(join(src, 'components')).filter(name => name !== 'ReportDocument.vue').map(name => `components/${name}`)]
for (const screen of screens) {
  readFileSync(join(src, screen), 'utf8').split('\n').forEach((line, index) => {
    assert.ok(!/[฀-๿]/.test(line) || allowed.test(line), `${screen}:${index + 1} has text outside messages.js`)
  })
}

// Every key used on a screen must exist.
for (const screen of screens) {
  const text = readFileSync(join(src, screen), 'utf8')
  for (const [, key] of text.matchAll(/\bt\('(\w+)'/g)) assert.ok(key in th, `${screen} uses unknown key ${key}`)
}
console.log('i18n ok')
