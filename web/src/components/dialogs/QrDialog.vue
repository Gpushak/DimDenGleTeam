<script setup lang="ts">
import { onMounted, ref } from 'vue'
import QRCode from 'qrcode'
import { itemQrPayload } from '@/lib/format'
import { errorMessage } from '@/api/client'
import { useNoticesStore } from '@/stores/notices'
import AppDialog from '@/components/AppDialog.vue'

const props = defineProps<{ itemId: number }>()
const emit = defineEmits<{ close: [] }>()
const notices = useNoticesStore()

const payload = itemQrPayload(props.itemId)
const imageUrl = ref('')

onMounted(async () => {
  try {
    imageUrl.value = await QRCode.toDataURL(payload, {
      margin: 1,
      width: 220,
      errorCorrectionLevel: 'M',
    })
  } catch (cause) {
    await notices.alert('QR', errorMessage(cause))
    emit('close')
  }
})
</script>

<template>
  <AppDialog title="QR-этикетка" @close="emit('close')">
    <p class="payload">{{ payload }}</p>
    <img v-if="imageUrl" class="code" :src="imageUrl" :alt="payload" />
    <p v-else>Формирование кода…</p>
    <div class="form-actions">
      <button type="button" class="btn" @click="emit('close')">Закрыть</button>
    </div>
  </AppDialog>
</template>

<style scoped lang="scss">
.payload {
  text-align: center;
  word-break: break-all;
}

.code {
  display: block;
  width: 220px;
  height: 220px;
  margin: 12px auto 0;
  background: #fff;
  border-radius: 8px;
}
</style>
