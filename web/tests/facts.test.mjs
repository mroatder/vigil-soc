import { readFacts, blockState } from '../src/alertFacts.js'
import assert from 'node:assert'
const real = { predecoder: { hostname: 'FW-EDGE-01', program_name: 'waflog' }, data: { waf_action: 'Block', srcip: '203.0.113.50', waf_class: 'Local File Inclusion Attack', dstip: '10.20.30.254:80', waf_msg: '[902350] Path Traversal Attack (/../) #1', url: 'http://1.2.3.4:80%2Findex.php%3Flang%3D..%2F' }, GeoLocation: { country_name: 'Iran' }, rule: { id: '100402', level: 12, description: 'x' }, full_log: 'Nov  2 15:51:03 fw waflog: deviceExternalId=E2 dvchost=FW-EDGE-01 TIME=2026-11-02 15:50:24 HOST=203.0.113.50 DST=10.20.30.254:80 URL=http://x ACTION=Block CLASS=Local File Inclusion Attack MSG=[902350] Path Traversal Attack (/../) #1 COUNT=1', timestamp: '2026-11-02T08:51:03.241+0000' }
let f = readFacts(JSON.stringify({ _source: real }))
assert.equal(f.state, 'blocked'); assert.equal(f.device, 'FW-EDGE-01'); assert.equal(f.time, '2026-11-02 15:50:24'); assert.equal(f.url, 'http://1.2.3.4:80/index.php?lang=../'); assert.equal(f.country, 'Iran'); assert.equal(f.rule, '100402 (level 12)'); assert.equal(f.isWaf, true)
f = readFacts('Nov 2 waflog: dvchost=FW-EDGE-01 TIME=2026-11-02 15:50:24 HOST=1.1.1.1 DST=10.0.0.1:80 ACTION=Allow CLASS=Local File Inclusion Attack MSG=[1] x COUNT=1')
assert.equal(f.state, 'allowed'); assert.equal(f.srcip, '1.1.1.1'); assert.equal(f.attack, 'Local File Inclusion Attack'); assert.equal(f.signature, '[1] x')
f = readFacts(JSON.stringify({ timestamp: '2026-11-02T08:51:03.241+0000', rule: { id: '5', description: 'Logon' } }))
assert.equal(f.state, 'unknown'); assert.equal(f.time, '2026-11-02 15:51:03'); assert.equal(f.action, '')
assert.equal(blockState('Monitor'), 'unknown'); assert.equal(readFacts('not json at all').state, 'unknown'); assert.equal(readFacts('{bad').url, '')
console.log('facts ok')
