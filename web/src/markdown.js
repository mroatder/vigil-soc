// Turns Claude's Markdown answer into plain data. Vue then renders it as text,
// so nothing in an alert or an answer can run as HTML.

export function unwrap(source) {
  const text = source.trim()
  const match = text.match(/^(`{4,})[^\n]*\n([\s\S]*)\n\1\s*$/) ||
    text.match(/^(```)(?:markdown|md)[ \t]*\n([\s\S]*)\n```\s*$/)
  return match ? match[2] : text
}

export function inline(text) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/).filter(Boolean).map(part => {
    if (/^`[^`]+`$/.test(part)) return { type: 'code', value: part.slice(1, -1) }
    if (/^\*\*[^*]+\*\*$/.test(part)) return { type: 'bold', value: part.slice(2, -2) }
    return { type: 'text', value: part }
  })
}

function parseKeyValues(text) {
  const values = {}
  for (const line of text.split('\n')) {
    const index = line.indexOf(':')
    if (index > 0) values[line.slice(0, index).trim().toLowerCase()] = line.slice(index + 1).trim()
  }
  return values
}

function parseFlow(text) {
  return text.split('\n').filter(line => line.trim()).map(line => {
    const [state, title, ...detail] = line.split('|').map(part => part.trim())
    const known = ['confirmed', 'blocked', 'unknown'].includes((state || '').toLowerCase())
    return { state: known ? state.toLowerCase() : 'unknown', title: title || '-', detail: detail.join(' | ') }
  })
}

function parseChecks(text) {
  return text.split('\n').filter(line => line.trim()).map(line => {
    const [priority, task, where, ...concern] = line.split('|').map(part => part.trim())
    return { priority: (priority || '').toLowerCase(), task: task || '-', where: where || '', concern: concern.join(' | ') }
  })
}

// A report block is "key: value" lines. Lines starting with "- " extend the last key as a list.
export function parseReport(text) {
  const fields = {}
  let current = null
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (line.startsWith('- ') && current) {
      fields[current].items.push(line.slice(2))
      continue
    }
    const index = line.indexOf(':')
    if (index > 0 && /^[a-z_]+$/.test(line.slice(0, index).trim())) {
      current = line.slice(0, index).trim()
      fields[current] = { text: line.slice(index + 1).trim(), items: [] }
    } else if (current) {
      fields[current].text = `${fields[current].text} ${line}`.trim()
    }
  }
  return fields
}

const splitRow = line => line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim())
const isSeparator = line => /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(line || '')
const BULLET = /^\s*[-*]\s+/
const NUMBER = /^\s*\d+\.\s+/

export function parseReply(source) {
  const lines = unwrap(source).split(/\r?\n/)
  const result = { summary: null, flow: [], killchain: null, checks: [], reports: {}, intro: [], sections: [] }
  let target = result.intro
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const fence = line.match(/^\s*(`{3,})\s*([\w-]*)\s*$/)
    if (fence) {
      const code = []
      index++
      while (index < lines.length && !lines[index].trim().startsWith(fence[1])) code.push(lines[index++])
      index++
      const text = code.join('\n')
      const lang = fence[2]
      if (lang === 'summary') result.summary = parseKeyValues(text)
      else if (lang === 'flow') result.flow = parseFlow(text)
      else if (lang === 'killchain') result.killchain = parseKeyValues(text)
      else if (lang === 'checks') result.checks = parseChecks(text)
      else if (lang === 'report-th') result.reports.th = parseReport(text)
      else if (lang === 'report-en') result.reports.en = parseReport(text)
      else target.push({ type: 'code', value: text })
      continue
    }
    if (!line.trim()) { index++; continue }

    const heading = line.match(/^(#{1,4})\s+(.*)$/)
    if (heading) {
      if (heading[1].length <= 2) {
        const section = { title: heading[2].replace(/\*\*/g, ''), blocks: [] }
        result.sections.push(section)
        target = section.blocks
      } else {
        target.push({ type: 'heading', parts: inline(heading[2]) })
      }
      index++
      continue
    }
    if (line.includes('|') && isSeparator(lines[index + 1])) {
      const rows = []
      while (index < lines.length && lines[index].includes('|')) rows.push(lines[index++])
      target.push({
        type: 'table',
        head: splitRow(rows[0]).map(inline),
        rows: rows.slice(2).map(row => splitRow(row).map(inline))
      })
      continue
    }
    if (BULLET.test(line) || NUMBER.test(line)) {
      const ordered = NUMBER.test(line)
      const pattern = ordered ? NUMBER : BULLET
      const items = []
      const start = ordered ? parseInt(line, 10) : 1
      while (index < lines.length && pattern.test(lines[index])) {
        items.push(inline(lines[index].replace(pattern, '')))
        index++
      }
      target.push({ type: 'list', ordered, start, items })
      continue
    }
    target.push({ type: 'paragraph', parts: inline(line) })
    index++
  }
  return result
}
