'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Star, Award, TrendingUp, Clock, CheckCircle, DollarSign, RefreshCw } from 'lucide-react'

interface Analytics {
  total_reviews: number
  pending_reviews: number
  completed_reviews: number
  avg_score_given: number
  total_fees_earned: number
  disputes_arbitrated: number
  credentials_verified: number
  endorsements_given: number
  sla_compliance_rate: number
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export default function ProfessorAnalytics() {
  const router = useRouter()
  const [data, setData] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    const token = localStorage.getItem('auth_token')
    if (!token) { router.push('/auth/login'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API}/professor/analytics`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403) { router.push('/dashboard'); return }
      setData(await res.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="p-8 flex items-center gap-2 text-medGrey">
      <RefreshCw className="w-5 h-5 animate-spin" /> Loading analytics...
    </div>
  )
  if (!data) return null

  const stats = [
    { label: 'Total Reviews', value: data.total_reviews, icon: Star, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Pending Reviews', value: data.pending_reviews, icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
    { label: 'Completed Reviews', value: data.completed_reviews, icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Avg Score Given', value: `${data.avg_score_given.toFixed(1)}/100`, icon: TrendingUp, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Fees Earned', value: `$${data.total_fees_earned.toFixed(2)}`, icon: DollarSign, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Disputes Arbitrated', value: data.disputes_arbitrated, icon: Award, color: 'text-red-600', bg: 'bg-red-50' },
    { label: 'Credentials Verified', value: data.credentials_verified, icon: CheckCircle, color: 'text-teal-600', bg: 'bg-teal-50' },
    { label: 'Endorsements Given', value: data.endorsements_given, icon: Award, color: 'text-indigo-600', bg: 'bg-indigo-50' },
  ]

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">My Analytics</h1>
          <p className="text-medGrey text-sm mt-1">Your performance as a platform reviewer</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 bg-white border border-divider rounded-lg text-sm hover:bg-lightGrey transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* SLA compliance highlight */}
      <div className="mb-6 bg-gradient-to-br from-steelBlue to-ctaBlue rounded-2xl p-6 text-white">
        <div className="text-sm font-medium text-white/75 mb-1">SLA Compliance Rate</div>
        <div className="text-5xl font-bold mb-3">{data.sla_compliance_rate}%</div>
        <div className="h-2 bg-white/20 rounded-full overflow-hidden">
          <div
            className="h-full bg-white rounded-full transition-all"
            style={{ width: `${data.sla_compliance_rate}%` }}
          />
        </div>
        <div className="text-xs text-white/60 mt-2">Reviews completed within the agreed SLA window</div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white border border-divider rounded-xl p-5">
            <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>
              <Icon className={`w-5 h-5 ${color}`} />
            </div>
            <div className="text-2xl font-bold text-charcoal">{value}</div>
            <div className="text-xs text-medGrey mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Score bands reference */}
      <div className="mt-6 bg-white border border-divider rounded-xl p-5">
        <h3 className="text-sm font-semibold text-charcoal mb-3">Quality Score Reference</h3>
        <div className="grid grid-cols-5 gap-2 text-center text-xs">
          {[
            { range: '90–100', grade: 'A', color: 'bg-green-100 text-green-700' },
            { range: '80–89', grade: 'B', color: 'bg-teal-100 text-teal-700' },
            { range: '70–79', grade: 'C', color: 'bg-yellow-100 text-yellow-700' },
            { range: '60–69', grade: 'D', color: 'bg-orange-100 text-orange-700' },
            { range: '<60', grade: 'F', color: 'bg-red-100 text-red-700' },
          ].map(({ range, grade, color }) => (
            <div key={grade} className={`${color} rounded-lg py-2`}>
              <div className="font-bold text-base">{grade}</div>
              <div className="text-xs opacity-75">{range}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
