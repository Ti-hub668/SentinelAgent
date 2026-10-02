<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

import { STORAGE_KEY } from '../../i18n'

const { locale, t } = useI18n()

const currentLanguage = computed({
  get() {
    return locale.value
  },

  set(value) {
    locale.value = value

    localStorage.setItem(
      STORAGE_KEY,
      value,
    )

    document.documentElement.lang = value

    ElMessage.success(
      t('settings.saved'),
    )
  },
})
</script>

<template>
  <section class="settings-page">
    <div class="page-heading">
      <div>
        <h2>{{ t('settings.title') }}</h2>

        <p>
          {{ t('settings.description') }}
        </p>
      </div>
    </div>

    <el-card
      class="settings-card"
      shadow="never"
    >
      <template #header>
        <div class="card-header">
          {{ t('settings.appearance') }}
        </div>
      </template>

      <div class="setting-row">
        <div class="setting-info">
          <div class="setting-title">
            {{ t('settings.language') }}
          </div>

          <div class="setting-description">
            {{
              t(
                'settings.languageDescription',
              )
            }}
          </div>
        </div>

        <el-select
          v-model="currentLanguage"
          class="language-select"
        >
          <el-option
            :label="
              t('settings.chinese')
            "
            value="zh-CN"
          />

          <el-option
            :label="
              t('settings.english')
            "
            value="en-US"
          />
        </el-select>
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-heading h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.page-heading p {
  margin: 8px 0 0;
  color: var(
    --el-text-color-secondary
  );
}

.settings-card {
  border-radius: 10px;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.setting-info {
  min-width: 0;
}

.setting-title {
  font-size: 15px;
  font-weight: 500;
}

.setting-description {
  margin-top: 6px;
  color: var(
    --el-text-color-secondary
  );
  font-size: 13px;
}

.language-select {
  width: 200px;
  flex-shrink: 0;
}

@media (
  max-width: 768px
) {
  .setting-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .language-select {
    width: 100%;
  }
}
</style>