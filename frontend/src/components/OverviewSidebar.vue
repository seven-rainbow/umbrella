<template>
  <aside class="overview-sidebar">
    <div class="brand-block">
      <span>Umbrella</span>
      <strong>Domain Intelligence</strong>
    </div>

    <section class="sidebar-section">
      <div class="section-title">
        <span>Dataset</span>
        <strong>{{ datasetStatus }}</strong>
      </div>
      <dl class="stat-list">
        <div>
          <dt>Snapshots</dt>
          <dd>{{ formatNumber(overview?.snapshot_days) }}</dd>
        </div>
        <div>
          <dt>Total Rows</dt>
          <dd>{{ formatNumber(overview?.total_rows) }}</dd>
        </div>
        <div>
          <dt>First Date</dt>
          <dd>{{ overview?.min_date ?? '-' }}</dd>
        </div>
        <div>
          <dt>Latest Date</dt>
          <dd>{{ overview?.max_date ?? '-' }}</dd>
        </div>
      </dl>
    </section>

    <section class="sidebar-section">
      <div class="section-title">
        <span>Domain</span>
        <strong>{{ activity?.domain ?? 'No Query' }}</strong>
      </div>
      <dl class="stat-list">
        <div>
          <dt>Days Seen</dt>
          <dd>{{ domainValue('days_seen') }}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{{ coverage }}</dd>
        </div>
        <div>
          <dt>Best Rank</dt>
          <dd>{{ formatRank(activity?.summary.best_rank) }}</dd>
        </div>
        <div>
          <dt>Worst Rank</dt>
          <dd>{{ formatRank(activity?.summary.worst_rank) }}</dd>
        </div>
        <div>
          <dt>Average Rank</dt>
          <dd>{{ formatRank(activity?.summary.avg_rank) }}</dd>
        </div>
      </dl>
    </section>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  overview: {
    type: Object,
    default: null
  },
  activity: {
    type: Object,
    default: null
  }
})

const datasetStatus = computed(() => {
  if (!props.overview || props.overview.snapshot_days === 0) return 'Empty'
  return 'Ready'
})

const coverage = computed(() => {
  if (!props.activity) return '-'
  return `${Math.round(props.activity.summary.coverage_ratio * 100)}%`
})

function domainValue(key) {
  if (!props.activity) return '-'
  return formatNumber(props.activity.summary[key])
}

function formatNumber(value) {
  if (value === null || value === undefined) return '-'
  return Number(value).toLocaleString()
}

function formatRank(value) {
  if (value === null || value === undefined) return '-'
  return Math.round(value).toLocaleString()
}
</script>
