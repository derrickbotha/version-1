'use client'

import { useEffect, useState } from 'react'
import { Star, CheckCircle, RefreshCw, AlertTriangle, RotateCcw } from 'lucide-react'
import { api, QualityReview } from '@/lib/api'
import { fmtDateTime } from '@/lib/utils'

const STATUS_STYLE: Record<string, string> = {
  approved:          'bg-green-100 text-green-700',
  revision_required: 'bg-yellow-100 text-yellow-700',
  rejected:          'bg-red-100 text-red-700',
  pending:           'bg-blue-100 text-blue-700',
  in_review:         'bg-purple-100 text-purple-700',
}

const GRADE = (s: number) =>
  s >= 90 ? 'A' : s >= 80 ? 'B' : s >= 70 ? 'C' : s >= 60 ? 'D' : 'F'

const GRADE_COLOR = (s: number) =>
  s >= 90 ? 'text-green-600' : s >= 80 ? 'text-teal-600' : s >= 70 ? 'text-yellow-600' : s >= 60 ? 'text-orange-600' : 'text-red-600'

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<QualityReview[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try { setReviews(await api.getMyReviews()) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const totalEarned = reviews.filter(r => r.fee_paid).reduce((sum, r) => sum + r.fee_amount, 0)
  const avgScore    = reviews.filter(r => r.score != null).length
    ? reviews.filter(r => r.score != null).reduce((s, r) => s + (r.score ?? 0), 0) / reviews.filter(r => r.score != null).length
    : 0

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Quality Reviews</h1>
          <p className="text-medGrey text-sm mt-1">{reviews.length} reviews · avg score {avgScore.toFixed(1)}</p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="/reviews/submit"
            className="px-4 py-2 bg-profTeal text-white rounded-lg text-sm font-medium hover:bg-profDark transition-colors"
          >
            + New Review
          </a>
          <button onClick={load} className="p-2 bg-white border border-divider rounded-lg hover:bg-lightGrey transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Approved',   count: reviews.filter(r=>r.status==='approved').length,          color: 'text-green-600'  },
          { label: 'Revisions',  count: reviews.filter(r=>r.status==='revision_required').length, color: 'text-yellow-600' },
          { label: 'Rejected',   count: reviews.filter(r=>r.status==='rejected').length,          color: 'text-red-600'    },
        ].map(({ label, count, color }) => (
          <div key={label} className="bg-white border border-divider rounded-xl px-5 py-4 text-center">
            <div className={`text-2xl font-bold ${color}`}>{count}</div>
            <div className="text-xs text-medGrey mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="py-12 flex items-center justify-center gap-2 text-medGrey">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading…
        </div>
      ) : reviews.length === 0 ? (
        <div className="py-16 text-center">
          <Star className="w-10 h-10 text-medGrey mx-auto mb-3 opacity-30" />
          <p className="text-medGrey">No reviews submitted yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map(r => (
            <div key={r.id} className="bg-white border border-divider rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLE[r.status]}`}>
                      {r.status.replace(/_/g,' ')}
                    </span>
                    <span className="text-xs text-medGrey">Round {r.round_number}</span>
                    {r.payment_held && (
                      <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full text-xs">Payment Held</span>
                    )}
                  </div>
                  <div className="text-sm text-charcoal">
                    Contract: <span className="font-mono text-xs text-medGrey">{r.contract_id.slice(0,8)}…</span>
                  </div>
                  {r.feedback && (
                    <p className="text-xs text-medGrey mt-1.5 line-clamp-2">{r.feedback}</p>
                  )}
                  {r.reviewed_at && (
                    <div className="text-xs text-medGrey mt-1">{fmtDateTime(r.reviewed_at)}</div>
                  )}
                </div>
                <div className="flex-shrink-0 text-right space-y-1">
                  {r.score != null && (
                    <div>
                      <span className={`text-3xl font-bold ${GRADE_COLOR(r.score)}`}>{GRADE(r.score)}</span>
                      <span className="text-xs text-medGrey ml-1">{r.score}/100</span>
                    </div>
                  )}
                  {r.originality_score != null && (
                    <div className="text-xs text-medGrey">
                      Originality: {r.originality_score}%
                    </div>
                  )}
                  <div className={`text-xs font-medium ${r.fee_paid ? 'text-green-600' : 'text-medGrey'}`}>
                    ${r.fee_amount.toFixed(2)} {r.fee_paid ? '(paid)' : '(pending)'}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
