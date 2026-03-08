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
