async function parseResponse(response) {
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the generic message when the server does not return JSON.
    }
    throw new Error(message)
  }
  return response.json()
}

export async function runDomainAssessment(domain, fromDate, toDate, modelId = null) {
  const response = await fetch(`/api/v1/domains/${encodeURIComponent(domain)}/assessment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: fromDate,
      to: toDate,
      mode: 'quick',
      model_id: modelId
    })
  })
  return parseResponse(response)
}

export async function fetchDomainAssessments(domain, limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) })
  const response = await fetch(`/api/v1/domains/${encodeURIComponent(domain)}/assessments?${params}`)
  return parseResponse(response)
}

export async function fetchVolatileDomains(limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) })
  const response = await fetch(`/api/v1/assessments/volatile-domains?${params}`)
  return parseResponse(response)
}
