<template>
  <div ref="chartEl" class="rank-chart"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  series: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['visible-range'])

const chartEl = ref(null)
let chart = null

function formatRank(value) {
  if (value >= 1000000) return '1M'
  if (value >= 1000) return `${Math.round(value / 1000)}k`
  return value.toLocaleString()
}

function rankAxisRange() {
  const ranks = props.series
    .map((point) => point.rank)
    .filter((rank) => Number.isFinite(rank))

  if (ranks.length === 0) {
    return { min: 1, max: 1000000 }
  }

  const minRank = Math.min(...ranks)
  const maxRank = Math.max(...ranks)
  const spread = Math.max(maxRank - minRank, Math.round(maxRank * 0.08), 100)
  const padding = Math.ceil(spread * 0.18)

  return {
    min: Math.max(1, minRank - padding),
    max: Math.min(1000000, maxRank + padding)
  }
}

function emitFullRange() {
  if (props.series.length === 0) return
  emit('visible-range', {
    from: props.series[0].date,
    to: props.series[props.series.length - 1].date
  })
}

function emitZoomRange(event) {
  if (props.series.length === 0) return

  const zoom = event.batch?.[0] ?? event
  const lastIndex = props.series.length - 1
  let startIndex = Number.isFinite(zoom.startValue) ? Number(zoom.startValue) : null
  let endIndex = Number.isFinite(zoom.endValue) ? Number(zoom.endValue) : null

  if (startIndex === null || endIndex === null) {
    const startPercent = Number.isFinite(zoom.start) ? zoom.start : 0
    const endPercent = Number.isFinite(zoom.end) ? zoom.end : 100
    startIndex = Math.floor((startPercent / 100) * lastIndex)
    endIndex = Math.ceil((endPercent / 100) * lastIndex)
  }

  startIndex = Math.max(0, Math.min(lastIndex, startIndex))
  endIndex = Math.max(startIndex, Math.min(lastIndex, endIndex))

  emit('visible-range', {
    from: props.series[startIndex].date,
    to: props.series[endIndex].date
  })
}

function renderChart() {
  if (!chart && chartEl.value) {
    chart = echarts.init(chartEl.value)
    chart.on('dataZoom', emitZoomRange)
  }
  if (!chart) return

  const axisRange = rankAxisRange()

  chart.setOption({
    color: ['#008f7a'],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#152026'
        }
      },
      formatter(params) {
        const item = params[0]
        const point = props.series[item.dataIndex]
        const rank = point.rank ? point.rank.toLocaleString() : 'Not in top 1m'
        const score = point.active_score ?? '-'
        return `${point.date}<br/>Rank: ${rank}<br/>Activity Score: ${score}`
      }
    },
    grid: {
      left: 72,
      right: 28,
      top: 28,
      bottom: 54
    },
    xAxis: {
      type: 'category',
      data: props.series.map((point) => point.date),
      axisLabel: {
        hideOverlap: true
      }
    },
    yAxis: {
      type: 'value',
      inverse: true,
      min: axisRange.min,
      max: axisRange.max,
      splitNumber: 6,
      axisLabel: {
        formatter(value) {
          return formatRank(value)
        }
      },
      splitLine: {
        lineStyle: {
          color: '#e7ecef'
        }
      }
    },
    dataZoom: [
      {
        type: 'inside'
      },
      {
        type: 'slider',
        height: 24,
        bottom: 12
      }
    ],
    series: [
      {
        name: 'Rank',
        type: 'line',
        connectNulls: false,
        showSymbol: false,
        lineStyle: {
          width: 3
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 143, 122, 0.24)' },
              { offset: 1, color: 'rgba(0, 143, 122, 0.02)' }
            ]
          }
        },
        emphasis: {
          focus: 'series'
        },
        data: props.series.map((point) => point.rank)
      }
    ]
  }, true)
  emitFullRange()
}

function resizeChart() {
  chart?.resize()
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', resizeChart)
})

watch(() => props.series, renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.off('dataZoom', emitZoomRange)
  chart?.dispose()
  chart = null
})
</script>
