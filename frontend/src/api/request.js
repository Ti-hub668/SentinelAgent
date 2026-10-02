import i18n from '../i18n'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT)
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: configuredTimeout > 0 ? configuredTimeout : 15000,
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (axios.isCancel(error)) return Promise.reject(error)
    const detail = error.response?.data?.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item.msg).filter(Boolean).join(i18n.global.locale.value === 'zh-CN' ? '；' : '; ') || i18n.global.t('feedback.requestInvalid')
        : error.code === 'ECONNABORTED'
          ? i18n.global.t('feedback.requestTimeout')
          : error.response ? i18n.global.t('feedback.requestFailed', { status: error.response.status }) : i18n.global.t('feedback.requestDisconnected')
    if (!error.config?.silent) ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
