import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchCallDetail, fetchCallStatus, deleteCall, audioUrl, sendConversion } from '../api/client'
import ScoreDisplay from './ScoreDisplay'
import { useAuth } from '../contexts/AuthContext'

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function MetaItem({ label, value }) {
  if (!value) return null
  return (
    <div>
      <span className="text-xs text-slate-500">{label}</span>
      <p className="text-sm font-medium text-slate-800">{value}</p>
    </div>
  )
}

export default function CallDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [call, setCall] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const handleRetryConversion = async () => {
    try {
      await sendConversion(id)
      const updated = await fetchCallDetail(id)
      setCall(updated)
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to send conversion')
    }
  }

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

  if (loading) return <p className="text-slate-500">Loading...</p>
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
          <h1 className="text-2xl font-bold text-slate-900">
            Call {call.call_date ? new Date(call.call_date).toLocaleDateString() : `#${call.id}`}
          </h1>
          <p className="text-sm text-slate-500">
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
      <div className="bg-white rounded-lg border border-slate-200 p-5 mb-6">
        <h2 className="text-base font-semibold text-slate-700 mb-3">Call Details</h2>
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
          <div className="mt-3 pt-3 border-t flex items-center gap-3">
            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
              call.conversion.status.includes('sent') ? 'bg-green-100 text-green-800' :
              call.conversion.status === 'failed' ? 'bg-red-100 text-red-800' :
              'bg-slate-100 text-slate-800'
            }`}>
              Conversion: {call.conversion.status}
            </span>
            {call.conversion.status === 'failed' && user?.role === 'admin' && (
              <button onClick={handleRetryConversion} className="text-xs text-slate-600 hover:underline">
                Retry
              </button>
            )}
          </div>
        )}
        {!call.conversion && call.gclid && call.status === 'completed' && user?.role === 'admin' && (
          <div className="mt-3 pt-3 border-t">
            <button onClick={handleRetryConversion} className="text-xs text-slate-600 hover:underline">
              Send Conversion
            </button>
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
          <div className="bg-white rounded-lg border border-slate-200 p-4 max-h-96 overflow-y-auto space-y-3">
            {call.transcript.segments?.length > 0 ? (
              call.transcript.segments.map((seg, i) => {
                const prevSpeaker = i > 0 ? call.transcript.segments[i - 1].speaker : null
                const showSpeaker = seg.speaker && seg.speaker !== prevSpeaker
                const firstSpeaker = call.transcript.segments.find(s => s.speaker)?.speaker
                const isFirstSpeaker = seg.speaker === firstSpeaker
                return (
                  <div key={i} className="flex gap-3 text-sm">
                    <span className="font-mono text-slate-400 whitespace-nowrap text-xs mt-0.5">
                      {formatTime(seg.start)}
                    </span>
                    <div>
                      {showSpeaker && (
                        <span className={`text-xs font-semibold mr-1 ${
                          isFirstSpeaker ? 'text-slate-600' : 'text-emerald-600'
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
