# Phase 3: Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update the React frontend from Call Monitor's old sentiment/review UI to a CTM call scoring dashboard.

**Architecture:** Update existing React components to consume the already-built backend API (no backend changes). Remove dead Twilio/sentiment/review code. Add ScoreDisplay component for call detail. Update Reports to use campaigns/reps endpoints.

**Tech Stack:** React 18, Vite, Tailwind CSS, Recharts, Axios

---

### Task 1: Fix Vite Config and Clean API Client

**Files:**
- Modify: `frontend/vite.config.js`
- Modify: `frontend/src/api/client.js`

**Step 1: Fix vite proxy port from 8000 to 8002**

Update `frontend/vite.config.js`:
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8002',
      '/audio': 'http://localhost:8002',
    },
  },
})
```

**Step 2: Update API client — remove dead methods, add new ones**

Replace `frontend/src/api/client.js` with:
```js
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

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

// Audit log
export const fetchAuditLog = (params) => api.get('/audit-log', { params })

export function audioUrl(filename) {
  return `/audio/${filename}`
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
```

Key changes:
- Removed: `fetchCallScores`, `fetchCallReview`, `submitReview`, `dialCall`, `getTwilioToken`, `fetchTeamComparison`, `fetchCompliance`
- Added: `assignCall`, `fetchCampaigns`, `fetchReps`
- `uploadAudio` no longer takes `title` param (Call model has no title)

**Step 3: Commit**

```bash
git add frontend/vite.config.js frontend/src/api/client.js
git commit -m "fix: update vite proxy port and clean API client for CTM scoring"
```

---

### Task 2: Update App.jsx — Remove CallDialer, Fix Branding

**Files:**
- Modify: `frontend/src/App.jsx`

**Step 1: Update App.jsx**

Replace `frontend/src/App.jsx` with:
```jsx
import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Login from './components/Login'
import ProtectedRoute from './components/ProtectedRoute'
import InactivityTimer from './components/InactivityTimer'
import Dashboard from './components/Dashboard'
import CallList from './components/CallList'
import CallDetail from './components/CallDetail'
import AudioUpload from './components/AudioUpload'
import UserManagement from './components/UserManagement'
import TeamManagement from './components/TeamManagement'
import AuditLog from './components/AuditLog'
import Reports from './components/Reports'

function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const roleColors = {
    admin: 'bg-purple-200 text-purple-800',
    supervisor: 'bg-blue-200 text-blue-800',
    rep: 'bg-green-200 text-green-800',
  }

  return (
    <nav className="bg-indigo-700 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="text-xl font-bold tracking-tight">CTM Scorer</Link>
          <div className="flex gap-6 text-sm font-medium">
            <Link to="/" className="hover:text-indigo-200">Dashboard</Link>
            <Link to="/calls" className="hover:text-indigo-200">Calls</Link>
            <Link to="/upload" className="hover:text-indigo-200">Upload</Link>
            <Link to="/reports" className="hover:text-indigo-200">Reports</Link>
            {user.role === 'admin' && (
              <>
                <Link to="/users" className="hover:text-indigo-200">Users</Link>
                <Link to="/teams" className="hover:text-indigo-200">Teams</Link>
                <Link to="/audit-log" className="hover:text-indigo-200">Audit Log</Link>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span>{user.name}</span>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${roleColors[user.role]}`}>
            {user.role}
          </span>
          <button onClick={handleLogout} className="text-indigo-200 hover:text-white ml-2">
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <InactivityTimer />

      <main className="max-w-7xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/calls" element={<ProtectedRoute><CallList /></ProtectedRoute>} />
          <Route path="/calls/:id" element={<ProtectedRoute><CallDetail /></ProtectedRoute>} />
          <Route path="/upload" element={<ProtectedRoute><AudioUpload /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute roles={['admin']}><UserManagement /></ProtectedRoute>} />
          <Route path="/teams" element={<ProtectedRoute roles={['admin']}><TeamManagement /></ProtectedRoute>} />
          <Route path="/audit-log" element={<ProtectedRoute roles={['admin']}><AuditLog /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  )
}
```

Key changes:
- Removed: `CallDialer` import and `/call` route
- Renamed: "Call Monitor" → "CTM Scorer"
- Fixed: role colors `worker` → `rep`
- Removed: "Call" nav link

**Step 2: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: update App.jsx - rebrand to CTM Scorer, remove CallDialer"
```

---

### Task 3: Update Dashboard Component

**Files:**
- Modify: `frontend/src/components/Dashboard.jsx`

**Step 1: Rewrite Dashboard for CTM scoring stats**

Replace `frontend/src/components/Dashboard.jsx` with:
```jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { fetchDashboardStats } from '../api/client'

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 text-center">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color || ''}`}>{value}</p>
    </div>
  )
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-gray-400">-</span>
  const color =
    score >= 8 ? 'text-green-600' :
    score >= 6 ? 'text-yellow-600' :
    score >= 4 ? 'text-orange-600' : 'text-red-600'
  return <span className={`font-medium ${color}`}>{score.toFixed(1)}</span>
}

function StatusBadge({ status }) {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[status] || 'bg-gray-100'}`}>
      {status}
    </span>
  )
}

function NavWidget({ to, title, description, accent }) {
  return (
    <Link to={to} className="bg-white rounded-xl shadow hover:shadow-md transition-shadow p-6 flex flex-col gap-2 border-l-4" style={{ borderLeftColor: accent }}>
      <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
      <p className="text-sm text-gray-500">{description}</p>
    </Link>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDashboardStats().then(setStats).catch(e => setError(e.message))
  }, [])

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!stats) return <p className="text-gray-500">Loading...</p>

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Welcome back, {user.name}</h1>
        <p className="text-sm text-gray-500 mt-1">Here's an overview of your call scoring activity.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total Calls" value={stats.total_calls} />
        <StatCard label="Completed" value={stats.completed_calls} />
        <StatCard label="Avg Rep Score" value={stats.avg_rep_score != null ? stats.avg_rep_score.toFixed(1) : 'N/A'} color="text-indigo-600" />
        <StatCard label="Avg Lead Score" value={stats.avg_lead_score != null ? stats.avg_lead_score.toFixed(1) : 'N/A'} color="text-emerald-600" />
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Quick Access</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <NavWidget to="/calls" title="Calls" description="Browse and review all scored calls" accent="#6366f1" />
          <NavWidget to="/upload" title="Upload" description="Upload audio files for transcription and scoring" accent="#8b5cf6" />
          <NavWidget to="/reports" title="Reports" description="View trends, campaign metrics, and export data" accent="#10b981" />
          {user.role === 'admin' && (
            <>
              <NavWidget to="/users" title="Users" description="Manage user accounts and role assignments" accent="#f59e0b" />
              <NavWidget to="/teams" title="Teams" description="Create and manage teams" accent="#f97316" />
              <NavWidget to="/audit-log" title="Audit Log" description="Review system activity and access history" accent="#ef4444" />
            </>
          )}
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Recent Calls</h2>
        {stats.recent_calls.length === 0 ? (
          <p className="text-gray-500">No calls yet. <Link to="/upload" className="text-indigo-600 underline">Upload one</Link>.</p>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left">
                <tr>
                  <th className="px-4 py-2">Date</th>
                  <th className="px-4 py-2">Campaign</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Rep Score</th>
                  <th className="px-4 py-2">Lead Score</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_calls.map(c => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <Link to={`/calls/${c.id}`} className="text-indigo-600 hover:underline">
                        {c.call_date ? new Date(c.call_date).toLocaleDateString() : '-'}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-gray-600">{c.campaign_name || '-'}</td>
                    <td className="px-4 py-2"><StatusBadge status={c.status} /></td>
                    <td className="px-4 py-2"><ScoreBadge score={c.rep_score} /></td>
                    <td className="px-4 py-2"><ScoreBadge score={c.lead_score} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
```

Key changes:
- Stats: Total Calls, Completed, Avg Rep Score, Avg Lead Score (removed sentiment/review/flagged)
- Recent calls table: Date, Campaign, Status, Rep Score, Lead Score (removed title/rating/review)
- Uses `call_date` instead of `date`, `campaign_name` instead of `title`
- Removed "Call a Patient" nav widget
- Updated descriptions

**Step 2: Commit**

```bash
git add frontend/src/components/Dashboard.jsx
git commit -m "feat: update Dashboard for CTM scoring stats"
```

---

### Task 4: Update CallList Component

**Files:**
- Modify: `frontend/src/components/CallList.jsx`

**Step 1: Rewrite CallList for CTM scoring fields**

Replace `frontend/src/components/CallList.jsx` with:
```jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchCalls, deleteCall } from '../api/client'

function StatusBadge({ status }) {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[status] || 'bg-gray-100'}`}>
      {status}
    </span>
  )
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-gray-400">-</span>
  const color =
    score >= 8 ? 'text-green-600' :
    score >= 6 ? 'text-yellow-600' :
    score >= 4 ? 'text-orange-600' : 'text-red-600'
  return <span className={`font-medium ${color}`}>{score.toFixed(1)}</span>
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function CallList() {
  const [calls, setCalls] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [campaignFilter, setCampaignFilter] = useState('')
  const [sortField, setSortField] = useState('call_date')
  const [sortDir, setSortDir] = useState('desc')

  const load = () => {
    setLoading(true)
    fetchCalls().then(setCalls).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (id) => {
    if (!confirm('Delete this call?')) return
    await deleteCall(id)
    load()
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const campaigns = [...new Set(calls.map(c => c.campaign_name).filter(Boolean))]

  const filtered = calls
    .filter(c => !statusFilter || c.status === statusFilter)
    .filter(c => !campaignFilter || c.campaign_name === campaignFilter)

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortField]
    const bv = b[sortField]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'asc' ? cmp : -cmp
  })

  const SortHeader = ({ field, children }) => (
    <th className="px-4 py-2 cursor-pointer select-none hover:text-indigo-600" onClick={() => handleSort(field)}>
      {children} {sortField === field ? (sortDir === 'asc' ? '▲' : '▼') : ''}
    </th>
  )

  if (loading) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">All Calls</h1>
        <Link to="/upload" className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700">
          Upload New
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="border rounded px-2 py-1 text-sm">
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select value={campaignFilter} onChange={e => setCampaignFilter(e.target.value)}
          className="border rounded px-2 py-1 text-sm">
          <option value="">All Campaigns</option>
          {campaigns.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {sorted.length === 0 ? (
        <p className="text-gray-500">No calls found.</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <SortHeader field="call_date">Date</SortHeader>
                <th className="px-4 py-2">Caller</th>
                <SortHeader field="campaign_name">Campaign</SortHeader>
                <SortHeader field="duration">Duration</SortHeader>
                <SortHeader field="rep_score">Rep Score</SortHeader>
                <SortHeader field="lead_score">Lead Score</SortHeader>
                <th className="px-4 py-2">Rep</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(c => (
                <tr key={c.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <Link to={`/calls/${c.id}`} className="text-indigo-600 hover:underline">
                      {c.call_date ? new Date(c.call_date).toLocaleDateString() : '-'}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-gray-600">{c.caller_phone || '-'}</td>
                  <td className="px-4 py-2">{c.campaign_name || '-'}</td>
                  <td className="px-4 py-2">{formatDuration(c.duration)}</td>
                  <td className="px-4 py-2"><ScoreBadge score={c.rep_score} /></td>
                  <td className="px-4 py-2"><ScoreBadge score={c.lead_score} /></td>
                  <td className="px-4 py-2 text-gray-600">{c.rep_name || '-'}</td>
                  <td className="px-4 py-2"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:text-red-700 text-xs">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

Key changes:
- Columns: Date, Caller, Campaign, Duration, Rep Score, Lead Score, Rep, Status
- Added filters: status dropdown, campaign dropdown
- Added sortable column headers (click to sort)
- Removed: Title, Sentiment, Rating, Review Status columns
- Uses `call_date`, `caller_phone`, `campaign_name`, `rep_name`, `rep_score`, `lead_score`

**Step 2: Commit**

```bash
git add frontend/src/components/CallList.jsx
git commit -m "feat: update CallList with CTM fields, filters, and sorting"
```

---

### Task 5: Create ScoreDisplay Component and Update CallDetail

**Files:**
- Create: `frontend/src/components/ScoreDisplay.jsx`
- Modify: `frontend/src/components/CallDetail.jsx`

**Step 1: Create ScoreDisplay component**

Create `frontend/src/components/ScoreDisplay.jsx`:
```jsx
function ScoreCircle({ score, label, color }) {
  if (score == null) return null
  const ringColor =
    score >= 8 ? 'border-green-400' :
    score >= 6 ? 'border-yellow-400' :
    score >= 4 ? 'border-orange-400' : 'border-red-400'
  const textColor =
    score >= 8 ? 'text-green-600' :
    score >= 6 ? 'text-yellow-600' :
    score >= 4 ? 'text-orange-600' : 'text-red-600'

  return (
    <div className="text-center">
      <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full border-4 ${ringColor}`}>
        <span className={`text-xl font-bold ${textColor}`}>{score.toFixed(1)}</span>
      </div>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}

function SubScore({ label, value }) {
  if (value == null) return null
  const barWidth = `${(value / 10) * 100}%`
  const color =
    value >= 8 ? 'bg-green-400' :
    value >= 6 ? 'bg-yellow-400' :
    value >= 4 ? 'bg-orange-400' : 'bg-red-400'

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-28 text-gray-600 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: barWidth }} />
      </div>
      <span className="w-8 text-right text-gray-700 font-medium">{value.toFixed(1)}</span>
    </div>
  )
}

export default function ScoreDisplay({ score }) {
  if (!score) return null

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Rep Score */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-base font-semibold text-gray-700 mb-4">Rep Score</h3>
        <div className="flex items-start gap-6">
          <ScoreCircle score={score.rep_score} label="Overall" />
          <div className="flex-1 space-y-2">
            <SubScore label="Tone" value={score.rep_tone} />
            <SubScore label="Call Steering" value={score.rep_steering} />
            <SubScore label="Service" value={score.rep_service} />
          </div>
        </div>
        {score.rep_reasoning && (
          <p className="text-sm text-gray-500 mt-4 border-t pt-3">{score.rep_reasoning}</p>
        )}
      </div>

      {/* Lead Score */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-base font-semibold text-gray-700 mb-4">Lead Score</h3>
        <div className="flex items-start gap-6">
          <ScoreCircle score={score.lead_score} label="Overall" />
          <div className="flex-1 space-y-2">
            <SubScore label="Service Match" value={score.lead_service_match} />
            <SubScore label="Insurance" value={score.lead_insurance} />
            <SubScore label="Intent" value={score.lead_intent} />
          </div>
        </div>
        {score.lead_reasoning && (
          <p className="text-sm text-gray-500 mt-4 border-t pt-3">{score.lead_reasoning}</p>
        )}
      </div>
    </div>
  )
}
```

**Step 2: Rewrite CallDetail component**

Replace `frontend/src/components/CallDetail.jsx` with:
```jsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchCallDetail, fetchCallStatus, deleteCall, audioUrl } from '../api/client'
import ScoreDisplay from './ScoreDisplay'

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function MetaItem({ label, value }) {
  if (!value) return null
  return (
    <div>
      <span className="text-xs text-gray-500">{label}</span>
      <p className="text-sm font-medium text-gray-800">{value}</p>
    </div>
  )
}

