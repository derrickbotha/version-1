'use client'

import { useEffect, useState } from 'react'
import { ClipboardList, Clock, Play, CheckCircle, RefreshCw, AlertCircle } from 'lucide-react'
import { api, QueueItem } from '@/lib/api'
import { timeUntil, fmtDateTime } from '@/lib/utils'

const PRIORITY: Record<number, { label: string; color: string }> = {
  1: { label: 'URGENT',  color: 'bg-red-100 text-red-700'     },
  2: { label: 'HIGH',    color: 'bg-orange-100 text-orange-700'},
  5: { label: 'NORMAL',  color: 'bg-blue-100 text-blue-700'   },
  8: { label: 'LOW',     color: 'bg-gray-100 text-gray-500'   },
}

const TYPE_COLOR: Record<string, string> = {
  quality_review:           'bg-profLight text-profTeal border-profTeal/30',
  dispute_arbitration:      'bg-red-50 text-red-700 border-red-200',
  credential_verification:  'bg-purple-50 text-purple-700 border-purple-200',
}

export default function QueuePage() {
  const [items, setItems]       = useState<QueueItem[]>([])
  const [tab, setTab]           = useState<'active' | 'done'>('active')
  const [loading, setLoading]   = useState(true)
  const [actioning, setActioning] = useState<string | null>(null)
  const [flash, setFlash]       = useState('')

  async function load() {
    setLoading(true)
    try {
      const all = await api.getQueue()
      setItems(all)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function accept(id: string) {
    setActioning(id)
    try {
      await api.acceptQueueItem(id)
      setFlash('Item accepted — SLA clock has started')
      load()
    } catch (err: any) { setFlash(err.message) }
    finally { setActioning(null) }
  }

  const active   = items.filter(i => ['queued','assigned','in_progress'].includes(i.status))
  const done     = items.filter(i => ['completed','expired','reassigned'].includes(i.status))
  const visible  = tab === 'active' ? active : done

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Review Queue</h1>
          <p className="text-medGrey text-sm mt-1">
            {active.length} active · {done.length} completed
          </p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 bg-white border border-divider rounded-lg text-sm hover:bg-lightGrey transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">{flash}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-5">
        {(['active','done'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
              tab === t ? 'bg-profTeal text-white' : 'bg-white border border-divider text-charcoal hover:bg-lightGrey'
            }`}
          >
            {t} ({t === 'active' ? active.length : done.length})
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-12 flex items-center justify-center gap-2 text-medGrey">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading…
        </div>
      ) : visible.length === 0 ? (
        <div className="py-16 text-center">
          <ClipboardList className="w-12 h-12 text-medGrey mx-auto mb-3 opacity-30" />
          <p className="text-charcoal font-medium">Nothing here</p>
          <p className="text-medGrey text-sm mt-1">
            {tab === 'active' ? 'No items assigned yet' : 'No completed items'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map(item => {
            const t    = timeUntil(item.due_at ?? null)
            const p    = PRIORITY[item.priority] ?? PRIORITY[5]
            const tc   = TYPE_COLOR[item.queue_type] ?? 'bg-lightGrey text-charcoal border-divider'
            const inProgress = item.status === 'in_progress'
            const isQueued   = ['queued','assigned'].includes(item.status)
            return (
              <div
                key={item.id}
                className={`bg-white rounded-xl border p-5 ${inProgress ? 'border-profTeal/50 ring-1 ring-profTeal/20' : 'border-divider'}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* Badges */}
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${tc}`}>
                        {item.queue_type.replace(/_/g,' ').toUpperCase()}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${p.color}`}>
                        {p.label}
                      </span>
                      {inProgress && (
                        <span className="px-2 py-0.5 bg-profTeal text-white rounded-full text-xs font-semibold">
                          IN PROGRESS
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-charcoal">
                      Contract: <span className="font-mono text-xs text-medGrey">{item.contract_id.slice(0,8)}…</span>
                    </div>
                    {item.notes && (
                      <p className="text-xs text-medGrey mt-1 truncate">{item.notes}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-xs text-medGrey">
                      <span>SLA: {item.sla_hours}h</span>
                      {item.assigned_at && <span>Assigned: {fmtDateTime(item.assigned_at)}</span>}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex-shrink-0 flex flex-col items-end gap-2">
                    {item.due_at && (
                      <span className={`text-xs font-semibold flex items-center gap-1 ${t.urgent ? 'text-red-600' : 'text-medGrey'}`}>
                        <Clock className="w-3.5 h-3.5" />{t.label}
                      </span>
                    )}
                    {isQueued && (
                      <button
                        onClick={() => accept(item.id)}
                        disabled={actioning === item.id}
                        className="flex items-center gap-1.5 px-4 py-2 bg-profTeal text-white rounded-lg text-sm font-medium hover:bg-profDark disabled:opacity-50 transition-colors"
                      >
                        <Play className="w-3.5 h-3.5" /> Accept
                      </button>
                    )}
                    {inProgress && (
                      <a
                        href={`/reviews/submit?contract=${item.contract_id}`}
                        className="flex items-center gap-1.5 px-4 py-2 bg-profTeal text-white rounded-lg text-sm font-medium hover:bg-profDark transition-colors"
                      >
                        Submit Review →
                      </a>
                    )}
                    {['completed','expired','reassigned'].includes(item.status) && (
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        item.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {item.status}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
