<script setup>
import { computed } from 'vue'
import logo from '../favicon.svg'

const props = defineProps({
  cases: { type: Array, required: true },
  pending: { type: Array, required: true },
  activeId: { type: String, default: '' },
  query: { type: String, default: '' },
  open: { type: Boolean, default: false },
  more: { type: Boolean, default: false },
  failed: { type: Boolean, default: false },
  loaded: { type: Boolean, default: false },
  version: { type: String, default: '' },
  canQuit: { type: Boolean, default: false }
})
defineEmits(['update:query', 'select', 'new', 'close', 'retry', 'quit'])

const SEVERITY = {
  Info: 'var(--info)',
  Low: 'var(--ok)',
  Medium: 'var(--warn)',
  High: 'var(--bad)',
  Critical: 'var(--bad)'
}

const startOfDay = date => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
const DAY = 86400000
const clock = new Intl.DateTimeFormat('th-TH-u-ca-gregory', { hour: '2-digit', minute: '2-digit', hour12: false })
const shortDate = new Intl.DateTimeFormat('th-TH-u-ca-gregory', { day: 'numeric', month: 'short' })

function groupName(date, today) {
  const age = Math.round((today - startOfDay(date)) / DAY)
  if (age <= 0) return 'วันนี้'
  if (age === 1) return 'เมื่อวาน'
  if (age < 7) return '7 วันที่ผ่านมา'
  return 'เก่ากว่า'
}

function timeLabel(date, group) {
  if (group === 'วันนี้' || group === 'เมื่อวาน') return clock.format(date)
  return `${shortDate.format(date)} ${clock.format(date)}`
}

const groups = computed(() => {
  const today = startOfDay(new Date())
  const result = []
  for (const item of props.cases) {
    const date = new Date(item.created_at)
    const name = groupName(date, today)
    let group = result[result.length - 1]
    if (!group || group.name !== name) {
      group = { name, items: [] }
      result.push(group)
    }
    group.items.push({ ...item, time: timeLabel(date, name) })
  }
  return result
})
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-30 bg-black/40 lg:hidden" @click="$emit('close')"></div>
  <aside id="history" :class="['fixed inset-y-0 left-0 z-30 w-[300px] max-w-[86vw] lg:w-[288px] bg-side border-r border-line flex flex-col transition-transform motion-reduce:transition-none lg:translate-x-0 lg:visible', open ? 'translate-x-0' : '-translate-x-full invisible']">
    <div class="px-3 pt-3 pb-2 grid gap-2">
      <div class="flex items-center justify-between gap-2 pl-1 min-h-[44px]">
        <strong class="font-medium flex items-center gap-2"><img :src="logo" alt="" class="w-6 h-6">Vigil</strong>
        <button type="button" class="lg:hidden min-h-[44px] px-1 text-tint font-normal" @click="$emit('close')">ปิด</button>
      </div>
      <button type="button" class="min-h-[44px] rounded-xl bg-tint-soft text-tint font-normal flex items-center justify-center gap-2" @click="$emit('new')">
        <svg class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        แชตใหม่
      </button>
      <input :value="query" type="search" aria-label="ค้นหาประวัติ" placeholder="ค้นหา IP, Host, Rule"
        class="w-full min-h-[40px] rounded-[10px] bg-raised px-3 text-[15px] placeholder:text-hint focus:outline-none focus-visible:ring-2 focus-visible:ring-tint"
        @input="$emit('update:query', $event.target.value)">
    </div>

    <nav class="flex-1 min-h-0 overflow-y-auto px-2 pb-3" aria-label="ประวัติการวิเคราะห์">
      <ul v-if="pending.length" class="grid gap-0.5 mt-1">
        <li v-for="job in pending" :key="job.run" class="px-2.5 py-2">
          <span class="block line-clamp-2 text-[15px] leading-5 font-normal text-soft">{{ job.title }}</span>
          <span class="block text-[13px] text-soft mt-1">Local AI กำลังวิเคราะห์</span>
        </li>
      </ul>

      <section v-for="group in groups" :key="group.name" class="mt-2">
        <h2 class="px-2.5 py-1 text-[13px] text-soft font-normal">{{ group.name }}</h2>
        <ul class="grid gap-0.5">
          <li v-for="item in group.items" :key="item.id">
            <button type="button" :aria-current="item.id === activeId ? 'true' : undefined"
              :class="['w-full text-left rounded-xl px-2.5 py-2 min-w-0 block', item.id === activeId ? 'bg-raised' : 'hover:bg-ground']"
              @click="$emit('select', item.id)">
              <span class="block line-clamp-2 text-[15px] leading-5 font-normal break-words">{{ item.title }}</span>
              <span class="flex items-center gap-1.5 text-[13px] leading-5 text-soft mt-1">
                <template v-if="item.severity">
                  <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: SEVERITY[item.severity] }"></span>
                  <span>{{ item.severity }}</span>
                </template>
                <span v-else-if="item.answered">มีรายงานแล้ว</span>
                <span v-else>รอคำตอบ Claude</span>
                <span class="ml-auto whitespace-nowrap">{{ item.time }}</span>
              </span>
            </button>
          </li>
        </ul>
      </section>

      <div v-if="failed" class="px-2.5 py-3 text-[15px]">
        <p class="text-soft">โหลดประวัติไม่สำเร็จ</p>
        <button type="button" class="min-h-[44px] text-tint font-normal" @click="$emit('retry')">ลองอีกครั้ง</button>
      </div>
      <p v-else-if="loaded && !cases.length && !pending.length" class="px-2.5 py-3 text-[15px] text-soft">
        {{ query.trim() ? `ไม่พบเคสที่ตรงกับ "${query.trim()}"` : 'เคสที่วิเคราะห์จะแสดงที่นี่' }}
      </p>
      <p v-if="more" class="px-2.5 py-3 text-[13px] text-soft">แสดง 200 เคสล่าสุด ค้นหาเพื่อดูเคสที่เก่ากว่า</p>
    </nav>

    <div class="border-t border-line">
      <button v-if="canQuit" type="button" :disabled="pending.length > 0" :title="pending.length ? 'รอ Local AI ทำงานให้เสร็จก่อน' : undefined" class="w-full min-h-[44px] px-4 text-left text-[15px] text-tint font-normal disabled:opacity-50" @click="$emit('quit')">ปิดโปรแกรม</button>
      <p class="px-4 py-2.5 text-[13px] text-soft">เก็บเฉพาะในเครื่องนี้<span class="float-right">v{{ version }}</span></p>
    </div>
  </aside>
</template>
