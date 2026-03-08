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
