<template>
  <section class="query-panel">
    <div class="query-copy">
      <div class="panel-kicker">Domain Lookup</div>
      <h1>Historical Activity</h1>
      <p>Daily rank history from Cisco Umbrella top-1m snapshots.</p>
    </div>
    <form class="query-form" @submit.prevent="$emit('submit')">
      <label class="query-field domain-field">
        <span>Domain</span>
        <input
          :value="domain"
          type="text"
          placeholder="example.com"
          autocomplete="off"
          @input="$emit('update:domain', $event.target.value.trim())"
        />
      </label>
      <label class="query-field">
        <span>From</span>
        <input
          :value="fromDate"
          type="date"
          :max="toDate || maxDate"
          @input="$emit('update:fromDate', $event.target.value)"
        />
      </label>
      <label class="query-field">
        <span>To</span>
        <input
          :value="toDate"
          type="date"
          :min="fromDate"
          :max="maxDate"
          @input="$emit('update:toDate', $event.target.value)"
        />
      </label>
      <button class="query-submit" type="submit" :disabled="loading || Boolean(rangeError)">
        {{ loading ? 'Loading' : 'Query' }}
      </button>
      <div class="range-presets" aria-label="Date range presets">
        <button type="button" @click="$emit('apply-range', 30)">30D</button>
        <button type="button" @click="$emit('apply-range', 90)">90D</button>
        <button type="button" @click="$emit('apply-range', 180)">180D</button>
        <button type="button" @click="$emit('apply-range', 365)">1Y</button>
      </div>
      <p v-if="rangeError" class="range-error">{{ rangeError }}</p>
    </form>
  </section>
</template>

<script setup>
defineProps({
  domain: {
    type: String,
    required: true
  },
  fromDate: {
    type: String,
    required: true
  },
  toDate: {
    type: String,
    required: true
  },
  loading: {
    type: Boolean,
    required: true
  },
  maxDate: {
    type: String,
    required: true
  },
  rangeError: {
    type: String,
    default: ''
  }
})

defineEmits(['submit', 'update:domain', 'update:fromDate', 'update:toDate', 'apply-range'])
</script>
