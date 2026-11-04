import { ref, watch } from 'vue'
import { MESSAGES } from './messages.js'

const STORE_KEY = 'vigil-lang'

function savedLanguage() {
  try {
    return localStorage.getItem(STORE_KEY)
  } catch (_error) {
    return null
  }
}

function firstLanguage() {
  const saved = savedLanguage()
  if (saved === 'th' || saved === 'en') return saved
  return (navigator.language || '').toLowerCase().startsWith('th') ? 'th' : 'en'
}

export const lang = ref(firstLanguage())
export const locale = () => (lang.value === 'th' ? 'th-TH-u-ca-gregory' : 'en-GB')

export function t(key, values = {}) {
  const text = MESSAGES[lang.value][key] ?? key
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in values ? values[name] : match))
}

export function setLang(next) {
  if (next !== 'th' && next !== 'en') return
  lang.value = next
  try {
    localStorage.setItem(STORE_KEY, next)
  } catch (_error) {
    // The choice still applies until this page closes.
  }
}

watch(lang, value => { document.documentElement.lang = value }, { immediate: true })
