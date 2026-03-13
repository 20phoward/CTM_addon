import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { fetchDashboardStats } from '../api/client'

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 text-center">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color || ''}`}>{value}</p>
    </div>
  )
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400">-</span>
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

function NavWidget({ to, title, description }) {
  return (
    <Link to={to} className="bg-white border border-slate-200 rounded-lg hover:border-slate-300 transition p-4 flex flex-col gap-1">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <p className="text-xs text-slate-400">{description}</p>
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
  if (!stats) return <p className="text-slate-500">Loading...</p>

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Welcome back, {user.name}</h1>
        <p className="text-sm text-slate-500 mt-1">Here's an overview of your call scoring activity.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Stats summary — left side */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-lg p-6">
          <h2 className="text-sm font-medium text-slate-400 mb-4">Overview</h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-3xl font-bold text-slate-900">{stats.total_calls}</p>
              <p className="text-sm text-slate-500 mt-1">Total Calls</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-slate-900">{stats.completed_calls}</p>
              <p className="text-sm text-slate-500 mt-1">Completed</p>
            </div>
            <div>
              <p className={`text-3xl font-bold ${stats.avg_rep_score != null ? 'text-slate-700' : 'text-slate-300'}`}>
                {stats.avg_rep_score != null ? stats.avg_rep_score.toFixed(1) : '—'}
              </p>
              <p className="text-sm text-slate-500 mt-1">Avg Rep Score</p>
            </div>
            <div>
              <p className={`text-3xl font-bold ${stats.avg_lead_score != null ? 'text-emerald-600' : 'text-slate-300'}`}>
                {stats.avg_lead_score != null ? stats.avg_lead_score.toFixed(1) : '—'}
              </p>
              <p className="text-sm text-slate-500 mt-1">Avg Lead Score</p>
            </div>
          </div>
        </div>

        {/* Quick access — right side */}
        <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NavWidget to="/calls" title="Calls" description="Browse scored calls" />
          <NavWidget to="/upload" title="Upload" description="Upload audio files" />
          <NavWidget to="/reports" title="Reports" description="Trends & exports" />
          {user.role === 'admin' && (
            <>
              <NavWidget to="/users" title="Users" description="Manage accounts" />
              <NavWidget to="/teams" title="Teams" description="Manage teams" />
              <NavWidget to="/audit-log" title="Audit Log" description="Activity history" />
            </>
          )}
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Recent Calls</h2>
        {stats.recent_calls.length === 0 ? (
          <p className="text-slate-500">No calls yet. <Link to="/upload" className="text-slate-600 hover:text-slate-800 underline">Upload one</Link>.</p>
        ) : (
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left">
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
                  <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-2">
                      <Link to={`/calls/${c.id}`} className="text-slate-600 hover:text-slate-800 hover:underline">
                        {c.call_date ? new Date(c.call_date).toLocaleDateString() : '-'}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-slate-500">{c.campaign_name || '-'}</td>
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
