<script setup>
import InlineText from './InlineText.vue'

defineProps({ blocks: { type: Array, required: true } })
defineEmits(['copy'])
</script>

<template>
  <div class="grid gap-4 min-w-0">
    <template v-for="(block, index) in blocks" :key="index">
      <p v-if="block.type === 'paragraph'" class="max-w-[66ch]"><InlineText :parts="block.parts" /></p>
      <h3 v-else-if="block.type === 'heading'" class="text-[17px] font-medium mt-2"><InlineText :parts="block.parts" /></h3>
      <component :is="block.ordered ? 'ol' : 'ul'" v-else-if="block.type === 'list'" :start="block.ordered ? block.start : undefined"
        :class="['pl-6 grid gap-2 max-w-[66ch]', block.ordered ? 'list-decimal' : 'list-disc']">
        <li v-for="(item, itemIndex) in block.items" :key="itemIndex"><InlineText :parts="item" /></li>
      </component>
      <div v-else-if="block.type === 'table'" class="overflow-x-auto">
        <table class="w-full text-[15px] border-collapse">
          <thead>
            <tr><th v-for="(cell, cellIndex) in block.head" :key="cellIndex" class="text-left font-medium text-soft py-2 pr-5 border-b border-line align-top"><InlineText :parts="cell" /></th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex" class="py-2.5 pr-5 border-b border-line align-top"><InlineText :parts="cell" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="block.type === 'code'" class="bg-raised rounded-2xl p-4 flex items-start gap-3 min-w-0">
        <pre class="flex-1 min-w-0 overflow-x-auto font-mono text-[13.5px] leading-6">{{ block.value }}</pre>
        <button type="button" class="text-tint text-[15px] font-normal shrink-0 min-h-[32px]" @click="$emit('copy', block.value)">คัดลอก</button>
      </div>
    </template>
  </div>
</template>
