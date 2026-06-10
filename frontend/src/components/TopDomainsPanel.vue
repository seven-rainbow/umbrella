<template>
  <aside class="top-domains-panel">
    <div class="panel-kicker">Current Active</div>
    <div class="top-panel-heading">
      <h2>Top 100 Domains</h2>
      <span>{{ snapshotDate ?? '-' }} · {{ domains.length }}</span>
    </div>
    <div class="top-domain-list">
      <button
        v-for="item in domains"
        :key="`${item.rank}-${item.domain}`"
        class="top-domain-row"
        :class="{ active: item.domain === selectedDomain }"
        type="button"
        @click="$emit('select', item.domain)"
      >
        <span class="rank-badge">{{ item.rank }}</span>
        <span class="domain-name">{{ item.domain }}</span>
      </button>
      <div v-if="domains.length === 0" class="compact-empty">No imported data</div>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  snapshotDate: {
    type: String,
    default: null
  },
  domains: {
    type: Array,
    required: true
  },
  selectedDomain: {
    type: String,
    default: ''
  }
})

defineEmits(['select'])
</script>
