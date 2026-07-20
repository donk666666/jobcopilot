<script setup lang="ts">
defineProps<{ title: string; description: string; actionLabel?: string }>()
const emit = defineEmits<{ action: [] }>()
</script>

<template>
  <div class="empty-state">
    <svg class="empty-illustration" width="80" height="80" viewBox="0 0 80 80" fill="none">
      <path d="M20 60 L40 20 L60 60" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.4" fill="none" />
      <circle cx="40" cy="50" r="6" stroke="var(--accent)" stroke-width="1.5" opacity="0.6" fill="none" />
      <path d="M40 56 L40 62" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" opacity="0.4" />
    </svg>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-desc">{{ description }}</p>
    <button v-if="actionLabel" class="empty-action" @click="emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  animation: empty-in var(--t-slow) ease-out;
}

@keyframes empty-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.empty-illustration {
  margin-bottom: 20px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  max-width: 280px;
  line-height: 1.5;
}

.empty-action {
  margin-top: 16px;
  padding: 8px 24px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: var(--radius-btn);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}

.empty-action:hover {
  background: var(--accent-hover);
  transform: scale(1.02);
}
</style>
