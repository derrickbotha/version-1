'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, Star, Scale, Award, RefreshCw, Clock } from 'lucide-react'
import { api, ProfAnalytics } from '@/lib/api'

const GRADE = (s: number) =>
  s >= 90 ? 'A' : s >= 80 ? 'B' : s >= 70 ? 'C' : s >= 60 ? 'D' : 'F'

const GRADE_COLOR = (s: number) =>
  s >= 90 ? 'text-green-600' : s >= 80 ? 'text-teal-600' : s >= 70 ? 'text-yellow-600' : s >= 60 ? 'text-orange-600' : 'text-red-600'

function StatCard({ label, value, sub, color = 'text-charcoal' }: {
  label: string; value: string | number; sub?: string; color?: string
}) {
  return (
    <div className="bg-white border border-divider rounded-xl px-5 py-4">
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
      <div className="text-sm font-medium text-charcoal mt-0.5">{label}</div>
      {sub && <div className="text-xs text-medGrey mt-0.5">{sub}</div>}
    </div>
  )
}

export default function AnalyticsPage() {
  const [data, setData]       = useState<ProfAnalytics | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try { setData(await api.getAnalytics()) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="p-8 flex items-center justify-center gap-2 text-medGrey">
      <RefreshCw className="w-5 h-5 animate-spin" /> Loading analytics…
    </div>
  )

  if (!data) return (
    <div className="p-8 text-red-600">Failed to load analytics.</div>
  )

  const slaColor = data.sla_compliance_rate >= 90
    ? 'bg-green-500' : data.sla_compliance_rate >= 70
    ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Performance Analytics</h1>
          <p className="text-medGrey text-sm mt-1">Your activity and quality metrics</p>
        </div>
        <button onClick={load} className="p-2 bg-white border border-divider rounded-lg hover:bg-lightGrey transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Reviews Done"
          value={data.completed_reviews}
          sub="Total quality reviews"
          color="text-profTeal"
        />
        <StatCard
          label="Disputes Resolved"
          value={data.disputes_arbitrated}
          sub="Arbitration rulings issued"
          color="text-blue-600"
        />
        <StatCard
          label="Credentials Verified"
          value={data.credentials_verified}
          sub="Researcher credentials"
          color="text-purple-600"
        />
        <StatCard
          label="Fees Earned"
          value={`$${data.total_fees_earned.toFixed(2)}`}
          sub="Total review fees"
          color="text-green-600"
        />
      </div>

      {/* Score + SLA */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">

        {/* Average Score */}
        <div className="bg-white border border-divider rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Star className="w-5 h-5 text-profTeal" />
            <h2 className="font-semibold text-charcoal">Average Scores Given</h2>
          </div>
          {data.avg_score_given != null ? (
            <div className="flex items-end gap-3">
              <span className={`text-5xl font-bold ${GRADE_COLOR(data.avg_score_given)}`}>
                {GRADE(data.avg_score_given)}
              </span>
              <div className="pb-1">
                <div className="text-2xl font-bold text-charcoal">{data.avg_score_given.toFixed(1)}</div>
                <div className="text-xs text-medGrey">/ 100</div>
              </div>
            </div>
          ) : (
            <p className="text-medGrey text-sm">No reviews submitted yet</p>
          )}
          <div className="mt-4 h-2 bg-lightGrey rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${GRADE_COLOR(data.avg_score_given ?? 0).replace('text-', 'bg-')}`}
              style={{ width: `${data.avg_score_given ?? 0}%` }}
            />
          </div>
        </div>

        {/* SLA Compliance */}
        <div className="bg-white border border-divider rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-profTeal" />
            <h2 className="font-semibold text-charcoal">SLA Compliance</h2>
          </div>
          <div className="flex items-end gap-2 mb-3">
            <span className="text-4xl font-bold text-charcoal">{data.sla_compliance_rate.toFixed(0)}%</span>
            <span className="text-sm text-medGrey pb-1">on-time completion</span>
          </div>
          <div className="h-3 bg-lightGrey rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${slaColor}`}
              style={{ width: `${data.sla_compliance_rate}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-medGrey mt-1.5">
            <span>0%</span>
            <span className={data.sla_compliance_rate >= 90 ? 'text-green-600 font-medium' : ''}>
              {data.sla_compliance_rate >= 90 ? 'Excellent' : data.sla_compliance_rate >= 70 ? 'Good' : 'Needs improvement'}
            </span>
            <span>100%</span>
          </div>
        </div>
      </div>

      {/* Pending */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-divider rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Scale className="w-5 h-5 text-profTeal" />
            <h2 className="font-semibold text-charcoal">Queue Overview</h2>
          </div>
          <div className="space-y-3">
            {[
              { label: 'Pending Reviews',    value: data.pending_reviews,                              color: 'bg-blue-500'   },
              { label: 'Disputes Handled',   value: data.disputes_arbitrated,                          color: 'bg-red-500'    },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-sm text-charcoal">{label}</span>
                <span className={`px-3 py-0.5 rounded-full text-white text-xs font-bold ${color}`}>{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-divider rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-profTeal" />
            <h2 className="font-semibold text-charcoal">Activity Summary</h2>
          </div>
          <div className="space-y-2 text-sm">
            {[
              { label: 'Reviews completed',      value: data.completed_reviews    },
              { label: 'Disputes resolved',       value: data.disputes_arbitrated    },
              { label: 'Credentials verified',    value: data.credentials_verified },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between py-1 border-b border-divider last:border-0">
                <span className="text-medGrey">{label}</span>
                <span className="font-semibold text-charcoal">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
