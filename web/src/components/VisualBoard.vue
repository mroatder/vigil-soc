<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  report: { type: Object, required: true },
  checksDone: { type: Array, default: () => [] }
})
const emit = defineEmits(['checks'])

const SEVERITY = {
  info: { value: 20, color: 'var(--info)' },
  low: { value: 40, color: 'var(--ok)' },
  medium: { value: 60, color: 'var(--warn)' },
  high: { value: 80, color: 'var(--bad)' },
  critical: { value: 100, color: 'var(--bad)' }
}
const severityName = computed(() => props.report.summary?.severity || 'Unknown')
const severity = computed(() => SEVERITY[severityName.value.toLowerCase()] || { value: 0, color: 'var(--soft)' })

const CONFIDENCE = { high: 3, medium: 2, low: 1 }
const confidence = value => CONFIDENCE[(value || '').toLowerCase()] || 0
const confidenceRows = computed(() => [
  { label: 'เหตุการณ์', value: props.report.summary?.event_confidence || 'Unknown' },
  { label: 'ผลกระทบ', value: props.report.summary?.impact_confidence || 'Unknown' }
])

const STATES = {
  confirmed: { label: 'ยืนยันแล้ว', color: 'var(--ok)', soft: 'var(--ok-soft)' },
  blocked: { label: 'ถูกบล็อก', color: 'var(--bad)', soft: 'var(--bad-soft)' },
  unknown: { label: 'ยังไม่ยืนยัน', color: 'var(--warn)', soft: 'var(--warn-soft)' }
}
const ICONS = {
  internet: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M3.6 9h16.8M3.6 15h16.8M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18'],
  shield: ['M12 3 5 6v5c0 4.6 2.9 8.4 7 10 4.1-1.6 7-5.4 7-10V6l-7-3Z'],
  server: ['M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01'],
  file: ['M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z', 'M14 3v5h5'],
  step: ['M12 8v8M8 12h8']
}
const iconFor = item => {
  const text = `${item.title} ${item.detail}`.toLowerCase()
  if (/waf|firewall|ไฟร์วอลล์|บล็อก/.test(text)) return ICONS.shield
  if (/\.git|file|ไฟล์|โฟลเดอร์/.test(text)) return ICONS.file
  if (/server|เครื่อง|host/.test(text)) return ICONS.server
  if (/ผู้ส่ง|internet|อินเทอร์เน็ต|sender|source/.test(text)) return ICONS.internet
  return ICONS.step
}
const flow = computed(() => props.report.flow)
const stopIndex = computed(() => {
  const index = flow.value.findIndex(item => item.state !== 'confirmed')
  return index === -1 ? flow.value.length : index
})

const evidence = computed(() => {
  const counts = { confirmed: 0, blocked: 0, unknown: 0 }
  flow.value.forEach(item => { counts[item.state]++ })
  return counts
})
const evidenceTotal = computed(() => flow.value.length)
const rings = computed(() => {
  let offset = 0
  return Object.entries(evidence.value).filter(([, count]) => count).map(([state, count]) => {
    const share = count / evidenceTotal.value * 100
    const ring = { state, share, offset, color: STATES[state].color }
    offset += share
    return ring
  })
})

const CHAIN = [
  ['recon', 'สำรวจ', 'Recon'],
  ['initial_access', 'เข้าถึง', 'Initial Access'],
  ['execution', 'รันคำสั่ง', 'Execution'],
  ['persistence', 'ฝังตัว', 'Persistence'],
  ['lateral_movement', 'ขยายผล', 'Lateral Movement'],
  ['impact', 'ผลกระทบ', 'Impact']
]
const CHAIN_STATES = {
  observed: { label: 'พบ', color: 'var(--warn)', soft: 'var(--warn-soft)' },
  blocked: { label: 'ถูกบล็อก', color: 'var(--bad)', soft: 'var(--bad-soft)' },
  unknown: { label: 'ยังไม่รู้', color: 'var(--soft)', soft: 'var(--raised)' },
  none: { label: 'ไม่พบ', color: 'var(--soft)', soft: 'transparent' }
}
const chain = computed(() => {
  const values = props.report.killchain
  if (!values) return []
  return CHAIN.map(([key, thai, english]) => {
    const state = CHAIN_STATES[(values[key] || 'none').toLowerCase()] ? (values[key] || 'none').toLowerCase() : 'unknown'
    return { key, thai, english, state, ...CHAIN_STATES[state] }
  })
})

