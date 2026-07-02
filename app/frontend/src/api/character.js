import axios from 'axios'
import { getClientId, getCsrfToken } from './client.js'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  config.headers['X-Binteumsai-Client-Id'] = getClientId()
  const csrfToken = getCsrfToken()
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

export const characterApi = {
  async getPreference() {
    const { data } = await http.get('/characters/preference/')
    return data.preference
  },

  async savePreference(payload) {
    const { data } = await http.post('/characters/preference/', payload)
    return data.preference
  },
}
