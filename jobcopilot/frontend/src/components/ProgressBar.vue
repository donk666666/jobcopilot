<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number }>()

const color = computed(() => {
  if (props.value >= 80) return 'var(--color-success)'
  if (props.value >= 60) return 'var(--color-warning)'
  return 'var(--color-danger)'
})
</script>

<template>
  <div class="mini-progress">
    <div class="mini-progress-track">
      <div
        class="mini-progress-fill"
        :style="{ width: value + '%', background: color }"
      ></div>
    </div>
    <span class="mini-progress-value">{{ value }}</span>
  </div>
</template>

<style scoped>
.mini-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-progress-track {
  width: 60px;
  height: 6px;
  background: var(--bg-hover);
  border-radius: 3px;
  overflow: hidden;
}

.mini-progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width var(--t-normal) ease;
}

.mini-progress-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
