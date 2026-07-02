export const CLIENT_ID_KEY = 'binteumsaiClientId'
export const CSRF_TOKEN_KEY = 'binteumsaiCsrfToken'

export function getClientId() {
  let clientId = localStorage.getItem(CLIENT_ID_KEY)
  if (!clientId) {
    clientId = crypto.randomUUID()
    localStorage.setItem(CLIENT_ID_KEY, clientId)
  }
  return clientId
}

export function getCsrfToken() {
  return localStorage.getItem(CSRF_TOKEN_KEY) || ''
}

export function setCsrfToken(token) {
  if (token) {
    localStorage.setItem(CSRF_TOKEN_KEY, token)
  }
}

export function clearCsrfToken() {
  localStorage.removeItem(CSRF_TOKEN_KEY)
}

export function getLocalDateString(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
