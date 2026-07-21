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

export const reportApi = {
  async getReports() {
    const { data } = await http.get('/report/generate/')
    return data
  },

  async refreshReports() {
    const { data } = await http.post('/report/generate/')
    return data
  }
}
