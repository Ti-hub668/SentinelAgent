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

export const getDiscovery = (config = {}) =>
  request.get('/scans/discovery', config)

export const getScan = (scanId, config = {}) =>
  request.get(`/scans/${scanId}`, config)

export const createScan = (data, config = {}) =>
  request.post('/scans', data, config)

export const getFindings = (config = {}) =>
  request.get('/findings', config)

export const getFinding = (findingId, config = {}) =>
  request.get(`/findings/${findingId}`, config)

export const startInvestigation = (
  findingId,
  config = {},
) =>
  request.post(
    `/agent/investigate/${findingId}`,
    null,
    config,
  )

export const getInvestigationRuns = (
  config = {},
) =>
  request.get(
    '/agent/runs',
    config,
  )

export const getInvestigationRun = (
  runId,
  config = {},
) =>
  request.get(
    `/agent/runs/${runId}`,
    config,
  )

export const getInvestigationTrace = (
  runId,
  config = {},
) =>
  request.get(
    `/agent/runs/${runId}/trace`,
    config,
  )

export const approveInvestigationAction = (
  runId,
  requestIndex,
  data,
  config = {},
) =>
  request.post(
    `/agent/runs/${runId}/approvals/${requestIndex}/approve`,
    data,
    config,
  )

export const rejectInvestigationAction = (
  runId,
  requestIndex,
  data,
  config = {},
) =>
  request.post(
    `/agent/runs/${runId}/approvals/${requestIndex}/reject`,
    data,
    config,
  )

export const executeInvestigationTools = (
  runId,
  config = {},
) =>
  request.post(
    `/agent/runs/${runId}/execute`,
    null,
    config,
  )

export const reconcileInvestigationExecutions = (
  runId,
  config = {},
) =>
  request.post(
    `/agent/runs/${runId}/reconcile`,
    null,
    config,
  )

export { default as request } from './request'