<template>
  <section class="assessment-panel">
    <div class="panel-header">
      <div>
        <h2>AI Assessment</h2>
        <p v-if="assessment?.report">{{ assessment.domain }} · {{ assessment.status }}</p>
        <p v-else>Run an assessment after loading a domain.</p>
      </div>
      <span v-if="assessment?.report" class="risk-badge" :class="`risk-${assessment.report.risk_level}`">
        {{ assessment.report.risk_level }}
      </span>
    </div>

    <div v-if="loading" class="compact-empty" aria-live="polite">Assessing domain activity...</div>
    <div v-else-if="error" class="assessment-error" aria-live="polite">
      <strong>Assessment unavailable</strong>
      <span>{{ error }}</span>
    </div>
    <div v-else-if="assessment?.report" class="assessment-body">
      <p class="assessment-summary">{{ assessment.report.summary }}</p>
      <div class="evidence-grid">
        <div>
          <span>Confidence</span>
          <strong>{{ Math.round(assessment.report.confidence * 100) }}%</strong>
        </div>
        <div>
          <span>Volatility</span>
          <strong>{{ assessment.report.evidence.volatility_score }}</strong>
        </div>
        <div>
          <span>Latest rank</span>
          <strong>{{ formatNumber(assessment.report.evidence.latest_rank) }}</strong>
        </div>
        <div>
          <span>Coverage</span>
          <strong>{{ Math.round(assessment.report.evidence.coverage_ratio * 100) }}%</strong>
        </div>
      </div>
      <div class="assessment-columns">
        <div>
          <h3>Findings</h3>
          <ul>
            <li v-for="item in assessment.report.key_findings" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div>
          <h3>Actions</h3>
          <ul>
            <li v-for="item in assessment.report.recommended_actions" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
      <p class="model-line">
        {{ assessment.report.model.provider }} · {{ assessment.report.model.model }}
      </p>
    </div>
    <div v-else class="empty-state small">No assessment report yet.</div>
  </section>
</template>

<script setup>
defineProps({
  assessment: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    required: true
  },
  error: {
    type: String,
    default: ''
  }
})

function formatNumber(value) {
  return value === null || value === undefined ? '-' : value.toLocaleString()
}
</script>
