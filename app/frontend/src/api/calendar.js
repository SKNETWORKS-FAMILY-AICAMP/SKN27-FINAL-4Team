import axios from 'axios'
import { getClientId } from './client.js'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  config.headers['X-Binteumsai-Client-Id'] = getClientId()
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
}

