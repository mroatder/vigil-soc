<script setup>
import { computed } from 'vue'
import logo from '../favicon.svg'
import { lang, locale, setLang, t } from '../i18n.js'

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
const LANGUAGES = [['th', 'ไทย'], ['en', 'EN']]

function groupName(date, today) {
  const age = Math.round((today - startOfDay(date)) / DAY)
  if (age <= 0) return 'today'
  if (age === 1) return 'yesterday'
  if (age < 7) return 'last7Days'
  return 'older'
}

function timeLabel(date, group) {
  const clock = new Intl.DateTimeFormat(locale(), { hour: '2-digit', minute: '2-digit', hour12: false })
  if (group === 'today' || group === 'yesterday') return clock.format(date)
  const shortDate = new Intl.DateTimeFormat(locale(), { day: 'numeric', month: 'short' })
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
        <button type="button" class="lg:hidden min-h-[44px] px-1 text-tint font-normal" @click="$emit('close')">{{ t('close') }}</button>
      </div>
      <button type="button" class="min-h-[44px] rounded-xl bg-tint-soft text-tint font-normal flex items-center justify-center gap-2" @click="$emit('new')">
        <svg class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        {{ t('newChat') }}
      </button>
      <input :value="query" type="search" :aria-label="t('searchHistory')" :placeholder="t('searchPlaceholder')"
        class="w-full min-h-[40px] rounded-[10px] bg-raised px-3 text-[15px] placeholder:text-hint focus:outline-none focus-visible:ring-2 focus-visible:ring-tint"
        @input="$emit('update:query', $event.target.value)">
    </div>

    <nav class="flex-1 min-h-0 overflow-y-auto px-2 pb-3" :aria-label="t('historyNav')">
      <ul v-if="pending.length" class="grid gap-0.5 mt-1">
        <li v-for="job in pending" :key="job.run" class="px-2.5 py-2">
          <span class="block line-clamp-2 text-[15px] leading-5 font-normal text-soft">{{ job.title }}</span>
          <span class="block text-[13px] text-soft mt-1">{{ t('localAnalyzing') }}</span>
        </li>
      </ul>

      <section v-for="group in groups" :key="group.name" class="mt-2">
        <h2 class="px-2.5 py-1 text-[13px] text-soft font-normal">{{ t(group.name) }}</h2>
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
                <span v-else-if="item.answered">{{ t('hasReport') }}</span>
                <span v-else>{{ t('waitingAnswer') }}</span>
                <span class="ml-auto whitespace-nowrap">{{ item.time }}</span>
              </span>
            </button>
          </li>
        </ul>
      </section>

      <div v-if="failed" class="px-2.5 py-3 text-[15px]">
        <p class="text-soft">{{ t('historyFailed') }}</p>
        <button type="button" class="min-h-[44px] text-tint font-normal" @click="$emit('retry')">{{ t('retry') }}</button>
      </div>
      <p v-else-if="loaded && !cases.length && !pending.length" class="px-2.5 py-3 text-[15px] text-soft">
        {{ query.trim() ? t('noMatch', { query: query.trim() }) : t('noCases') }}
      </p>
      <p v-if="more" class="px-2.5 py-3 text-[13px] text-soft">{{ t('showingLatest') }}</p>
    </nav>

    <div class="border-t border-line">
      <button v-if="canQuit" type="button" :disabled="pending.length > 0" :title="pending.length ? t('waitLocal') : undefined" class="w-full min-h-[44px] px-4 text-left text-[15px] text-tint font-normal disabled:opacity-50" @click="$emit('quit')">{{ t('quit') }}</button>
      <div class="px-4 pt-2.5 flex items-center justify-between gap-3">
        <span class="text-[13px] text-soft">{{ t('language') }}</span>
        <div class="grid grid-cols-2 bg-raised rounded-[10px] p-0.5" role="group" :aria-label="t('language')">
          <button v-for="option in LANGUAGES" :key="option[0]" type="button" :aria-pressed="lang === option[0]"
            :class="['min-h-[32px] min-w-[48px] px-2 rounded-lg text-[13px] font-normal', lang === option[0] ? 'bg-surface shadow-sm' : 'text-soft']" @click="setLang(option[0])">{{ option[1] }}</button>
        </div>
      </div>
      <p class="px-4 py-2.5 text-[13px] text-soft">{{ t('localOnly') }}<span class="float-right">v{{ version }}</span></p>
    </div>
  </aside>
</template>
