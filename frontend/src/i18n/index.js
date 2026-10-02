import { watch } from 'vue'
import { createI18n } from 'vue-i18n'

import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

export const STORAGE_KEY = 'sentinelagent-language'

const saved = localStorage.getItem(STORAGE_KEY)
const savedLanguage = ['zh-CN', 'en-US'].includes(saved) ? saved : 'zh-CN'

const i18n = createI18n({
  legacy: false,
  locale: savedLanguage,
  fallbackLocale: 'en-US',

  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

watch(i18n.global.locale, (value) => {
  document.documentElement.lang = value
  localStorage.setItem(STORAGE_KEY, value)
}, { immediate: true })

export default i18n