export default function CallDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [call, setCall] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let interval
    const load = async () => {
      try {
        const data = await fetchCallDetail(id)
        setCall(data)
        setLoading(false)
        if (['pending', 'processing'].includes(data.status)) {
          interval = setInterval(async () => {
            const status = await fetchCallStatus(id)
            if (status.status !== data.status) {
              const updated = await fetchCallDetail(id)
              setCall(updated)
              if (updated.status === 'completed' || updated.status === 'failed') {
                clearInterval(interval)
              }
            }
          }, 3000)
        }
      } catch (e) {
        setError(e.message)
        setLoading(false)
      }
    }
    load()
    return () => clearInterval(interval)
  }, [id])

  const handleDelete = async () => {
    if (!confirm('Delete this call?')) return
    await deleteCall(id)
    navigate('/calls')
  }

  if (loading) return <p className="text-gray-500">Loading...</p>
  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!call) return <p className="text-red-600">Call not found</p>

  const statusColors = {
    pending: 'text-yellow-600',
    processing: 'text-blue-600',
    completed: 'text-green-600',
    failed: 'text-red-600',
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            Call {call.call_date ? new Date(call.call_date).toLocaleDateString() : `#${call.id}`}
          </h1>
          <p className="text-sm text-gray-500">
            <span className={statusColors[call.status]}>{call.status}</span>
            {call.duration && ` · ${formatTime(call.duration)}`}
            {call.source_type && ` · ${call.source_type}`}
          </p>
        </div>
        <button onClick={handleDelete} className="text-red-500 hover:text-red-700 text-sm border border-red-300 px-3 py-1 rounded">
          Delete
        </button>
      </div>

      {call.error_message && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-6 text-sm">
          {call.error_message}
        </div>
      )}

      {['pending', 'processing'].includes(call.status) && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 p-4 rounded mb-6 flex items-center gap-3">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          Processing... This may take a minute.
        </div>
      )}

      {/* Call Metadata */}
      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <h2 className="text-base font-semibold text-gray-700 mb-3">Call Details</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          <MetaItem label="Caller" value={call.caller_phone} />
          <MetaItem label="Receiving Number" value={call.receiving_number} />
          <MetaItem label="Campaign" value={call.campaign_name} />
          <MetaItem label="Keyword" value={call.keyword} />
          <MetaItem label="Landing Page" value={call.landing_page_url} />
          <MetaItem label="GCLID" value={call.gclid} />
          <MetaItem label="Rep" value={call.rep_name} />
          <MetaItem label="CTM Call ID" value={call.ctm_call_id} />
        </div>
        {call.conversion && (
          <div className="mt-3 pt-3 border-t">
            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
              call.conversion.status === 'sent' ? 'bg-green-100 text-green-800' :
              call.conversion.status === 'failed' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              Conversion: {call.conversion.status}
            </span>
          </div>
        )}
      </div>

      {/* Audio Player */}
      {call.audio_filename && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-2">Audio</h2>
          <audio controls className="w-full" src={audioUrl(call.audio_filename)} />
        </div>
      )}

      {/* Scores */}
      {call.score && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">Scores</h2>
          <ScoreDisplay score={call.score} />
        </div>
      )}

      {/* Transcript */}
      {call.transcript && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">Transcript</h2>
          <div className="bg-white rounded-lg shadow p-4 max-h-96 overflow-y-auto space-y-3">
            {call.transcript.segments?.length > 0 ? (
              call.transcript.segments.map((seg, i) => {
                const prevSpeaker = i > 0 ? call.transcript.segments[i - 1].speaker : null
                const showSpeaker = seg.speaker && seg.speaker !== prevSpeaker
                const firstSpeaker = call.transcript.segments.find(s => s.speaker)?.speaker
                const isFirstSpeaker = seg.speaker === firstSpeaker
                return (
                  <div key={i} className="flex gap-3 text-sm">
                    <span className="font-mono text-gray-400 whitespace-nowrap text-xs mt-0.5">
                      {formatTime(seg.start)}
                    </span>
                    <div>
                      {showSpeaker && (
                        <span className={`text-xs font-semibold mr-1 ${
                          isFirstSpeaker ? 'text-indigo-600' : 'text-emerald-600'
                        }`}>
                          {seg.speaker}:
                        </span>
                      )}
                      <span>{seg.text}</span>
                    </div>
                  </div>
                )
              })
            ) : (
              <p className="text-sm whitespace-pre-wrap">{call.transcript.full_text}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

Key changes:
- Removed: TonalityChart, ScoreCard, ReviewPanel imports (all dead code)
- Added: ScoreDisplay component for Rep Score + Lead Score breakdown
- Added: Call metadata section (caller, campaign, keyword, landing page, GCLID, rep, CTM ID)
- Added: Conversion status badge
- Removed: tonality analysis section, quality score section, review panel
- Removed: Twilio-specific status checking (`connecting`, `in_progress`)
- Header shows date instead of title

**Step 3: Commit**

```bash
git add frontend/src/components/ScoreDisplay.jsx frontend/src/components/CallDetail.jsx
git commit -m "feat: add ScoreDisplay component, rewrite CallDetail for CTM scoring"
```

---

### Task 6: Update Reports Component

**Files:**
- Modify: `frontend/src/components/Reports.jsx`

**Step 1: Rewrite Reports for CTM scoring**

Replace `frontend/src/components/Reports.jsx` with:
```jsx
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { fetchTrends, fetchCampaigns, fetchReps, exportCsvUrl, exportPdfUrl } from '../api/client'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts'

const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
]

function formatDate(d) {
  return d.toISOString().split('T')[0]
}

export default function Reports() {
  const { user } = useAuth()
  const [startDate, setStartDate] = useState(() => formatDate(new Date(Date.now() - 90 * 86400000)))
  const [endDate, setEndDate] = useState(() => formatDate(new Date()))
  const [period, setPeriod] = useState('weekly')
  const [trends, setTrends] = useState(null)
  const [campaigns, setCampaigns] = useState(null)
  const [reps, setReps] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { start_date: startDate, end_date: endDate }
      const trendsData = await fetchTrends({ ...params, period })
      setTrends(trendsData)

      const campaignData = await fetchCampaigns(params)
      setCampaigns(campaignData)

      if (user.role !== 'rep') {
        const repData = await fetchReps(params)
        setReps(repData)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load reports')
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, period, user.role])

  useEffect(() => { loadData() }, [loadData])

  const applyPreset = (days) => {
    setEndDate(formatDate(new Date()))
    setStartDate(formatDate(new Date(Date.now() - days * 86400000)))
  }

  const handleExport = (format) => {
    const params = { start_date: startDate, end_date: endDate }
    const token = localStorage.getItem('access_token')
    const url = format === 'csv' ? exportCsvUrl(params) : exportPdfUrl(params)
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(resp => resp.blob())
      .then(blob => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `report-${endDate}.${format}`
        a.click()
        URL.revokeObjectURL(a.href)
      })
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading reports...</div>
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Reports & Analytics</h1>
        <div className="flex gap-2">
          <button onClick={() => handleExport('csv')}
            className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">Export CSV</button>
          <button onClick={() => handleExport('pdf')}
            className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">Export PDF</button>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded text-sm">{error}</div>}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 flex flex-wrap items-center gap-4">
        <div className="flex gap-1">
          {PRESETS.map(p => (
            <button key={p.days} onClick={() => applyPreset(p.days)}
              className="px-3 py-1 text-xs border rounded-full hover:bg-indigo-50 hover:border-indigo-300">
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 text-sm">
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
            className="border rounded px-2 py-1" />
          <span className="text-gray-400">to</span>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
            className="border rounded px-2 py-1" />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-gray-600">Period:</label>
          <select value={period} onChange={e => setPeriod(e.target.value)}
            className="border rounded px-2 py-1">
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <button onClick={loadData}
          className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700">
          Apply
        </button>
      </div>

      {/* Score Trends */}
      {trends && trends.length > 0 && trends.some(b => b.call_count > 0) && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Score Trends</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends.filter(b => b.call_count > 0)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="start_date" tick={{ fontSize: 11 }}
                tickFormatter={v => v.slice(5)} />
              <YAxis domain={[0, 10]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="avg_rep_score"
                stroke="#6366f1" strokeWidth={2} name="Avg Rep Score" dot />
              <Line type="monotone" dataKey="avg_lead_score"
                stroke="#10b981" strokeWidth={2} name="Avg Lead Score" dot />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Campaign Performance */}
      {campaigns && campaigns.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Campaign Performance</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={campaigns}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="campaign_name" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="score" domain={[0, 10]} />
              <YAxis yAxisId="count" orientation="right" allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="score" dataKey="avg_lead_score" fill="#10b981" name="Avg Lead Score" />
              <Bar yAxisId="score" dataKey="avg_rep_score" fill="#6366f1" name="Avg Rep Score" />
              <Bar yAxisId="count" dataKey="call_count" fill="#cbd5e1" name="Call Count" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Rep Performance (supervisor/admin only) */}
      {reps && reps.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Rep Performance</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="py-2">Rep</th>
                <th className="py-2">Calls</th>
                <th className="py-2">Avg Rep Score</th>
              </tr>
            </thead>
            <tbody>
              {reps.map(r => (
                <tr key={r.rep_id} className="border-b">
                  <td className="py-2">{r.rep_name}</td>
                  <td className="py-2">{r.call_count}</td>
                  <td className="py-2">
                    {r.avg_rep_score != null ? (
                      <span className={`font-medium ${
                        r.avg_rep_score >= 8 ? 'text-green-600' :
                        r.avg_rep_score >= 6 ? 'text-yellow-600' :
                        r.avg_rep_score >= 4 ? 'text-orange-600' : 'text-red-600'
                      }`}>{r.avg_rep_score.toFixed(1)}</span>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

Key changes:
- Removed: `fetchTeamComparison`, `fetchCompliance` (dead endpoints)
- Added: `fetchCampaigns`, `fetchReps` (new endpoints)
- Trends chart: two lines on same Y axis (0-10) — Avg Rep Score and Avg Lead Score
- Campaign chart: grouped bar chart with lead score, rep score, call count
- Rep table: simple table with name, call count, avg rep score (supervisor/admin only)
- Removed: team comparison charts, compliance section, worker references
- Uses `user.role !== 'rep'` instead of `user.role !== 'worker'`
- Trends data is now a flat array (not `trends.buckets`)

**Step 2: Commit**

```bash
git add frontend/src/components/Reports.jsx
git commit -m "feat: update Reports for CTM campaigns and rep performance"
```

---

### Task 7: Update AudioUpload — Remove Title Field

**Files:**
- Modify: `frontend/src/components/AudioUpload.jsx`

**Step 1: Remove title field from AudioUpload**

Replace `frontend/src/components/AudioUpload.jsx` with:
```jsx
import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadAudio } from '../api/client'

export default function AudioUpload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef()
  const navigate = useNavigate()

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (f) setFile(f)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setError(null)
    setUploading(true)
    try {
      const call = await uploadAudio(file)
      navigate(`/calls/${call.id}`)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
      setUploading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Upload Audio</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
            dragOver ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".wav,.mp3,.m4a,.webm,.ogg,.flac"
            onChange={handleFileChange}
            className="hidden"
          />
          {file ? (
            <div>
              <p className="font-medium">{file.name}</p>
              <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
            </div>
          ) : (
            <div>
              <p className="text-gray-500">Drag & drop an audio file here, or click to browse</p>
              <p className="text-xs text-gray-400 mt-1">WAV, MP3, M4A, WebM, OGG, FLAC</p>
            </div>
          )}
        </div>

        {error && (
          <p className="text-red-600 text-sm">{error}</p>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          className="w-full bg-indigo-600 text-white py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Upload & Process'}
        </button>
      </form>
    </div>
  )
}
```

Key changes:
- Removed: title state, title input field (Call model has no title)
- `uploadAudio(file)` instead of `uploadAudio(file, title)`

**Step 2: Commit**

```bash
git add frontend/src/components/AudioUpload.jsx
git commit -m "feat: remove title field from AudioUpload (Call has no title)"
```

---

### Task 8: Update frontend/index.html Title

**Files:**
- Modify: `frontend/index.html`

**Step 1: Update the page title**

Change `<title>Call Monitor</title>` to `<title>CTM Scorer</title>` in `frontend/index.html`.

**Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "fix: update page title to CTM Scorer"
```
