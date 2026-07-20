<script setup lang="ts">
defineProps<{ status: 'online' | 'offline' | 'loading' }>()
</script>

<template>
  <div class="status-indicator">
    <span class="status-dot" :class="`dot-${status}`"></span>
    <span class="status-label">
      {{ status === 'online' ? '服务在线' : status === 'offline' ? '服务离线' : '连接中...' }}
    </span>
  </div>
</template>

<style scoped>
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-online {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
}

.dot-offline {
  background: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
}

.dot-loading {
  background: var(--color-warning);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.status-label {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
