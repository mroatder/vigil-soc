<script setup>
defineProps({ parts: { type: Array, required: true } })
</script>

<template>
  <template v-for="(part, index) in parts" :key="index">
    <code v-if="part.type === 'code'" class="font-mono text-[.86em] bg-raised rounded-md px-1.5 py-0.5 break-words">{{ part.value }}</code>
    <strong v-else-if="part.type === 'bold'" class="font-medium">{{ part.value }}</strong>
    <template v-else>{{ part.value }}</template>
  </template>
</template>
