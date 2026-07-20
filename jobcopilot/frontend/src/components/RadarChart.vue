<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: Record<string, number>
  size?: number
}>()

const dims = computed(() => {
  const entries = Object.entries(props.data)
  return { labels: entries.map(([k]) => k), values: entries.map(([, v]) => v) }
})

const s = computed(() => props.size || 200)
const cx = computed(() => s.value / 2)
const cy = computed(() => s.value / 2)
const r = computed(() => s.value / 2 - 30)

function polar(i: number, total: number, radius: number): [number, number] {
  const angle = (Math.PI * 2 * i) / total - Math.PI / 2
  return [cx.value + radius * Math.cos(angle), cy.value + radius * Math.sin(angle)]
}

const pathData = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return ''
  const pts = dims.value.values.map((v, i) => {
    const [x, y] = polar(i, n, (v / 100) * r.value)
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  })
  return pts.join(' ') + 'Z'
})

const gridPaths = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return []
  const levels = [0.25, 0.5, 0.75, 1]
  return levels.map(level => {
    const pts = Array.from({ length: n }, (_, i) => {
      const [x, y] = polar(i, n, level * r.value)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    return pts.join(' ') + 'Z'
  })
})

const axisLines = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return []
  return Array.from({ length: n }, (_, i) => {
    const [x, y] = polar(i, n, r.value)
    return { x1: cx.value, y1: cy.value, x2: x, y2: y }
  })
})

const labelPositions = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return []
  return dims.value.labels.map((label, i) => {
    const [x, y] = polar(i, n, r.value + 16)
    return { label, x, y }
  })
})
</script>

<template>
  <svg :width="s" :height="s" :viewBox="`0 0 ${s} ${s}`">
    <path
      v-for="(gp, idx) in gridPaths"
      :key="'g' + idx"
      :d="gp"
      fill="none"
      :stroke="'var(--border-subtle)'"
      stroke-width="1"
    />
    <line
      v-for="(al, idx) in axisLines"
      :key="'a' + idx"
      :x1="al.x1" :y1="al.y1" :x2="al.x2" :y2="al.y2"
      stroke="var(--border-subtle)" stroke-width="1"
    />
    <path
      :d="pathData"
      fill="rgba(240, 185, 11, 0.15)"
      stroke="var(--accent)"
      stroke-width="2"
      stroke-linejoin="round"
    />
    <circle
      v-for="(v, idx) in dims.values"
      :key="'p' + idx"
      :cx="polar(idx, dims.labels.length, (v / 100) * r)[0]"
      :cy="polar(idx, dims.labels.length, (v / 100) * r)[1]"
      r="3"
      fill="var(--accent)"
    />
    <text
      v-for="lp in labelPositions"
      :key="lp.label"
      :x="lp.x" :y="lp.y"
      text-anchor="middle"
      dominant-baseline="middle"
      fill="var(--text-muted)"
      font-size="11"
    >{{ lp.label }}</text>
  </svg>
</template>
