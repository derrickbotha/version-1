'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, RefreshCw, Scale, CheckCircle } from 'lucide-react'
import { api, QueueItem, RulingPayload } from '@/lib/api'
import { timeUntil, fmtDateTime } from '@/lib/utils'

const RULINGS = [
  { val: 'full_release',   label: 'Full Release',   sub: 'Pay researcher 100%',         color: 'border-green-500 bg-green-50 text-green-700'   },
  { val: 'partial_release',label: 'Partial Release', sub: 'Pay researcher a percentage', color: 'border-yellow-500 bg-yellow-50 text-yellow-700' },
  { val: 'full_refund',    label: 'Full Refund',    sub: 'Refund student entirely',      color: 'border-red-500 bg-red-50 text-red-700'          },
  { val: 'revision',       label: 'Revision',       sub: 'One more revision round',      color: 'border-blue-500 bg-blue-50 text-blue-700'       },
] as const

export default function DisputesPage() {
  const [items, setItems]         = useState<QueueItem[]>([])
  const [loading, setLoading]     = useState(true)
  const [activeId, setActiveId]   = useState<string | null>(null)
  const [flash, setFlash]         = useState('')

  const [ruling, setRuling]       = useState<RulingPayload['ruling']>('full_release')
  const [pct,    setPct]          = useState(50)
  const [reason, setReason]       = useState('')
  const [evidence, setEvidence]   = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function load() {
    setLoading(true)
    try { setItems(await api.getDisputes()) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function submitRuling(disputeId: string) {
    if (reason.length < 100) { setFlash('Reasoning must be at least 100 characters'); return }
    setSubmitting(true)
    try {
      await api.submitRuling(disputeId, {
        ruling,
        release_percentage: ruling === 'partial_release' ? pct : undefined,
        reasoning: reason,
        evidence_reviewed: evidence || undefined,
      })
      setFlash('Ruling submitted — admin will execute the financial outcome')
      setActiveId(null)
      setReason('')
      setEvidence('')
      load()
    } catch (err: any) { setFlash(err.message) }
    finally { setSubmitting(false) }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Dispute Arbitration</h1>
          <p className="text-medGrey text-sm mt-1">{items.length} disputes assigned to you</p>
        </div>
        <button onClick={load} className="p-2 bg-white border border-divider rounded-lg hover:bg-lightGrey">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-profLight border border-profTeal/30 rounded-lg text-profTeal text-sm flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />{flash}
        </div>
      )}

      {loading ? (
        <div className="py-12 flex items-center justify-center gap-2 text-medGrey">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading…
        </div>
      ) : items.length === 0 ? (
        <div className="py-16 text-center">
          <Scale className="w-12 h-12 text-medGrey mx-auto mb-3 opacity-30" />
          <p className="text-charcoal font-medium">No disputes assigned</p>
          <p className="text-medGrey text-sm mt-1">You will be notified when a dispute needs arbitration</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map(item => {
            const t       = timeUntil(item.due_at ?? null)
            const isOpen  = activeId === item.id
            return (
              <div key={item.id} className="bg-white border border-divider rounded-xl overflow-hidden">
                {/* Header */}
                <div className="p-5 flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-bold">DISPUTE</span>
                      <span className={`text-xs font-semibold ${t.urgent ? 'text-red-600' : 'text-medGrey'}`}>
                        {t.label}
                      </span>
                    </div>
                    <div className="text-sm text-charcoal">
                      Contract: <span className="font-mono text-xs text-medGrey">{item.contract_id.slice(0,8)}…</span>
                    </div>
                    {item.due_at && (
                      <div className="text-xs text-medGrey mt-0.5">Due: {fmtDateTime(item.due_at)}</div>
                    )}
                  </div>
                  {!isOpen ? (
                    <button
                      onClick={() => setActiveId(item.id)}
                      className="flex items-center gap-2 px-4 py-2 bg-profTeal text-white rounded-lg text-sm font-medium hover:bg-profDark transition-colors"
                    >
                      <Scale className="w-4 h-4" /> Submit Ruling
                    </button>
                  ) : (
                    <button
                      onClick={() => setActiveId(null)}
                      className="px-4 py-2 border border-divider rounded-lg text-sm hover:bg-lightGrey transition-colors"
                    >
                      Cancel
                    </button>
                  )}
                </div>

                {/* Ruling form */}
                {isOpen && (
                  <div className="border-t border-divider p-5 bg-lightGrey/40 space-y-5">
                    <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-700">
                      <strong>Important:</strong> Your ruling is binding. The admin will execute the financial action based on your decision. Only a super_admin can override.
                    </div>

                    {/* Ruling selector */}
                    <div>
                      <label className="block text-sm font-semibold text-charcoal mb-2">Ruling</label>
                      <div className="grid grid-cols-2 gap-2">
                        {RULINGS.map(({ val, label, sub, color }) => (
                          <button
                            key={val}
                            type="button"
                            onClick={() => setRuling(val)}
                            className={`p-3 rounded-xl border-2 text-left transition-all ${ruling === val ? color : 'border-divider bg-white'}`}
                          >
                            <div className="text-sm font-semibold">{label}</div>
                            <div className="text-xs opacity-70 mt-0.5">{sub}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Percentage for partial */}
                    {ruling === 'partial_release' && (
                      <div>
                        <label className="block text-sm font-semibold text-charcoal mb-2">
                          Release Percentage: <span className="text-profTeal font-bold">{pct}%</span>
                        </label>
                        <input type="range" min={0} max={100} value={pct}
                          onChange={e => setPct(Number(e.target.value))}
                          className="w-full accent-profTeal" />
                        <div className="flex justify-between text-xs text-medGrey mt-1">
                          <span>0% — full refund to student</span>
                          <span>100% — full payment to researcher</span>
                        </div>
                      </div>
                    )}

                    {/* Evidence */}
                    <div>
                      <label className="block text-sm font-semibold text-charcoal mb-1.5">Evidence Reviewed (optional)</label>
                      <textarea rows={3} value={evidence} onChange={e => setEvidence(e.target.value)}
                        placeholder="Briefly summarise the materials you reviewed (contract spec, submissions, message history)…"
                        className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal bg-white resize-none" />
                    </div>

                    {/* Reasoning */}
                    <div>
                      <label className="block text-sm font-semibold text-charcoal mb-1.5">
                        Reasoning <span className="font-normal text-medGrey">(min 100 chars)</span>
                      </label>
                      <textarea rows={5} value={reason} onChange={e => setReason(e.target.value)}
                        placeholder="Provide your detailed academic reasoning for this ruling…"
                        className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal bg-white resize-none" />
                      <div className={`text-xs mt-1 text-right ${reason.length < 100 ? 'text-orange-500' : 'text-green-600'}`}>
                        {reason.length} / 100 min chars
                      </div>
                    </div>

                    <button
                      onClick={() => submitRuling(item.id)}
                      disabled={submitting || reason.length < 100}
                      className="w-full py-3 bg-profTeal text-white rounded-xl font-semibold text-sm hover:bg-profDark disabled:opacity-50 transition-colors"
                    >
                      {submitting ? 'Submitting…' : 'Submit Binding Ruling'}
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