const done = ref(Object.fromEntries(props.checksDone.map(index => [index, true])))
const toggleCheck = (index, value) => {
  done.value[index] = value
  emit('checks', Object.keys(done.value).filter(key => done.value[key]).map(Number))
}
const checks = computed(() => props.report.checks)
const doneCount = computed(() => checks.value.filter((_item, index) => done.value[index]).length)
const PRIORITY = { high: 'var(--bad)', medium: 'var(--warn)', low: 'var(--soft)' }
</script>

<template>
  <div class="grid gap-3 min-w-0">
    <div class="grid gap-3 sm:grid-cols-3">
      <section class="bg-surface rounded-2xl p-4 grid justify-items-center content-start" aria-label="ระดับความสำคัญ">
        <h3 class="justify-self-start text-[14px] text-soft font-normal">ความเสี่ยง</h3>
        <svg class="w-full max-w-[170px] mt-2" viewBox="0 0 120 68" role="img" :aria-label="`ระดับ ${severityName}`">
          <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="var(--raised)" stroke-width="11" stroke-linecap="round" />
          <path v-if="severity.value" d="M10 60 A50 50 0 0 1 110 60" fill="none" :stroke="severity.color" stroke-width="11" stroke-linecap="round" pathLength="100" :stroke-dasharray="`${severity.value} 100`" />
        </svg>
        <strong class="text-[24px] font-medium -mt-7" :style="{ color: severity.color }">{{ severityName }}</strong>
      </section>

      <section class="bg-surface rounded-2xl p-4" aria-label="สถานะหลักฐาน">
        <h3 class="text-[14px] text-soft font-normal">หลักฐาน</h3>
        <div class="flex items-center gap-4 mt-2">
          <svg class="w-[84px] h-[84px] shrink-0 -rotate-90" viewBox="0 0 42 42" role="img" :aria-label="`ยืนยันแล้ว ${evidence.confirmed} ถูกบล็อก ${evidence.blocked} ยังไม่ยืนยัน ${evidence.unknown}`">
            <circle cx="21" cy="21" r="15.9" fill="none" stroke="var(--raised)" stroke-width="6" />
            <circle v-for="ring in rings" :key="ring.state" cx="21" cy="21" r="15.9" fill="none" :stroke="ring.color" stroke-width="6" pathLength="100"
              :stroke-dasharray="`${ring.share} ${100 - ring.share}`" :stroke-dashoffset="-ring.offset" />
          </svg>
          <ul class="grid gap-1 text-[14px] min-w-0">
            <li v-for="(count, state) in evidence" :key="state" class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: STATES[state].color }"></span>
              <span class="truncate">{{ STATES[state].label }}</span><strong class="font-medium ml-auto pl-1">{{ count }}</strong>
            </li>
          </ul>
        </div>
      </section>

      <section class="bg-surface rounded-2xl p-4" aria-label="ความมั่นใจ">
        <h3 class="text-[14px] text-soft font-normal">ความมั่นใจ</h3>
        <div v-for="row in confidenceRows" :key="row.label" class="mt-3">
          <div class="flex justify-between gap-3 text-[14px]"><span>{{ row.label }}</span><strong class="font-medium">{{ row.value }}</strong></div>
          <div class="grid grid-cols-3 gap-1 mt-1.5" aria-hidden="true">
            <span v-for="level in 3" :key="level" class="h-1.5 rounded-full" :style="{ background: level <= confidence(row.value) ? 'var(--info)' : 'var(--raised)' }"></span>
          </div>
        </div>
      </section>
    </div>

    <section v-if="flow.length" class="bg-surface rounded-2xl p-4 sm:p-5 min-w-0" aria-label="เส้นทางการโจมตี">
      <h3 class="text-[14px] text-soft font-normal mb-4">เส้นทางการโจมตี</h3>
      <ol class="grid gap-4 sm:gap-1 sm:[grid-template-columns:repeat(var(--steps),minmax(0,1fr))]" :style="{ '--steps': flow.length }">
        <li v-for="(item, index) in flow" :key="index" class="relative flex sm:block items-start gap-3 sm:text-center min-w-0">
          <span v-if="index < flow.length - 1" class="hidden sm:block absolute top-[21px] left-1/2 w-full border-t-2"
            :style="{ borderColor: index < stopIndex ? 'var(--ok)' : 'var(--line)', borderTopStyle: index < stopIndex ? 'solid' : 'dashed' }"></span>
          <span class="relative z-[1] w-11 h-11 sm:mx-auto flex items-center justify-center rounded-full bg-surface shrink-0">
            <span class="w-11 h-11 rounded-full flex items-center justify-center" :style="{ background: STATES[item.state].soft, color: STATES[item.state].color }">
              <svg class="w-[22px] h-[22px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-for="(path, pathIndex) in iconFor(item)" :key="pathIndex" :d="path" /></svg>
            </span>
          </span>
          <span class="block min-w-0 sm:mt-2 sm:px-1">
            <strong class="block font-medium text-[15px] leading-5">{{ item.title }}</strong>
            <span class="block text-[13px] font-normal mt-0.5" :style="{ color: STATES[item.state].color }">{{ STATES[item.state].label }}</span>
            <span class="block text-[13px] text-soft leading-5 mt-0.5 break-words">{{ item.detail }}</span>
          </span>
        </li>
      </ol>
    </section>

    <section v-if="chain.length" class="bg-surface rounded-2xl p-4 sm:p-5 min-w-0" aria-label="Kill Chain">
      <h3 class="text-[14px] text-soft font-normal mb-3">ระยะของการโจมตี</h3>
      <ol class="grid grid-cols-2 sm:grid-cols-6 gap-1.5">
        <li v-for="stage in chain" :key="stage.key" class="rounded-xl px-2.5 py-2 min-w-0 border" :style="{ background: stage.soft, borderColor: stage.state === 'none' ? 'var(--line)' : 'transparent' }">
          <strong class="block text-[14px] font-medium leading-5">{{ stage.thai }}</strong>
          <span class="block text-[11px] text-soft leading-4 truncate">{{ stage.english }}</span>
          <span class="block text-[13px] font-normal mt-1" :style="{ color: stage.color }">{{ stage.label }}</span>
        </li>
      </ol>
    </section>

    <section v-if="checks.length" class="bg-surface rounded-2xl p-4 sm:p-5 min-w-0" aria-label="รายการตรวจ">
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-[14px] text-soft font-normal">รายการตรวจ</h3>
        <span class="text-[14px] font-normal">{{ doneCount }} จาก {{ checks.length }}</span>
      </div>
      <div class="h-1.5 rounded-full bg-raised mt-2 overflow-hidden" aria-hidden="true"><div class="h-full bg-ok rounded-full" :style="{ width: `${doneCount / checks.length * 100}%` }"></div></div>
      <ul class="mt-2 divide-y divide-line">
        <li v-for="(item, index) in checks" :key="index">
          <label :for="`check-${index}`" class="flex items-start gap-3 py-2.5 cursor-pointer">
            <input :id="`check-${index}`" :checked="done[index]" type="checkbox" @change="toggleCheck(index, $event.target.checked)" class="w-5 h-5 mt-0.5 shrink-0 accent-[var(--tint)]">
            <span class="min-w-0 flex-1">
              <span :class="['block font-normal leading-6', done[index] ? 'line-through text-soft' : '']">{{ item.task }}</span>
              <span class="block text-[13px] text-soft leading-5">{{ item.where }}</span>
              <span v-if="item.concern" class="block text-[13px] leading-5 mt-0.5" :style="{ color: 'var(--warn)' }">น่ากังวลถ้า {{ item.concern }}</span>
            </span>
            <span class="w-2 h-2 rounded-full mt-2 shrink-0" :style="{ background: PRIORITY[item.priority] || 'var(--soft)' }" :title="`ความสำคัญ ${item.priority}`"></span>
          </label>
        </li>
      </ul>
    </section>
  </div>
</template>
