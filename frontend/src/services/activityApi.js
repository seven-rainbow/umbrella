export async function fetchActivity(domain, fromDate, toDate) {
  const params = new URLSearchParams({ from: fromDate, to: toDate })
  const response = await fetch(`/api/v1/domains/${encodeURIComponent(domain)}/activity?${params}`)
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

