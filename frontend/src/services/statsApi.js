export async function fetchOverview() {
  const response = await fetch('/api/v1/stats/overview')
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

export async function fetchCurrentTopDomains() {
  const response = await fetch('/api/v1/stats/current-top-domains')
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
