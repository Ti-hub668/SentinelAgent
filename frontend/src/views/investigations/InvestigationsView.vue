<template>
  <section class="panel placeholder-page"><h2>AI Investigations</h2><p>LangGraph security investigation workflow</p><el-empty description="AI 调查工作流将在后续接入" /><div class="feature-tags"><el-tag v-for="stage in ['Context Bundle', 'Triage', 'RAG', 'Threat Intel', 'Evidence Assessment', 'Risk Synthesis', 'Grounding', 'Final Verdict', 'AI Reason']" :key="stage" effect="plain">{{ stage }}</el-tag></div></section>
</template>
