'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ClipboardList, Star, Award, TrendingUp, Clock, CheckCircle, DollarSign, AlertCircle, RefreshCw } from 'lucide-react'
import { api, ProfAnalytics, ProfProfile, QueueItem } from '@/lib/api'
import { timeUntil } from '@/lib/utils'

export default function Dashboard() {
  const router = useRouter()
  const [analytics, setAnalytics] = useState<ProfAnalytics | null>(null)
  const [profile,   setProfile]   = useState<ProfProfile | null>(null)
  const [queue,     setQueue]     = useState<QueueItem[]>([])
  const [loading,   setLoading]   = useState(true)
  const [userName,  setUserName]  = useState('')

  useEffect(() => {
    const raw = localStorage.getItem('prof_user')
    if (raw) {
      const u = JSON.parse(raw)
      setUserName(`${u.first_name} ${u.last_name}`)
    }
    load()
  }, [])

  async function load() {
    setLoading(true)
    try {
      const [a, p, q] = await Promise.all([
        api.getAnalytics(),
        api.getProfile().catch(() => null),
        api.getQueue('assigned').catch(() => [] as QueueItem[]),
      ])
      setAnalytics(a)
      if (p) {
        setProfile(p)
        localStorage.setItem('prof_profile', JSON.stringify(p))
      }
      setQueue((q as QueueItem[]).slice(0, 3))
    } catch (err: any) {
      if (err.message?.includes('401')) router.push('/auth/login')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return (
    <div className="p-8 flex items-center gap-3 text-medGrey">
      <RefreshCw className="w-5 h-5 animate-spin" /> Loading dashboard…
    </div>
  )

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-7">
        <h1 className="text-2xl font-bold text-charcoal">
          Welcome back, {userName.split(' ')[0]} 👋
        </h1>
        {profile && (
          <p className="text-medGrey text-sm mt-1">
            {profile.title && `${profile.title} · `}{profile.department ?? 'Professor'}
            {profile.status !== 'approved' && (
              <span className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full text-xs font-semibold uppercase">
                {profile.status}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Pending setup notice */}
      {profile?.status === 'pending' && (
        <div className="mb-6 flex items-start gap-3 px-5 py-4 bg-yellow-50 border border-yellow-200 rounded-xl text-sm text-yellow-800">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <strong>Profile under review.</strong> An admin is reviewing your professor profile.
            You will receive full queue access once approved.
          </div>
        </div>
      )}

      {/* Stats */}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-7">
          {[
            { label: 'Reviews Done',     value: analytics.completed_reviews, icon: CheckCircle, color: 'text-green-600',  bg: 'bg-green-50'  },
            { label: 'Pending Reviews',  value: analytics.pending_reviews,   icon: Clock,       color: 'text-yellow-600', bg: 'bg-yellow-50' },
            { label: 'Disputes Handled', value: analytics.disputes_arbitrated, icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50'    },
            { label: 'Fees Earned',      value: `$${analytics.total_fees_earned.toFixed(2)}`, icon: DollarSign, color: 'text-emerald-600', bg: 'bg-emerald-50' },
          ].map(({ label, value, icon: Icon, color, bg }) => (
            <div key={label} className="bg-white border border-divider rounded-xl p-5">
              <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div className="text-2xl font-bold text-charcoal">{value}</div>
              <div className="text-xs text-medGrey mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* SLA bar */}
      {analytics && (
        <div className="bg-white border border-divider rounded-xl p-5 mb-7">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-charcoal">SLA Compliance</span>
            <span className="text-sm font-bold text-profTeal">{analytics.sla_compliance_rate}%</span>
          </div>
          <div className="h-2.5 bg-lightGrey rounded-full overflow-hidden">
            <div
              className="h-full bg-profTeal rounded-full transition-all"
              style={{ width: `${analytics.sla_compliance_rate}%` }}
            />
          </div>
          <p className="text-xs text-medGrey mt-2">Reviews completed within the agreed SLA window</p>
        </div>
      )}

      {/* Active queue items */}
      <div className="mb-7">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-charcoal">Active Queue Items</h2>
          <a href="/queue" className="text-xs text-profTeal font-medium hover:underline">View all →</a>
        </div>
        {queue.length === 0 ? (
          <div className="bg-white border border-divider rounded-xl px-5 py-8 text-center text-medGrey text-sm">
            <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-30" />
            Queue is empty — nothing assigned yet
          </div>
        ) : (
          <div className="space-y-3">
            {queue.map(item => {
              const t = timeUntil(item.due_at ?? null)
              return (
                <div key={item.id} className="bg-white border border-divider rounded-xl px-5 py-4 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-charcoal capitalize">
                      {item.queue_type.replace(/_/g, ' ')}
                    </div>
                    <div className="text-xs text-medGrey mt-0.5">
                      Contract: <span className="font-mono">{item.contract_id.slice(0, 8)}…</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className={`text-xs font-semibold ${t.urgent ? 'text-red-600' : 'text-medGrey'}`}>
                      <Clock className="w-3.5 h-3.5 inline mr-1" />{t.label}
                    </span>
                    <a
                      href={`/reviews/submit?contract=${item.contract_id}`}
                      className="px-3 py-1.5 bg-profTeal text-white rounded-lg text-xs font-medium hover:bg-profDark transition-colors"
                    >
                      Review →
                    </a>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[
          { label: 'Review Queue',     href: '/queue',       icon: ClipboardList },
          { label: 'My Assignments',   href: '/assignments', icon: Award         },
          { label: 'Credentials',      href: '/credentials', icon: Star          },
          { label: 'Active Disputes',  href: '/disputes',    icon: AlertCircle   },
          { label: 'Analytics',        href: '/analytics',   icon: TrendingUp    },
          { label: 'My Profile',       href: '/account',     icon: Award         },
        ].map(({ label, href, icon: Icon }) => (
          <a
            key={href}
            href={href}
            className="flex items-center gap-3 p-4 bg-white border border-divider rounded-xl hover:border-profTeal hover:shadow-sm transition-all text-sm font-medium text-charcoal"
          >
            <Icon className="w-4 h-4 text-profTeal flex-shrink-0" />
            {label}
          </a>
        ))}
      </div>
    </div>
  )
}
