<script setup lang="ts">
import { onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import ConnectScreen from '@/components/ConnectScreen.vue'
import WarehouseApp from '@/components/WarehouseApp.vue'
import NoticeHost from '@/components/NoticeHost.vue'

const settings = useSettingsStore()

onMounted(() => {
  void settings.connect()
})
</script>

<template>
  <WarehouseApp v-if="settings.phase === 'ready'" />
  <ConnectScreen v-else />
  <NoticeHost />
</template>
