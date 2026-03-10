'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { CheckCircle, XCircle, RefreshCw, AlertTriangle } from 'lucide-react'
import { api } from '@/lib/api'

const GRADE = (s: number) =>
  s >= 90 ? { label: 'A — Excellent', color: 'text-green-600' } :
  s >= 80 ? { label: 'B — Good',      color: 'text-teal-600'  } :
  s >= 70 ? { label: 'C — Satisfactory', color: 'text-yellow-600' } :
  s >= 60 ? { label: 'D — Poor',      color: 'text-orange-600' } :
            { label: 'F — Fail',      color: 'text-red-600'   }

function SubmitReviewForm() {
  const router = useRouter()
  const params = useSearchParams()
  const contractId = params.get('contract') ?? ''

  const [score,        setScore]        = useState(80)
  const [originality,  setOriginality]  = useState(90)
  const [feedback,     setFeedback]     = useState('')
  const [verdict,      setVerdict]      = useState<'approved'|'revision_required'|'rejected'>('approved')
  const [submitting,   setSubmitting]   = useState(false)
  const [error,        setError]        = useState('')
  const [success,      setSuccess]      = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!contractId) { setError('No contract ID in URL'); return }
    if (feedback.length < 50) { setError('Feedback must be at least 50 characters'); return }
    setError('')
    setSubmitting(true)
    try {
      await api.submitReview(contractId, { score, originality_score: originality, feedback, verdict })
      setSuccess(true)
      setTimeout(() => router.push('/reviews'), 2000)
    } catch (err: any) {
      setError(err.message || 'Failed to submit review')
    } finally {
      setSubmitting(false)
    }
  }

  const grade = GRADE(score)

  if (success) return (
    <div className="p-8 max-w-2xl">
      <div className="bg-white border border-green-200 rounded-2xl p-10 text-center">
        <CheckCircle className="w-14 h-14 text-green-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-charcoal">Review Submitted</h2>
        <p className="text-medGrey text-sm mt-2">Redirecting to your reviews…</p>
      </div>
    </div>
  )

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-charcoal">Submit Quality Review</h1>
        <p className="text-medGrey text-sm mt-1">
          Contract: <span className="font-mono text-xs">{contractId.slice(0,8)}…</span>
        </p>
      </div>

      {error && (
        <div className="mb-5 flex items-start gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />{error}
        </div>
      )}

      <form onSubmit={submit} className="space-y-6">

        {/* Quality Score */}
        <div className="bg-white border border-divider rounded-xl p-5">
          <label className="block text-sm font-semibold text-charcoal mb-3">
            Quality Score: <span className={`text-xl font-bold ${grade.color}`}>{score}</span>
            <span className={`ml-2 text-sm font-medium ${grade.color}`}>{grade.label}</span>
          </label>
          <input
            type="range" min={0} max={100} value={score}
            onChange={e => setScore(Number(e.target.value))}
            className="w-full accent-profTeal"
          />
          <div className="flex justify-between text-xs text-medGrey mt-1">
            <span>0 — Fail</span><span>50</span><span>100 — Perfect</span>
          </div>
        </div>

        {/* Originality Score */}
        <div className="bg-white border border-divider rounded-xl p-5">
          <label className="block text-sm font-semibold text-charcoal mb-3">
            Originality Score: <span className="font-bold text-charcoal">{originality}%</span>
            <span className="ml-2 text-xs text-medGrey">(100 = fully original)</span>
          </label>
          <input
            type="range" min={0} max={100} value={originality}
            onChange={e => setOriginality(Number(e.target.value))}
            className="w-full accent-profTeal"
          />
          {originality < 70 && (
            <p className="text-xs text-orange-600 mt-1 flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" /> Below 70% — may indicate plagiarism
            </p>
          )}
        </div>

        {/* Feedback */}
        <div className="bg-white border border-divider rounded-xl p-5">
          <label className="block text-sm font-semibold text-charcoal mb-2">
            Feedback <span className="font-normal text-medGrey">(min 50 characters)</span>
          </label>
          <textarea
            required
            rows={6}
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="Provide detailed feedback on the quality, accuracy, originality, and areas for improvement…"
            className="w-full px-4 py-3 border border-divider rounded-lg text-sm text-charcoal placeholder:text-medGrey resize-none"
          />
          <div className={`text-xs mt-1 text-right ${feedback.length < 50 ? 'text-orange-500' : 'text-green-600'}`}>
            {feedback.length} / 50 min chars
          </div>
        </div>

        {/* Verdict */}
        <div className="bg-white border border-divider rounded-xl p-5">
          <label className="block text-sm font-semibold text-charcoal mb-3">Verdict</label>
          <div className="grid grid-cols-3 gap-3">
            {([
              { val: 'approved',          label: 'Approve',  sub: 'Work meets standards',   icon: CheckCircle, color: 'border-green-500 bg-green-50 text-green-700'  },
              { val: 'revision_required', label: 'Revise',   sub: 'Needs improvement',       icon: RefreshCw,   color: 'border-yellow-500 bg-yellow-50 text-yellow-700'},
              { val: 'rejected',          label: 'Reject',   sub: 'Unacceptable quality',    icon: XCircle,     color: 'border-red-500 bg-red-50 text-red-700'         },
            ] as const).map(({ val, label, sub, icon: Icon, color }) => (
              <button
                key={val}
                type="button"
                onClick={() => setVerdict(val)}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                  verdict === val ? color : 'border-divider hover:border-medGrey bg-white'
                }`}
              >
                <Icon className="w-6 h-6" />
                <span className="text-sm font-semibold">{label}</span>
                <span className="text-[10px] opacity-70 text-center">{sub}</span>
              </button>
            ))}
          </div>
          {verdict === 'rejected' && (
            <p className="mt-3 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
              Rejection will move the contract to <strong>disputed</strong> status. An admin will handle the financial resolution.
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={submitting || feedback.length < 50}
          className="w-full py-3 bg-profTeal text-white rounded-xl font-semibold text-sm hover:bg-profDark disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Submitting…' : 'Submit Review'}
        </button>
      </form>
    </div>
  )
}

export default function SubmitReviewPage() {
  return (
    <Suspense>
      <SubmitReviewForm />
    </Suspense>
  )
}
