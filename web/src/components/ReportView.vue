<script setup>
import { computed, reactive } from 'vue'
import ContentBlocks from './ContentBlocks.vue'
import VisualBoard from './VisualBoard.vue'
import { t } from '../i18n.js'

const props = defineProps({
  report: { type: Object, required: true },
  checksDone: { type: Array, default: () => [] }
})
defineEmits(['copy', 'export', 'checks', 'claude'])

const open = reactive({})
const isOpen = index => open[index] ?? index < 1
const allOpen = computed(() => props.report.sections.every((_section, index) => isOpen(index)))
const toggleAll = () => {
  const value = !allOpen.value
  props.report.sections.forEach((_section, index) => { open[index] = value })
}
const jump = index => {
  open[index] = true
  document.getElementById(`section-${index}`)?.scrollIntoView({ block: 'start' })
}

</script>

<template>
  <article class="grid gap-5 min-w-0">
    <header class="grid gap-1">
      <h2 class="text-[26px] sm:text-[32px] leading-[1.3] font-medium tracking-tight">{{ report.summary?.verdict || t('analysisReport') }}</h2>
      <p v-if="report.summary?.event_time" class="text-[15px] text-soft">{{ t('eventTime', { time: report.summary.event_time }) }}</p>
      <p v-if="report.summary?.source === 'local'" class="text-[15px] text-soft">
        {{ t('madeByLocal') }}
        <button type="button" class="min-h-[36px] text-tint font-normal" @click="$emit('claude')">{{ t('sendToExternal') }}</button>
      </p>
    </header>

    <VisualBoard :report="report" :checks-done="checksDone" @checks="$emit('checks', $event)" />

    <div class="flex flex-wrap gap-3">
      <button type="button" class="min-h-[44px] px-5 rounded-full bg-fill text-white font-normal" @click="$emit('export')">{{ t('exportReport') }}</button>
      <button v-if="report.sections.length" type="button" class="min-h-[44px] px-3 text-tint font-normal" @click="toggleAll">{{ allOpen ? t('collapseAll') : t('expandAll') }}</button>
    </div>

    <nav v-if="report.sections.length > 3" class="flex gap-2 overflow-x-auto pb-1" :aria-label="t('jumpToSection')">
      <button v-for="(section, index) in report.sections" :key="index" type="button"
        class="shrink-0 min-h-[36px] px-3 rounded-full bg-surface text-[14px] font-normal" @click="jump(index)">{{ section.title.replace(/^\d+\.\s*/, '') }}</button>
    </nav>

    <section v-for="(section, index) in report.sections" :id="`section-${index}`" :key="index" class="bg-surface rounded-2xl scroll-mt-20 min-w-0">
      <h3>
        <button type="button" :aria-expanded="isOpen(index)" class="w-full min-h-[52px] flex items-center justify-between gap-3 px-4 py-3 text-left text-[19px] font-medium" @click="open[index] = !isOpen(index)">
          <span>{{ section.title }}</span>
          <svg :class="['w-4 h-4 text-soft shrink-0 transition-transform motion-reduce:transition-none', isOpen(index) ? 'rotate-90' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
        </button>
      </h3>
      <div v-show="isOpen(index)" class="px-4 pb-5">
        <ContentBlocks :blocks="section.blocks" @copy="$emit('copy', $event)" />
      </div>
    </section>
  </article>
</template>
