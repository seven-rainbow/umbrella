<template>
  <aside class="volatile-domains-panel">
    <div class="panel-kicker">Volatility Watch</div>
    <div class="top-panel-heading">
      <h2>Volatile Domains</h2>
      <span>{{ snapshotDate ?? '-' }} · {{ domains.length }}</span>
    </div>
    <div class="top-domain-list">
      <div v-for="item in domains" :key="item.domain" class="volatile-row">
        <button class="volatile-main" type="button" @click="$emit('select', item.domain)">
          <span class="domain-name">{{ item.domain }}</span>
          <span>{{ item.reason }}</span>
        </button>
        <button class="mini-action" type="button" @click="$emit('assess', item.domain)">Assess</button>
      </div>
      <div v-if="domains.length === 0" class="compact-empty">No volatile domains</div>
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
  }
})

defineEmits(['select', 'assess'])
</script>
