import axios from 'axios'
import { clearCsrfToken, getClientId, getCsrfToken, setCsrfToken } from './client.js'

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

export const userApi = {
  async getCurrentUser() {
    const { data } = await http.get('/user/me/')
    if (data.csrf_token) {
      setCsrfToken(data.csrf_token)
    }
    if (data.user?.csrf_token) {
      setCsrfToken(data.user.csrf_token)
    }
    return data
  },

  async getSocialLoginProviders() {
    const { data } = await http.get('/user/social-login/providers/')
    return data.providers
  },

  async getSocialLoginUrl(provider, next = '/home') {
    const { data } = await http.get(`/user/social-login/${provider}/url/`, {
      params: { next },
    })
    return data
  },

  async completeSocialLogin(provider, payload) {
    const { data } = await http.post(`/user/social-login/${provider}/callback/`, payload)
    setCsrfToken(data.csrf_token)
    return data
  },

  async socialLogin(provider) {
    const { data } = await http.post('/user/social-login/', { provider })
    setCsrfToken(data.csrf_token)
    return data
  },

  async logout() {
    const { data } = await http.post('/user/logout/')
    if (data.csrf_token) {
      setCsrfToken(data.csrf_token)
    } else {
      clearCsrfToken()
    }
    return data
  },

  async getProfile() {
    const { data } = await http.get('/user/profile/')
    return data.profile
  },

  async saveProfile(payload) {
    const { data } = await http.put('/user/profile/', payload)
    return data.profile
  },
}
