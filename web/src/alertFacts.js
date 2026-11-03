// Reads facts straight from the alert, so the report never depends on what a
// model chose to write. Everything here is shown as text, never as HTML.

const LOG_FIELD = (log, name) => log.match(new RegExp(`\\b${name}=(.+?)(?=\\s+[A-Za-z_]+=|$)`))?.[1]?.trim() || ''

function parseAlert(text) {
  try {
    const data = JSON.parse(text)
    return data && typeof data === 'object' ? data._source || data : {}
  } catch (_error) {
    return {}
  }
}

function decode(url) {
  try {
    return decodeURIComponent(url)
  } catch (_error) {
    return url
  }
}

function eventTime(log, timestamp) {
  const logged = log.match(/\bTIME=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/)
  if (logged) return logged[1]
  const moment = new Date(String(timestamp || '').replace(/([+-]\d{2})(\d{2})$/, '$1:$2'))
  if (Number.isNaN(moment.getTime())) return ''
  const thai = new Date(moment.getTime() + 7 * 3600000).toISOString()
  return `${thai.slice(0, 10)} ${thai.slice(11, 19)}`
}

export function blockState(action) {
  if (/^(block|blocked|deny|denied|drop|dropped|reject|rejected|reset)$/i.test(action)) return 'blocked'
  if (/^(allow|allowed|accept|accepted|pass|passed|permit|permitted)$/i.test(action)) return 'allowed'
  return 'unknown'
}

export function readFacts(alertText) {
  const source = parseAlert(alertText)
  const data = source.data && typeof source.data === 'object' ? source.data : {}
  const log = String(source.full_log || (Object.keys(source).length ? '' : alertText))
  const action = data.waf_action || data.action || LOG_FIELD(log, 'ACTION')
  const device = LOG_FIELD(log, 'dvchost') || source.predecoder?.hostname || ''
  const isWaf = Boolean(data.waf_action) || /\bwaflog\b/.test(log)
  return {
    action,
    state: blockState(action),
    device,
    isWaf,
    srcip: data.srcip || LOG_FIELD(log, 'HOST') || LOG_FIELD(log, 'SRC'),
    country: source.GeoLocation?.country_name || '',
    dstip: data.dstip || LOG_FIELD(log, 'DST'),
    attack: data.waf_class || LOG_FIELD(log, 'CLASS') || source.rule?.description || '',
    signature: data.waf_msg || LOG_FIELD(log, 'MSG'),
    url: decode(data.url || LOG_FIELD(log, 'URL')),
    rule: source.rule?.id ? `${source.rule.id}${source.rule.level ? ` (level ${source.rule.level})` : ''}` : '',
    time: eventTime(log, source.timestamp)
  }
}
