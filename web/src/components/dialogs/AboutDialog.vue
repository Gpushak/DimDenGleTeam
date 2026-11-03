<script setup lang="ts">
import AppDialog from '@/components/AppDialog.vue'

defineEmits<{ close: [] }>()
</script>

<template>
  <AppDialog title="О программе" @close="$emit('close')">
    <div class="about">
      <strong>Складской учёт</strong>
      <span class="muted">Версия 1.0.0</span>
      <p>
        Учёт товаров на складе: структура контейнеров,
        позиции, весы, QR-этикетки.
        Своей базы нет — все данные на сервере.
      </p>
      <p>Qwentory Team</p>
    </div>
    <div class="form-actions">
      <button type="button" class="btn" @click="$emit('close')">Закрыть</button>
    </div>
  </AppDialog>
</template>

<style scoped lang="scss">
.about {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
}

strong {
  font-size: 20px;
}

.muted {
  color: var(--muted);
}

p {
  margin: 6px 0 0;
}
</style>
