<template>
  <aside class="overview-sidebar">
    <div class="brand-block">
      <span>Umbrella</span>
      <strong>Domain Intelligence</strong>
    </div>

    <p v-if="error" class="sidebar-error">{{ error }}</p>

    <section class="sidebar-section">
      <div class="section-title">
        <span>Dataset</span>
        <strong v-if="loadingOverview" class="skeleton-dark" style="width:48px;height:16px;display:inline-block;"></strong>
        <strong v-else>{{ datasetStatus }}</strong>
      </div>
      <dl class="stat-list">
        <div v-if="loadingOverview" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <div v-if="loadingOverview" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <template v-else>
          <div>
            <dt>Snapshots</dt>
            <dd>{{ formatNumber(overview?.snapshot_days) }}</dd>
          </div>
          <div>
            <dt>Total Rows</dt>
            <dd>{{ formatNumber(overview?.total_rows) }}</dd>
          </div>
        </template>
        <div v-if="loadingOverview" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <div v-if="loadingOverview" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <template v-else>
          <div>
            <dt>First Date</dt>
            <dd>{{ overview?.min_date ?? '-' }}</dd>
          </div>
          <div>
            <dt>Latest Date</dt>
            <dd>{{ overview?.max_date ?? '-' }}</dd>
          </div>
        </template>
      </dl>
    </section>

    <section class="sidebar-section">
      <div class="section-title">
        <span>Domain</span>
        <strong v-if="!activity">{{ domain ?? 'No Query' }}</strong>
        <strong v-else>{{ activity.domain }}</strong>
      </div>
      <dl class="stat-list">
        <div v-if="loadingActivity" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <div v-if="loadingActivity" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <template v-if="!loadingActivity">
          <div>
            <dt>Days Seen</dt>
            <dd>{{ domainValue('days_seen') }}</dd>
          </div>
          <div>
            <dt>Coverage</dt>
            <dd>{{ coverage }}</dd>
          </div>
        </template>
        <div v-if="loadingActivity" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <div v-if="loadingActivity" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <div v-if="loadingActivity" class="skeleton-dark" style="width:100%;height:20px;"></div>
        <template v-if="!loadingActivity">
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
        </template>
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
  },
  domain: {
    type: String,
    default: ''
  },
  loadingOverview: {
    type: Boolean,
    default: false
  },
  loadingActivity: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
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
