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

  async getTodayCheckin() {
    const { data } = await http.get('/checkin/today/')
    return data?.data ?? data
  },

  async saveActionFeedback(checkinId, actionId, helpfulness) {
    const { data } = await http.post(`/checkin/${checkinId}/feedback/`, {
      action_id: actionId,
      completed: true,
      helpfulness,
    })
    return data?.data ?? data
  },

  async refreshReports() {
    const { data } = await http.post('/report/generate/')
    return data
  }
}
