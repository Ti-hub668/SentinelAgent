import request from './request'

export const getHealth = (config = {}) =>
  request.get('/health', {
    ...config,
    baseURL: '',
  })

export const getAssets = (config = {}) =>
  request.get('/assets', config)

export const getScans = (config = {}) =>
  request.get('/scans', config)

export const getFindings = (config = {}) =>
  request.get('/findings', config)

export { default as request } from './request'