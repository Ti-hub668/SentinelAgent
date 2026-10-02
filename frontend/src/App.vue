<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCN from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

const { locale } = useI18n()
const elementLocale = computed(() => locale.value === 'zh-CN' ? zhCN : en)
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>
