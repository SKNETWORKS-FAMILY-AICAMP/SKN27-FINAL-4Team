export const CLIENT_ID_KEY = 'binteumsaiClientId'
export const CSRF_TOKEN_KEY = 'binteumsaiCsrfToken'

// 2026-07-23: crypto.randomUUID는 보안 컨텍스트(HTTPS·localhost) 전용이라
// http://IP 배포(EC2)에선 undefined → 모든 API 요청이 인터셉터에서 즉사했다
// ("백엔드 먹통"으로 보인 실체). getRandomValues는 비보안에서도 동작하므로 폴백.
function generateUuid() {
  if (crypto.randomUUID) return crypto.randomUUID()
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  bytes[6] = (bytes[6] & 0x0f) | 0x40   // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80   // variant
  const hex = [...bytes].map(b => b.toString(16).padStart(2, '0'))
  return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10, 16).join('')}`
}

export function getClientId() {
  let clientId = localStorage.getItem(CLIENT_ID_KEY)
  if (!clientId) {
    clientId = generateUuid()
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
