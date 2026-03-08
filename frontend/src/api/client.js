import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api'
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const resp = await axios.post('/api/auth/refresh', { refresh_token: refreshToken })
          localStorage.setItem('access_token', resp.data.access_token)
          localStorage.setItem('refresh_token', resp.data.refresh_token)
          originalRequest.headers.Authorization = `Bearer ${resp.data.access_token}`
          return api(originalRequest)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (email, password) => api.post('/auth/login', { email, password })
export const register = (data) => api.post('/auth/register', data)
export const getMe = () => api.get('/users/me')

// Teams
export const fetchTeams = () => api.get('/teams')
export const createTeam = (data) => api.post('/teams', data)

// Users
export const fetchUsers = () => api.get('/users')
export const updateUser = (id, data) => api.put(`/users/${id}`, data)
export const deleteUser = (id) => api.delete(`/users/${id}`)

// Calls
export async function fetchCalls() {
  const { data } = await api.get('/calls')
  return data
}

export async function fetchCallDetail(id) {
  const { data } = await api.get(`/calls/${id}`)
  return data
}

export async function fetchCallStatus(id) {
  const { data } = await api.get(`/calls/${id}/status`)
  return data
}

export async function fetchDashboardStats() {
  const { data } = await api.get('/calls/stats')
  return data
}

export async function uploadAudio(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/calls/upload', form)
  return data
}

export async function deleteCall(id) {
  const { data } = await api.delete(`/calls/${id}`)
  return data
}

export async function assignCall(id, repId) {
  const { data } = await api.patch(`/calls/${id}/assign`, { rep_id: repId })
  return data
}

// Conversions
export async function sendConversion(callId) {
  const { data } = await api.post(`/conversions/send/${callId}`)
  return data
}

export async function fetchConversions(params = {}) {
  const { data } = await api.get('/conversions/status', { params })
  return data
}

// Audit log
export const fetchAuditLog = (params) => api.get('/audit-log', { params })

export function audioUrl(filename) {
  const base = import.meta.env.VITE_API_URL?.replace('/api', '') || ''
  return `${base}/audio/${filename}`
}

// Reports
export async function fetchTrends(params = {}) {
  const { data } = await api.get('/reports/trends', { params })
  return data
}

export async function fetchCampaigns(params = {}) {
  const { data } = await api.get('/reports/campaigns', { params })
  return data
}

export async function fetchReps(params = {}) {
  const { data } = await api.get('/reports/reps', { params })
  return data
}

export function exportCsvUrl(params = {}) {
  const query = new URLSearchParams(params).toString()
  return `/api/reports/export/csv?${query}`
}

export function exportPdfUrl(params = {}) {
  const query = new URLSearchParams(params).toString()
  return `/api/reports/export/pdf?${query}`
}

export default api
