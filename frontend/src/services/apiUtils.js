/**
 * Shared API response parser.
 * Throws with a descriptive message on non-2xx responses.
 */
export async function parseResponse(response) {
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
