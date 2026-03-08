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
