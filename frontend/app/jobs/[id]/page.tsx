'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Clock, DollarSign, Loader2, CheckCircle, XCircle, User } from 'lucide-react'
import { getJob, getJobBids, placeBid, acceptBid, rejectBid, type JobData, type BidData } from '@/lib/api'
import { formatCurrency, formatDate, formatRelativeDate } from '@/lib/utils'

interface StoredUser { id: string; role: string; first_name: string }

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [user, setUser] = useState<StoredUser | null>(null)
  const [job, setJob] = useState<JobData | null>(null)
  const [bids, setBids] = useState<BidData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [bidPrice, setBidPrice] = useState('')
  const [bidMessage, setBidMessage] = useState('')
  const [bidLoading, setBidLoading] = useState(false)
  const [bidError, setBidError] = useState('')
  const [bidSuccess, setBidSuccess] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (!localStorage.getItem('auth_token')) { router.push('/auth/login'); return }
    if (userData) setUser(JSON.parse(userData))

    async function load() {
      try {
        const [jobRes, bidsRes] = await Promise.allSettled([
          getJob(id),
          getJobBids(id),
        ])
        if (jobRes.status === 'fulfilled') setJob(jobRes.value.data)
        else setError('Job not found.')
        if (bidsRes.status === 'fulfilled') setBids(bidsRes.value.data?.items || [])
      } catch {
        setError('Failed to load job.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id, router])

  async function handleBid(e: React.FormEvent) {
    e.preventDefault()
    setBidError('')
    if (!bidPrice || Number(bidPrice) <= 0) { setBidError('Enter a valid price.'); return }
    if (bidMessage.length < 10) { setBidError('Message must be at least 10 characters.'); return }
    setBidLoading(true)
    try {
      await placeBid(id, { proposed_price: Number(bidPrice).toFixed(2), message: bidMessage })
      setBidSuccess(true)
      setBidPrice(''); setBidMessage('')
    } catch (err) {
      setBidError(err instanceof Error ? err.message : 'Failed to place bid.')
    } finally {
      setBidLoading(false)
    }
  }

  async function handleAccept(bidId: string) {
    setActionLoading(bidId)
    try {
      await acceptBid(bidId)
      router.push('/contracts')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept bid.')
    } finally {
      setActionLoading(null)
    }
  }

  async function handleReject(bidId: string) {
    setActionLoading(bidId + '-reject')
    try {
      await rejectBid(bidId)
      const bidsRes = await getJobBids(id)
      setBids(bidsRes.data?.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject bid.')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-lightGrey flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-ctaBlue" />
    </div>
  )

  if (error && !job) return (
    <div className="min-h-screen bg-lightGrey flex flex-col items-center justify-center gap-4">
      <p className="text-red-600">{error}</p>
      <Link href="/marketplace" className="text-ctaBlue hover:underline">Back to Marketplace</Link>
    </div>
  )

  const isStudent = user?.role === 'student'
  const isOwner = isStudent && job?.student_id === user?.id
  const isResearcher = user?.role === 'researcher'
  const canBid = isResearcher && job?.status === 'open' && !bidSuccess

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[900px] mx-auto px-6 py-10">
        <Link href="/marketplace" className="inline-flex items-center gap-1.5 text-sm text-medGrey hover:text-charcoal mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Marketplace
        </Link>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-5">{error}</div>
        )}

        {job && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Job details */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="lg:col-span-2 bg-white rounded-2xl border border-divider p-8"
            >
              <div className="flex items-start justify-between gap-4 mb-4">
                <h1 className="font-display text-2xl font-semibold text-charcoal leading-snug">{job.title}</h1>
                <span className={`flex-shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${
                  job.status === 'open' ? 'bg-green-100 text-green-700' :
                  job.status === 'accepted' ? 'bg-blue-100 text-blue-700' :
                  job.status === 'in_progress' ? 'bg-indigo-100 text-indigo-700' :
                  job.status === 'submitted' ? 'bg-purple-100 text-purple-700' :
                  job.status === 'revision_requested' ? 'bg-orange-100 text-orange-700' :
                  job.status === 'completed' ? 'bg-green-100 text-green-700' :
                  job.status === 'disputed' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-600'
                }`}>{job.status.replace(/_/g, ' ')}</span>
              </div>

              <p className="text-sm text-medGrey leading-relaxed mb-6">{job.description}</p>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-lightGrey rounded-xl p-4">
                  <p className="text-xs text-medGrey mb-1">Budget</p>
                  <p className="font-semibold text-charcoal flex items-center gap-1">
                    <DollarSign className="w-4 h-4 text-ctaBlue" />
                    {formatCurrency(Number(job.proposed_price))}
                  </p>
                </div>
                <div className="bg-lightGrey rounded-xl p-4">
                  <p className="text-xs text-medGrey mb-1">Deadline</p>
                  <p className="font-semibold text-charcoal flex items-center gap-1">
                    <Clock className="w-4 h-4 text-steelBlue" />
                    {formatRelativeDate(job.deadline)}
                  </p>
                </div>
                <div className="bg-lightGrey rounded-xl p-4">
                  <p className="text-xs text-medGrey mb-1">Subject</p>
                  <p className="font-semibold text-charcoal">{job.subject}</p>
                </div>
                <div className="bg-lightGrey rounded-xl p-4">
                  <p className="text-xs text-medGrey mb-1">Academic Level</p>
                  <p className="font-semibold text-charcoal">{job.academic_level}</p>
                </div>
              </div>

              <p className="text-xs text-medGrey">Posted {formatDate(job.created_at)}</p>
            </motion.div>

            {/* Sidebar: bid form (researcher) or bids list (student) */}
            <div className="space-y-4">
              {/* Researcher bid form */}
              {isResearcher && (
                <motion.div
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="bg-white rounded-2xl border border-divider p-6"
                >
                  <h2 className="font-semibold text-charcoal mb-4">Place a Bid</h2>
                  {bidSuccess ? (
                    <div className="flex flex-col items-center gap-2 py-4 text-center">
                      <CheckCircle className="w-10 h-10 text-green-500" />
                      <p className="font-medium text-charcoal">Bid Submitted!</p>
                      <p className="text-xs text-medGrey">The student will review your bid.</p>
                    </div>
                  ) : job.status !== 'open' ? (
                    <p className="text-sm text-medGrey">This job is no longer accepting bids.</p>
                  ) : (
                    <form onSubmit={handleBid} className="space-y-4">
                      {bidError && <p className="text-xs text-red-500">{bidError}</p>}
                      <div>
                        <label className="block text-xs font-medium text-medGrey mb-1">Your Price (USD)</label>
                        <input
                          type="number"
                          value={bidPrice}
                          onChange={e => setBidPrice(e.target.value)}
                          placeholder="e.g. 220"
                          min="1" step="0.01"
                          className="w-full border border-divider rounded-lg px-3 py-2.5 text-sm outline-none focus:border-steelBlue transition-colors"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-medGrey mb-1">Message (min 10 chars)</label>
                        <textarea
                          value={bidMessage}
                          onChange={e => setBidMessage(e.target.value)}
                          placeholder="Introduce yourself and explain why you're the right fit..."
                          className="w-full border border-divider rounded-lg px-3 py-2.5 text-sm h-24 resize-none outline-none focus:border-steelBlue transition-colors"
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={bidLoading}
                        className="w-full bg-ctaBlue text-white text-sm font-semibold py-3 rounded-xl hover:bg-blue-600 disabled:opacity-60 transition-all flex items-center justify-center gap-2"
                      >
                        {bidLoading ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Submitting...</> : 'Submit Bid'}
                      </button>
                    </form>
                  )}
                </motion.div>
              )}

              {/* Student: bids list */}
              {isOwner && (
                <motion.div
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="bg-white rounded-2xl border border-divider p-6"
                >
                  <h2 className="font-semibold text-charcoal mb-4">Bids ({bids.length})</h2>
                  {bids.length === 0 ? (
                    <p className="text-sm text-medGrey">No bids yet. Researchers will bid soon.</p>
                  ) : (
                    <div className="space-y-3">
                      {bids.map(bid => (
                        <div key={bid.id} className="border border-divider rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <div className="w-7 h-7 bg-steelBlue/10 rounded-full flex items-center justify-center">
                              <User className="w-3.5 h-3.5 text-steelBlue" />
                            </div>
                            <span className="text-xs text-medGrey">Researcher</span>
                            <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${
                              bid.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                              bid.status === 'accepted' ? 'bg-green-100 text-green-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>{bid.status}</span>
                          </div>
                          <p className="font-semibold text-charcoal text-sm mb-1">{formatCurrency(Number(bid.proposed_price))}</p>
                          {bid.message && <p className="text-xs text-medGrey leading-relaxed mb-3 line-clamp-3">{bid.message}</p>}
                          {bid.status === 'pending' && (
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleAccept(bid.id)}
                                disabled={actionLoading === bid.id}
                                className="flex-1 bg-green-600 text-white text-xs font-semibold py-2 rounded-lg hover:bg-green-700 disabled:opacity-60 flex items-center justify-center gap-1"
                              >
                                {actionLoading === bid.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                                Accept
                              </button>
                              <button
                                onClick={() => handleReject(bid.id)}
                                disabled={actionLoading === bid.id + '-reject'}
                                className="flex-1 border border-divider text-charcoal text-xs font-semibold py-2 rounded-lg hover:bg-lightGrey disabled:opacity-60 flex items-center justify-center gap-1"
                              >
                                {actionLoading === bid.id + '-reject' ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                                Reject
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
