import { parseResponse } from './apiUtils'

export async function fetchOverview() {
  const response = await fetch('/api/v1/stats/overview')
  return parseResponse(response)
}

export async function fetchCurrentTopDomains() {
  const response = await fetch('/api/v1/stats/current-top-domains')
  return parseResponse(response)
}
