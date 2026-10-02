<script setup>
import { useI18n } from 'vue-i18n'
const { t, locale } = useI18n()
</script>

<template>
  <section class="panel placeholder-page"><h2>{{ t('interface.discovery') }}</h2><p>{{ t('interface.assetDiscoveryAndServiceInventory') }}</p><el-empty :description="t('interface.openPortsServicesProductVersionsAndWebTargetsWillBeAddedLater')" /></section>
</template>
