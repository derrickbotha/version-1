'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import {
  ArrowLeft, DollarSign, Clock, BookOpen, GraduationCap,
  CheckCircle, AlertCircle, Send, RefreshCw, Briefcase,
} from 'lucide-react'
import { api, Job, Bid } from '@/lib/api'

function timeLeft(deadline: string) {
  const diff = new Date(deadline).getTime() - Date.now()
  if (diff < 0) return { label: 'Deadline passed', urgent: true }
  const days = Math.floor(diff / 86400000)
  if (days > 0) return { label: `${days} day${days !== 1 ? 's' : ''} remaining`, urgent: days <= 2 }
  const hrs = Math.floor(diff / 3600000)
  return { label: `${hrs} hour${hrs !== 1 ? 's' : ''} remaining`, urgent: true }
}

export default function JobDetailPage() {
  const router = useRouter()
  const { id } = useParams<{ id: string }>()

  const [job,          setJob]          = useState<Job | null>(null)
  const [loading,      setLoading]      = useState(true)
  const [submitting,   setSubmitting]   = useState(false)
  const [success,      setSuccess]      = useState(false)
  const [error,        setError]        = useState('')
  const [myBids,       setMyBids]       = useState<Bid[]>([])

  // Bid form state
  const [price,   setPrice]   = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!id) return
    Promise.all([
      api.getJob(id),
      api.getMyBids().catch(() => ({ items: [] as Bid[], total: 0 })),
    ]).then(([j, b]) => {
      setJob(j)
      setMyBids(b.items)
      setPrice(j.proposed_price)
    }).catch(e => {
      if (e.message?.includes('401')) router.push('/auth/login')
    }).finally(() => setLoading(false))
  }, [id])

  const existingBid = myBids.find(b => b.job_id === id && ['pending', 'countered'].includes(b.status))

  async function submitBid(e: React.FormEvent) {
    e.preventDefault()
    if (!price || !message.trim()) {
      setError('Both price and message are required.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await api.bidOnJob(id, { proposed_price: price, message: message.trim() })
      setSuccess(true)
      // Refresh bids
      const b = await api.getMyBids().catch(() => ({ items: [] as Bid[], total: 0 }))
      setMyBids(b.items)
    } catch (e: any) {
      setError(e.message || 'Failed to place bid.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return (
    <div className="p-8 flex items-center gap-3 text-medGrey">
      <RefreshCw className="w-5 h-5 animate-spin" /> Loading job…
    </div>
  )

  if (!job) return (
    <div className="p-8 text-medGrey">Job not found.</div>
  )

  const t = timeLeft(job.deadline)

  return (
    <div className="p-8 max-w-4xl">
      {/* Back */}
      <button
        onClick={() => router.push('/jobs')}
        className="flex items-center gap-1.5 text-sm text-medGrey hover:text-profTeal transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to marketplace
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Job detail — left 2 cols */}
        <div className="lg:col-span-2 space-y-5">
          {/* Header card */}
          <div className="bg-white border border-divider rounded-xl p-6">
            <div className="flex items-start justify-between gap-3 mb-4">
              <h1 className="text-xl font-bold text-charcoal leading-snug">{job.title}</h1>
              <span className={`flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wide
                ${job.status === 'open' ? 'bg-green-100 text-green-700' :
                  job.status === 'negotiation' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-500'}`}>
                {job.status}
              </span>
            </div>

            {/* Meta pills */}
            <div className="flex flex-wrap gap-2 mb-5">
              {job.subject && (
                <span className="flex items-center gap-1.5 px-3 py-1.5 bg-lightGrey rounded-lg text-xs font-medium text-charcoal">
                  <BookOpen className="w-3.5 h-3.5 text-profTeal" /> {job.subject}
                </span>
              )}
              {job.academic_level && (
                <span className="flex items-center gap-1.5 px-3 py-1.5 bg-lightGrey rounded-lg text-xs font-medium text-charcoal">
                  <GraduationCap className="w-3.5 h-3.5 text-profTeal" /> {job.academic_level}
                </span>
              )}
              <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${t.urgent ? 'bg-red-50 text-red-600' : 'bg-lightGrey text-charcoal'}`}>
                <Clock className={`w-3.5 h-3.5 ${t.urgent ? 'text-red-500' : 'text-profTeal'}`} /> {t.label}
              </span>
            </div>

            {/* Budget */}
            <div className="flex items-center gap-2 p-4 bg-emerald-50 rounded-xl border border-emerald-100 mb-5">
              <DollarSign className="w-5 h-5 text-emerald-600 flex-shrink-0" />
              <div>
                <p className="text-xs text-emerald-700 font-medium">Student Budget</p>
                <p className="text-2xl font-bold text-emerald-700">${Number(job.proposed_price).toFixed(2)}</p>
              </div>
            </div>

            {/* Description */}
            <div>
              <h2 className="text-sm font-semibold text-charcoal mb-2">Job Description</h2>
              <p className="text-sm text-medGrey leading-relaxed whitespace-pre-wrap">{job.description}</p>
            </div>
          </div>

          {/* My existing bid */}
          {existingBid && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-blue-800">You already have an active bid</p>
                <p className="text-xs text-blue-600 mt-1">
                  Bid of <strong>${Number(existingBid.proposed_price).toFixed(2)}</strong> · Status: <strong>{existingBid.status}</strong>
                </p>
                <p className="text-xs text-blue-500 mt-0.5 italic">
                  "{existingBid.message}"
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Bid form — right col */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-divider rounded-xl p-5 sticky top-6">
            <h2 className="text-sm font-semibold text-charcoal mb-4 flex items-center gap-2">
              <Send className="w-4 h-4 text-profTeal" />
              {existingBid ? 'Update Your Bid' : 'Place a Bid'}
            </h2>

            {success ? (
              <div className="text-center py-6">
                <CheckCircle className="w-10 h-10 text-green-500 mx-auto mb-3" />
                <p className="text-sm font-semibold text-charcoal">Bid submitted!</p>
                <p className="text-xs text-medGrey mt-1">The student will review your proposal.</p>
                <button
                  onClick={() => { setSuccess(false); setMessage('') }}
                  className="mt-4 text-xs text-profTeal hover:underline"
                >
                  Place another bid
                </button>
              </div>
            ) : (
              <form onSubmit={submitBid} className="space-y-4">
                {/* Price */}
                <div>
                  <label className="block text-xs font-medium text-charcoal mb-1">
                    Your Price (USD)
                  </label>
                  <div className="relative">
                    <DollarSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-medGrey" />
                    <input
                      type="number"
                      step="0.01"
                      min="1"
                      value={price}
                      onChange={e => setPrice(e.target.value)}
                      className="w-full pl-8 pr-4 py-2.5 text-sm border border-divider rounded-lg focus:outline-none focus:border-profTeal"
                      placeholder="e.g. 150.00"
                      required
                    />
                  </div>
                  <p className="text-[11px] text-medGrey mt-1">
                    Student budget: ${Number(job.proposed_price).toFixed(2)}
                  </p>
                </div>

                {/* Message */}
                <div>
                  <label className="block text-xs font-medium text-charcoal mb-1">
                    Cover Letter
                  </label>
                  <textarea
                    value={message}
                    onChange={e => setMessage(e.target.value)}
                    rows={5}
                    className="w-full px-3 py-2.5 text-sm border border-divider rounded-lg focus:outline-none focus:border-profTeal resize-none"
                    placeholder="Introduce yourself, explain your expertise, and outline how you'd approach this job…"
                    required
                  />
                  <p className="text-[11px] text-medGrey mt-1">{message.length} chars</p>
                </div>

                {/* Error */}
                {error && (
                  <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={submitting || job.status !== 'open' && job.status !== 'negotiation'}
                  className="w-full py-2.5 bg-profTeal text-white rounded-lg text-sm font-semibold hover:bg-profDark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {submitting ? (
                    <><RefreshCw className="w-4 h-4 animate-spin" /> Submitting…</>
                  ) : (
                    <><Send className="w-4 h-4" /> Submit Bid</>
                  )}
                </button>

                {job.status !== 'open' && job.status !== 'negotiation' && (
                  <p className="text-xs text-center text-medGrey">
                    This job is no longer accepting bids.
                  </p>
                )}
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
