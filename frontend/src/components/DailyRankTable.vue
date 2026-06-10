<template>
  <section class="table-panel">
    <div class="panel-header">
      <div>
        <h2>Daily Details</h2>
        <p>{{ fromDate }} to {{ toDate }}</p>
      </div>
      <span>{{ series.length }} days</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Rank</th>
            <th>Activity Score</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="point in series" :key="point.date">
            <td>{{ point.date }}</td>
            <td>{{ formatRank(point.rank) }}</td>
            <td>{{ point.active_score ?? '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
defineProps({
  series: {
    type: Array,
    required: true
  },
  fromDate: {
    type: String,
    required: true
  },
  toDate: {
    type: String,
    required: true
  }
})

function formatRank(value) {
  if (value === null || value === undefined) return '-'
  return Math.round(value).toLocaleString()
}
</script>
