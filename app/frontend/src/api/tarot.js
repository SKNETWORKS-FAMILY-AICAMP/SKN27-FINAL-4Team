import axios from 'axios'
import { getClientId, getCsrfToken, getLocalDateString } from './client.js'

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

export const tarotApi = {
  async getDailyMajor(date = getLocalDateString()) {
    const { data } = await http.get('/tarot/daily-major/', {
      params: { date },
    })
    return data
  },

  async createReading(payload) {
    const { data } = await http.post('/tarot/readings/', {
      date: getLocalDateString(),
      ...payload,
    })
    return data
  },
}
