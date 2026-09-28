<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
</script>
<template>
  <section class="panel placeholder-page"><h2>Scans</h2><p>Security scan management</p><el-alert v-if="route.query.target" title="扫描目标已带入，尚未创建或执行扫描任务" type="info" :closable="false"><p class="scan-target">{{ route.query.target }}</p></el-alert><el-empty description="Nmap / Nuclei 扫描配置、状态、实时日志与历史记录将在后续接入" /></section>
</template>
