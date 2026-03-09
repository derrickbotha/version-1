'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ClipboardList, Clock, AlertCircle, CheckCircle, RefreshCw, Play } from 'lucide-react'

interface QueueItem {
  id: string
  contract_id: string
  queue_type: string
  status: string
  priority: number
  sla_hours: number
  due_at: string | null
  assigned_at: string | null
  completed_at: string | null
  notes: string | null
  created_at: string
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

function timeUntil(due: string | null): { label: string; urgent: boolean } {
  if (!due) return { label: 'No deadline', urgent: false }
  const diff = new Date(due).getTime() - Date.now()
  const hours = Math.floor(diff / 3_600_000)
  if (hours < 0) return { label: 'OVERDUE', urgent: true }
  if (hours < 4) return { label: `${hours}h left`, urgent: true }
  if (hours < 24) return { label: `${hours}h left`, urgent: false }
  const days = Math.floor(hours / 24)
  return { label: `${days}d left`, urgent: false }
}

const PRIORITY_LABEL: Record<number, { label: string; color: string }> = {
  1: { label: 'URGENT', color: 'bg-red-100 text-red-700' },
  2: { label: 'HIGH', color: 'bg-orange-100 text-orange-700' },
  5: { label: 'NORMAL', color: 'bg-blue-100 text-blue-700' },
  8: { label: 'LOW', color: 'bg-gray-100 text-gray-600' },
}

export default function ProfessorQueue() {
  const router = useRouter()
  const [items, setItems] = useState<QueueItem[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [actioning, setActioning] = useState<string | null>(null)
  const [flash, setFlash] = useState('')

  async function load() {
    const token = localStorage.getItem('auth_token')
    if (!token) { router.push('/auth/login'); return }
    setLoading(true)
    const params = new URLSearchParams()
    if (statusFilter) params.set('status_filter', statusFilter)
    try {
      const res = await fetch(`${API}/professor/queue?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403) { router.push('/dashboard'); return }
      setItems(await res.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [statusFilter])

  async function acceptItem(itemId: string) {
    const token = localStorage.getItem('auth_token')
    setActioning(itemId)
    const res = await fetch(`${API}/professor/queue/${itemId}/accept`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    setActioning(null)
    if (res.ok) { setFlash('Item accepted — SLA clock started'); load() }
  }

  function goToReview(contractId: string) {
    router.push(`/professor/reviews/submit?contract=${contractId}`)
  }

  const pending = items.filter(i => ['queued', 'assigned'].includes(i.status))
  const active = items.filter(i => i.status === 'in_progress')
  const completed = items.filter(i => ['completed', 'expired', 'reassigned'].includes(i.status))

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Review Queue</h1>
          <p className="text-medGrey text-sm mt-1">
            {pending.length} pending · {active.length} in progress
          </p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 bg-white border border-divider rounded-lg text-sm hover:bg-lightGrey transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          {flash}
        </div>
      )}

      {loading ? (
        <div className="py-12 flex items-center justify-center gap-2 text-medGrey">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading queue...
        </div>
      ) : items.length === 0 ? (
        <div className="py-16 text-center">
          <ClipboardList className="w-12 h-12 text-medGrey mx-auto mb-3" />
          <p className="text-charcoal font-medium">Queue is empty</p>
          <p className="text-medGrey text-sm mt-1">No review items assigned to you</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Active Items */}
          {active.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-charcoal mb-3 flex items-center gap-2">
                <Play className="w-4 h-4 text-green-600" /> In Progress
              </h2>
              <div className="space-y-3">
                {active.map(item => {
                  const timeInfo = timeUntil(item.due_at)
                  const priorityInfo = PRIORITY_LABEL[item.priority] || PRIORITY_LABEL[5]
                  return (
                    <div key={item.id} className="bg-white border-2 border-green-200 rounded-xl p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${priorityInfo.color}`}>
                              {priorityInfo.label}
                            </span>
                            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs capitalize">
                              {item.queue_type.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="text-sm text-charcoal font-medium">
                            Contract: <span className="font-mono text-xs text-medGrey">{item.contract_id.slice(0, 8)}…</span>
                          </div>
                          {item.notes && <p className="text-xs text-medGrey mt-1">{item.notes}</p>}
                        </div>
                        <div className="text-right flex-shrink-0 ml-4">
                          <div className={`text-sm font-semibold ${timeInfo.urgent ? 'text-red-600' : 'text-medGrey'}`}>
                            <Clock className="w-3.5 h-3.5 inline mr-1" />{timeInfo.label}
                          </div>
                          <button
                            onClick={() => goToReview(item.contract_id)}
                            className="mt-2 px-4 py-1.5 bg-steelBlue text-white rounded-lg text-sm font-medium hover:bg-ctaBlue transition-colors"
                          >
                            Submit Review →
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* Pending Items */}
          {pending.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-charcoal mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-yellow-600" /> Pending Acceptance
              </h2>
              <div className="space-y-3">
                {pending.map(item => {
                  const timeInfo = timeUntil(item.due_at)
                  const priorityInfo = PRIORITY_LABEL[item.priority] || PRIORITY_LABEL[5]
                  return (
                    <div key={item.id} className="bg-white border border-divider rounded-xl p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${priorityInfo.color}`}>
                              {priorityInfo.label}
                            </span>
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs capitalize">
                              {item.queue_type.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="text-sm text-charcoal font-medium">
                            Contract: <span className="font-mono text-xs text-medGrey">{item.contract_id.slice(0, 8)}…</span>
                          </div>
                          <div className="text-xs text-medGrey mt-1">SLA: {item.sla_hours}h from acceptance</div>
                        </div>
                        <button
                          onClick={() => acceptItem(item.id)}
                          disabled={actioning === item.id}
                          className="flex items-center gap-1.5 px-4 py-2 bg-steelBlue text-white rounded-lg text-sm font-medium hover:bg-ctaBlue disabled:opacity-50 transition-colors flex-shrink-0 ml-4"
                        >
                          <Play className="w-4 h-4" /> Accept
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* Completed */}
          {completed.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-charcoal mb-3 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-600" /> Completed
              </h2>
              <div className="space-y-2">
                {completed.slice(0, 5).map(item => (
                  <div key={item.id} className="bg-white border border-divider rounded-xl px-5 py-3 flex items-center justify-between">
                    <span className="text-sm text-charcoal font-mono">{item.contract_id.slice(0, 8)}…</span>
                    <div className="flex items-center gap-3 text-xs text-medGrey">
                      <span className="capitalize">{item.queue_type.replace(/_/g, ' ')}</span>
                      <span className={`px-2 py-0.5 rounded-full ${item.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {item.status}
                      </span>
                      {item.completed_at && <span>{new Date(item.completed_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
