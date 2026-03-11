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
      <p className="text-xs text-slate-500 mt-1">{label}</p>
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
      <span className="w-28 text-slate-600 shrink-0">{label}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: barWidth }} />
      </div>
      <span className="w-8 text-right text-slate-700 font-medium">{value.toFixed(1)}</span>
    </div>
  )
}

export default function ScoreDisplay({ score }) {
  if (!score) return null

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Rep Score */}
      <div className="bg-white rounded-lg border border-slate-200 p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">Rep Score</h3>
        <div className="flex items-start gap-6">
          <ScoreCircle score={score.rep_score} label="Overall" />
          <div className="flex-1 space-y-2">
            <SubScore label="Tone" value={score.rep_tone} />
            <SubScore label="Call Steering" value={score.rep_steering} />
            <SubScore label="Service" value={score.rep_service} />
          </div>
        </div>
        {score.rep_reasoning && (
          <p className="text-sm text-slate-500 mt-4 border-t pt-3">{score.rep_reasoning}</p>
        )}
      </div>

      {/* Lead Score */}
      <div className="bg-white rounded-lg border border-slate-200 p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">Lead Score</h3>
        <div className="flex items-start gap-6">
          <ScoreCircle score={score.lead_score} label="Overall" />
          <div className="flex-1 space-y-2">
            <SubScore label="Service Match" value={score.lead_service_match} />
            <SubScore label="Insurance" value={score.lead_insurance} />
            <SubScore label="Intent" value={score.lead_intent} />
          </div>
        </div>
        {score.lead_reasoning && (
          <p className="text-sm text-slate-500 mt-4 border-t pt-3">{score.lead_reasoning}</p>
        )}
      </div>
    </div>
  )
}
