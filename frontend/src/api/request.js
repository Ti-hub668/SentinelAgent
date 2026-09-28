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
        ? detail.map((item) => item.msg).filter(Boolean).join('；') || '请求参数有误'
        : error.code === 'ECONNABORTED'
          ? '请求超时，请稍后重试'
          : error.response ? `请求失败（${error.response.status}）` : '无法连接服务，请检查后端是否启动'
    if (!error.config?.silent) ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
