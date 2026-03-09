'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Users, FileText, ScrollText, AlertCircle,
  TrendingUp, DollarSign, Award, CheckCircle,
  Clock, BarChart2, RefreshCw,
} from 'lucide-react'

interface Overview {
  total_users: number
  active_users: number
  students: number
  researchers: number
  professors: number
  new_users_this_month: number
  total_jobs: number
  open_jobs: number
  completed_jobs: number
  disputed_jobs: number
  total_volume_usd: number
  platform_revenue_usd: number
  pending_payouts_usd: number
  avg_completion_rate: number
  avg_review_score: number
  avg_dispute_resolution_hours: number
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

function fmt(n: number, decimals = 0) {
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}
function fmtUsd(n: number) {
  return '$' + fmt(n, 2)
}

export default function AdminDashboard() {
  const router = useRouter()
  const [overview, setOverview] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    const token = localStorage.getItem('auth_token')
    if (!token) { router.push('/auth/login'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API}/admin/dashboard`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403) { router.push('/dashboard'); return }
      const data = await res.json()
      setOverview(data.data)
    } catch {
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="p-8 flex items-center gap-3 text-medGrey">
      <RefreshCw className="w-5 h-5 animate-spin" /> Loading platform overview...
    </div>
  )

  if (error) return (
    <div className="p-8 text-red-500">{error}</div>
  )

  if (!overview) return null

  return (
    <div className="p-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Platform Dashboard</h1>
          <p className="text-medGrey text-sm mt-1">Real-time platform overview</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-white border border-divider rounded-lg hover:bg-lightGrey transition-colors"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Users row */}
      <div className="mb-6">
        <h2 className="text-xs font-semibold text-medGrey uppercase tracking-widest mb-3">Users</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { label: 'Total Users', value: fmt(overview.total_users), icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Active', value: fmt(overview.active_users), icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
            { label: 'Students', value: fmt(overview.students), icon: FileText, color: 'text-purple-600', bg: 'bg-purple-50' },
            { label: 'Researchers', value: fmt(overview.researchers), icon: TrendingUp, color: 'text-orange-600', bg: 'bg-orange-50' },
            { label: 'Professors', value: fmt(overview.professors), icon: Award, color: 'text-teal-600', bg: 'bg-teal-50' },
            { label: 'New This Month', value: fmt(overview.new_users_this_month), icon: Users, color: 'text-indigo-600', bg: 'bg-indigo-50' },
          ].map(({ label, value, icon: Icon, color, bg }) => (
            <div key={label} className="bg-white rounded-xl border border-divider p-4">
              <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div className="text-2xl font-bold text-charcoal">{value}</div>
              <div className="text-xs text-medGrey mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Jobs row */}
      <div className="mb-6">
        <h2 className="text-xs font-semibold text-medGrey uppercase tracking-widest mb-3">Jobs & Contracts</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Jobs', value: fmt(overview.total_jobs), icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Open Jobs', value: fmt(overview.open_jobs), icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
            { label: 'Completed', value: fmt(overview.completed_jobs), icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
            { label: 'Disputed', value: fmt(overview.disputed_jobs), icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
          ].map(({ label, value, icon: Icon, color, bg }) => (
            <div key={label} className="bg-white rounded-xl border border-divider p-5">
              <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div className="text-3xl font-bold text-charcoal">{value}</div>
              <div className="text-xs text-medGrey mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Revenue row */}
      <div className="mb-6">
        <h2 className="text-xs font-semibold text-medGrey uppercase tracking-widest mb-3">Revenue</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-divider p-5">
            <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mb-3">
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
            <div className="text-3xl font-bold text-charcoal">{fmtUsd(overview.total_volume_usd)}</div>
            <div className="text-xs text-medGrey mt-1">Total Platform Volume</div>
          </div>
          <div className="bg-gradient-to-br from-ctaBlue to-steelBlue rounded-xl p-5 text-white">
            <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center mb-3">
              <BarChart2 className="w-5 h-5 text-white" />
            </div>
            <div className="text-3xl font-bold">{fmtUsd(overview.platform_revenue_usd)}</div>
            <div className="text-xs text-white/75 mt-1">Estimated Platform Revenue</div>
          </div>
          <div className="bg-white rounded-xl border border-divider p-5">
            <div className="w-9 h-9 bg-orange-50 rounded-lg flex items-center justify-center mb-3">
              <ScrollText className="w-5 h-5 text-orange-600" />
            </div>
            <div className="text-3xl font-bold text-charcoal">{fmtUsd(overview.pending_payouts_usd)}</div>
            <div className="text-xs text-medGrey mt-1">Pending Payouts</div>
          </div>
        </div>
      </div>

      {/* Quality KPIs */}
      <div>
        <h2 className="text-xs font-semibold text-medGrey uppercase tracking-widest mb-3">Quality Indicators</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-divider p-5">
            <div className="text-3xl font-bold text-charcoal">{overview.avg_completion_rate}%</div>
            <div className="text-xs text-medGrey mt-1">Job Completion Rate</div>
            <div className="mt-3 h-2 bg-lightGrey rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full"
                style={{ width: `${overview.avg_completion_rate}%` }}
              />
            </div>
          </div>
          <div className="bg-white rounded-xl border border-divider p-5">
            <div className="text-3xl font-bold text-charcoal">{overview.avg_review_score}/100</div>
            <div className="text-xs text-medGrey mt-1">Avg Professor Review Score</div>
            <div className="mt-3 h-2 bg-lightGrey rounded-full overflow-hidden">
              <div
                className="h-full bg-steelBlue rounded-full"
                style={{ width: `${overview.avg_review_score}%` }}
              />
            </div>
          </div>
          <div className="bg-white rounded-xl border border-divider p-5">
            <div className="text-3xl font-bold text-charcoal">{overview.avg_dispute_resolution_hours || '—'}h</div>
            <div className="text-xs text-medGrey mt-1">Avg Dispute Resolution Time</div>
          </div>
        </div>
      </div>

      {/* Quick links */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Manage Users', href: '/admin/users', icon: Users },
          { label: 'Approve Professors', href: '/admin/professors', icon: Award },
          { label: 'Review Disputes', href: '/admin/disputes', icon: AlertCircle },
          { label: 'Approve Payouts', href: '/admin/payouts', icon: ScrollText },
        ].map(({ label, href, icon: Icon }) => (
          <a
            key={href}
            href={href}
            className="flex items-center gap-3 p-4 bg-white border border-divider rounded-xl hover:border-steelBlue hover:shadow-sm transition-all text-sm font-medium text-charcoal"
          >
            <Icon className="w-4 h-4 text-steelBlue flex-shrink-0" />
            {label}
          </a>
        ))}
      </div>
    </div>
  )
}
