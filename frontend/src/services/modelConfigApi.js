import { parseResponse } from './apiUtils'

export async function fetchModelConfigs() {
  const response = await fetch('/api/v1/model-configs')
  return parseResponse(response)
}

export async function createProvider(payload) {
  const response = await fetch('/api/v1/model-configs/providers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return parseResponse(response)
}

export async function createModel(payload) {
  const response = await fetch('/api/v1/model-configs/models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return parseResponse(response)
}

export async function setDefaultModel(modelId) {
  const response = await fetch('/api/v1/model-configs/default', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId })
  })
  return parseResponse(response)
}

export async function testModelConnection(modelId) {
  const response = await fetch(`/api/v1/model-configs/models/${encodeURIComponent(modelId)}/test`, {
    method: 'POST'
  })
  return parseResponse(response)
}
