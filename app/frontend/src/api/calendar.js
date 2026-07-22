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

export const calendarApi = {
  async getMonth(year, month) {
    const { data } = await http.get('/calendar/month/', {
      params: { year, month },
    })
    return data
  },

  async getDay(date) {
    const { data } = await http.get('/calendar/day/', {
      params: { date },
    })
    return data
  },

  async saveActionFeedback(checkinId, actionId, helpfulness) {
    const { data } = await http.post(`/checkin/${checkinId}/feedback/`, {
      action_id: actionId,
      completed: true,
      helpfulness,
    })
    return data?.data ?? data
  },
}

