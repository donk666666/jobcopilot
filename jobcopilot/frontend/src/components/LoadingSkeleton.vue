<script setup lang="ts">
defineProps<{ lines?: number; delay?: number }>()
</script>

<template>
  <div class="skeleton-panel">
    <div class="skeleton-header">AI 正在解析...</div>
    <div
      v-for="i in (lines || 4)"
      :key="i"
      class="skeleton-row"
      :style="{ animationDelay: (delay || 200) * i + 'ms' }"
    >
      <div class="skeleton-label skeleton-line"></div>
      <div class="skeleton-value skeleton-line" :style="{ width: (50 + Math.random() * 40) + '%' }"></div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 24px;
}

.skeleton-header {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 24px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  animation: skeleton-fade-in 0.3s ease-out both;
}

@keyframes skeleton-fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.skeleton-label {
  width: 80px;
  flex-shrink: 0;
}

.skeleton-value {
  flex: 1;
}
</style>
