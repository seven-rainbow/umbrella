<template>
  <main class="dashboard-shell">
    <OverviewSidebar :overview="overview" :activity="activity" />

    <TopDomainsPanel
      :snapshot-date="topDomains?.snapshot_date"
      :domains="topDomains?.domains ?? []"
      :selected-domain="domain"
      @select="selectTopDomain"
    />

    <div class="main-content">
      <QueryPanel
        v-model:domain="domain"
        v-model:from-date="fromDate"
        v-model:to-date="toDate"
        :loading="loading"
        :max-date="today"
        :range-error="dateRangeError"
        @apply-range="applyDateRange"
        @submit="loadActivity"
      />

      <p v-if="error" class="error-message">{{ error }}</p>

      <section class="chart-panel">
        <div class="panel-header">
          <div>
            <h2>Daily Rank Curve</h2>
            <p v-if="activity">{{ activity.domain }} · {{ activity.from }} to {{ activity.to }}</p>
            <p v-else>Enter a domain to inspect its ranking trend.</p>
          </div>
          <div v-if="activity" class="trend-strip">
            <span>Latest {{ latestRank }}</span>
            <span>Seen {{ activity.summary.days_seen }}/{{ activity.summary.total_days }}</span>
          </div>
        </div>
        <RankChart v-if="activity" :series="activity.series" @visible-range="setChartVisibleRange" />
        <div v-else class="empty-state">No query has been run.</div>
      </section>

      <DailyRankTable
        v-if="activity"
        :series="selectedDailySeries"
        :from-date="selectedDailyRange.from"
        :to-date="selectedDailyRange.to"
      />
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import DailyRankTable from './components/DailyRankTable.vue'
import OverviewSidebar from './components/OverviewSidebar.vue'
import QueryPanel from './components/QueryPanel.vue'
import RankChart from './components/RankChart.vue'
import TopDomainsPanel from './components/TopDomainsPanel.vue'
import { fetchActivity } from './services/activityApi'
import { fetchCurrentTopDomains, fetchOverview } from './services/statsApi'

const domain = ref('example.com')
const activity = ref(null)
const overview = ref(null)
const topDomains = ref(null)
const loading = ref(false)
const error = ref('')
const fromDate = ref('')
const toDate = ref('')
const today = isoDate(new Date())
const chartVisibleRange = ref(null)

const latestRank = computed(() => {
  if (!activity.value) return '-'
  const ranked = [...activity.value.series].reverse().find((point) => point.rank !== null)
  return ranked ? ranked.rank.toLocaleString() : '-'
})

const dateRangeDays = computed(() => {
  if (!fromDate.value || !toDate.value) return 0
  const from = new Date(`${fromDate.value}T00:00:00`)
  const to = new Date(`${toDate.value}T00:00:00`)
  return Math.round((to - from) / 86400000) + 1
})

const dateRangeError = computed(() => {
  if (!fromDate.value || !toDate.value) return ''
  if (dateRangeDays.value <= 0) return 'From date must be earlier than To date.'
  if (dateRangeDays.value > 365) return 'Query range is limited to 1 year.'
  return ''
})

const selectedDailyRange = computed(() => {
  const fallback = {
    from: fromDate.value || activity.value?.from,
    to: toDate.value || activity.value?.to
  }

  if (!chartVisibleRange.value) return fallback

  return {
    from: chartVisibleRange.value.from ?? fallback.from,
    to: chartVisibleRange.value.to ?? fallback.to
  }
})

const selectedDailySeries = computed(() => {
  if (!activity.value) return []
  const { from, to } = selectedDailyRange.value
  return activity.value.series.filter((point) => point.date >= from && point.date <= to)
})

function isoDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function resetDates() {
  applyDateRange(180)
}

function applyDateRange(days) {
  const to = new Date(`${today}T00:00:00`)
  const from = new Date(to)
  from.setDate(to.getDate() - days + 1)
  fromDate.value = isoDate(from)
  toDate.value = today
}

function setChartVisibleRange(range) {
  chartVisibleRange.value = range
}

async function loadActivity() {
  if (!domain.value) return
  if (dateRangeError.value) {
    error.value = dateRangeError.value
    return
  }
  loading.value = true
  error.value = ''
  try {
    activity.value = await fetchActivity(domain.value, fromDate.value, toDate.value)
    chartVisibleRange.value = {
      from: activity.value.from,
      to: activity.value.to
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function selectTopDomain(selectedDomain) {
  domain.value = selectedDomain
  await loadActivity()
}

async function loadOverview() {
  try {
    overview.value = await fetchOverview()
  } catch (err) {
    error.value = err.message
  }
}

async function loadTopDomains() {
  try {
    topDomains.value = await fetchCurrentTopDomains()
  } catch (err) {
    error.value = err.message
  }
}

onMounted(() => {
  resetDates()
  loadOverview()
  loadTopDomains()
})

watch([fromDate, toDate], () => {
  chartVisibleRange.value = null
})
</script>
