<template>
  <aside class="top-domains-panel">
    <div class="panel-kicker">Current Active</div>
    <div class="top-panel-heading">
      <h2>Top 100 Domains</h2>
      <span>{{ snapshotDate ?? '-' }} · {{ domains.length }}</span>
    </div>
    <div class="top-domain-list">
      <template v-if="loading">
        <div v-for="i in 6" :key="i" class="skeleton" style="width:100%;height:32px;"></div>
      </template>
      <div v-else-if="error" class="compact-empty">{{ error }}</div>
      <template v-else>
        <button
          v-for="item in domains"
          :key="`${item.rank}-${item.domain}`"
          class="top-domain-row"
          :class="{ active: item.domain === selectedDomain }"
          type="button"
          aria-label="Select domain"
          @click="$emit('select', item.domain)"
        >
          <span class="rank-badge">{{ item.rank }}</span>
          <span class="domain-name">{{ item.domain }}</span>
        </button>
        <div v-if="domains.length === 0" class="compact-empty">No imported data</div>
      </template>
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
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

defineEmits(['select'])
</script>
