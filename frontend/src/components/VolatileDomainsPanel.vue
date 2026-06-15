<template>
  <aside class="volatile-domains-panel">
    <div class="panel-kicker">Volatility Watch</div>
    <div class="top-panel-heading">
      <h2>Volatile Domains</h2>
      <span>{{ snapshotDate ?? '-' }} · {{ domains.length }}</span>
    </div>
    <div class="top-domain-list">
      <template v-if="loading">
        <div v-for="i in 5" :key="i" class="skeleton" style="width:100%;height:42px;"></div>
      </template>
      <div v-else-if="error" class="compact-empty">{{ error }}</div>
      <template v-else>
        <div v-for="item in domains" :key="item.domain" class="volatile-row">
          <button class="volatile-main" type="button" aria-label="Select volatile domain" @click="$emit('select', item.domain)">
            <span class="domain-name">{{ item.domain }}</span>
            <span>{{ item.reason }}</span>
          </button>
          <button class="mini-action" type="button" aria-label="Assess domain" @click="$emit('assess', item.domain)">Assess</button>
        </div>
        <div v-if="domains.length === 0" class="compact-empty">No volatile domains</div>
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
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

defineEmits(['select', 'assess'])
</script>
