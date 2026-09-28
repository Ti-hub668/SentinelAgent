import request from './request'

export const getHealth = (config = {}) =>
  request.get('/health', {
    ...config,
    baseURL: '',
  })

export const getAssets = (config = {}) =>
  request.get('/assets', config)

export const createAsset = (data, config = {}) =>
  request.post('/assets', data, config)

export const getScans = (config = {}) =>
  request.get('/scans', config)

export const getScan = (scanId, config = {}) =>
  request.get(`/scans/${scanId}`, config)

export const createScan = (data, config = {}) =>
  request.post('/scans', data, config)

export const getFindings = (config = {}) =>
  request.get('/findings', config)

export const getFinding = (findingId, config = {}) =>
  request.get(`/findings/${findingId}`, config)

export { default as request } from './request'