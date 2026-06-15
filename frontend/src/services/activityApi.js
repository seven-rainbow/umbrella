import { parseResponse } from './apiUtils'

export async function fetchActivity(domain, fromDate, toDate) {
  const params = new URLSearchParams({ from: fromDate, to: toDate })
  const response = await fetch(`/api/v1/domains/${encodeURIComponent(domain)}/activity?${params}`)
  return parseResponse(response)
}
