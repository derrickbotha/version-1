'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Loader2, FileText, DollarSign, AlertTriangle, CheckCircle,
  RefreshCw, ChevronDown, ChevronUp, Send
} from 'lucide-react'
import {
  getContracts, getWallet, createEscrow, startContract,
  getContractSubmissions, getContractPayment, createSubmission, approveSubmission,
  requestRevision, releasePayment, openDispute,
  type ContractData, type SubmissionData, type WalletData, type PaymentData,
} from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'

interface StoredUser { id: string; role: string; first_name: string }

const statusColors: Record<string, string> = {
  accepted: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-indigo-100 text-indigo-700',
  submitted: 'bg-purple-100 text-purple-700',
  revision_requested: 'bg-orange-100 text-orange-700',
  completed: 'bg-green-100 text-green-700',
  disputed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

function ContractCard({ contract, user, wallet, onRefresh }: {
  contract: ContractData
  user: StoredUser
  wallet: WalletData | null
  onRefresh: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [submissions, setSubmissions] = useState<SubmissionData[]>([])
  const [payment, setPayment] = useState<PaymentData | null | 'none'>('none')
  const [subsLoading, setSubsLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submissionNotes, setSubmissionNotes] = useState('')
  const [revisionMsg, setRevisionMsg] = useState('')
  const [disputeReason, setDisputeReason] = useState('')
  const [showSubmitForm, setShowSubmitForm] = useState(false)
  const [showRevisionForm, setShowRevisionForm] = useState<string | null>(null)
  const [showDisputeForm, setShowDisputeForm] = useState(false)

  const isStudent = user.role === 'student'
  const isResearcher = user.role === 'researcher'
  const latestSub = submissions[submissions.length - 1]

  async function loadSubmissions() {
    setSubsLoading(true)
    try {
      const res = await getContractSubmissions(contract.id)
      setSubmissions(res.data?.items || [])
    } catch { /* ignore */ }
    finally { setSubsLoading(false) }
  }

  async function loadPayment() {
    try {
      const res = await getContractPayment(contract.id)
      setPayment(res.data ?? null)
    } catch {
      setPayment(null)
    }
  }

  async function toggle() {
    if (!expanded) {
      await Promise.all([loadSubmissions(), loadPayment()])
    }
    setExpanded(v => !v)
  }

  async function act(key: string, fn: () => Promise<unknown>) {
    setActionLoading(key)
    setError('')
    setSuccess('')
    try {
      await fn()
      setSuccess('Done!')
      await Promise.all([loadSubmissions(), loadPayment()])
      onRefresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed.')
    } finally {
      setActionLoading('')
    }
  }

  async function handleEscrow() {
    const balance = Number(wallet?.balance || 0)
    const price = Number(contract.agreed_price)
    if (balance < price) { setError(`Insufficient wallet balance. You have ${formatCurrency(balance)}, need ${formatCurrency(price)}. Please deposit funds.`); return }
    await act('escrow', () => createEscrow({
      contract_id: contract.id,
      payment_provider: 'wallet',
      provider_reference: `wallet-${Date.now()}`,
    }))
  }

  async function handleStart() {
    await act('start', () => startContract(contract.id))
  }

  async function handleSubmit() {
    if (submissionNotes.length < 10) { setError('Submission notes must be at least 10 characters.'); return }
    await act('submit', async () => {
      await createSubmission({ contract_id: contract.id, submission_notes: submissionNotes })
      setSubmissionNotes('')
      setShowSubmitForm(false)
    })
  }

  async function handleApprove(subId: string) {
    await act('approve', () => approveSubmission(subId))
  }

  async function handleRevision(subId: string) {
    if (revisionMsg.length < 10) { setError('Revision message must be at least 10 characters.'); return }
    await act('revision', async () => {
      await requestRevision(subId, revisionMsg)
      setRevisionMsg('')
      setShowRevisionForm(null)
    })
  }

  async function handleRelease() {
    await act('release', () => releasePayment(contract.id))
  }

  async function handleDispute() {
    if (disputeReason.length < 20) { setError('Dispute reason must be at least 20 characters.'); return }
    await act('dispute', async () => {
      await openDispute({ contract_id: contract.id, reason: disputeReason })
      setDisputeReason('')
      setShowDisputeForm(false)
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl border border-divider overflow-hidden"
    >
      {/* Header */}
      <button onClick={toggle} className="w-full text-left p-6 flex items-start justify-between gap-4 hover:bg-lightGrey/30 transition-colors">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusColors[contract.status] || 'bg-gray-100 text-gray-500'}`}>
              {contract.status.replace(/_/g, ' ')}
            </span>
            <span className="text-xs text-medGrey">Contract #{contract.id.slice(0, 8)}</span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-1 font-semibold text-charcoal">
              <DollarSign className="w-4 h-4 text-ctaBlue" />
              {formatCurrency(Number(contract.agreed_price))}
            </span>
            <span className="text-medGrey">Created {formatDate(contract.created_at)}</span>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-medGrey flex-shrink-0 mt-1" /> : <ChevronDown className="w-4 h-4 text-medGrey flex-shrink-0 mt-1" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden border-t border-divider"
          >
            <div className="p-6 space-y-5">
              {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2.5 rounded-lg">{error}</div>}
              {success && <div className="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-2.5 rounded-lg">{success}</div>}

              {/* STUDENT ACTIONS */}
              {isStudent && (
                <div className="space-y-3">
                  {/* Step 1: Escrow funds */}
                  {contract.status === 'accepted' && (
                    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                      <p className="text-sm font-semibold text-blue-800 mb-1">Step 1: Fund Escrow</p>
                      <p className="text-xs text-blue-700 mb-3">
                        Lock {formatCurrency(Number(contract.agreed_price))} in escrow so the researcher can start.
                        Your wallet balance: {formatCurrency(Number(wallet?.balance || 0))}.
                      </p>
                      <button
                        onClick={handleEscrow}
                        disabled={actionLoading === 'escrow'}
                        className="bg-blue-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2"
                      >
                        {actionLoading === 'escrow' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <DollarSign className="w-3.5 h-3.5" />}
                        Fund Escrow
                      </button>
                    </div>
                  )}

                  {/* Step 3: Review submission */}
                  {contract.status === 'submitted' && latestSub && (
                    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                      <p className="text-sm font-semibold text-purple-800 mb-1">Submission Received</p>
                      <p className="text-xs text-purple-700 mb-2">{latestSub.submission_notes}</p>
                      {latestSub.files?.length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs font-medium text-medGrey mb-1">Files:</p>
                          {latestSub.files.map((url, i) => (
                            <a key={i} href={url} target="_blank" rel="noreferrer"
                              className="text-xs text-ctaBlue hover:underline block"
                            >File {i + 1}</a>
                          ))}
                        </div>
                      )}
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApprove(latestSub.id)}
                          disabled={actionLoading === 'approve'}
                          className="bg-green-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-60 flex items-center gap-2"
                        >
                          {actionLoading === 'approve' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                          Approve Work
                        </button>
                        <button
                          onClick={() => setShowRevisionForm(latestSub.id)}
                          className="border border-orange-300 text-orange-700 text-sm font-semibold px-4 py-2 rounded-lg hover:bg-orange-50"
                        >
                          Request Revision
                        </button>
                      </div>
                      {showRevisionForm === latestSub.id && (
                        <div className="mt-3 space-y-2">
                          <textarea
                            value={revisionMsg}
                            onChange={e => setRevisionMsg(e.target.value)}
                            placeholder="Describe what needs to be revised (min 10 chars)..."
                            className="w-full border border-divider rounded-lg px-3 py-2 text-sm h-20 resize-none outline-none focus:border-steelBlue"
                          />
                          <button
                            onClick={() => handleRevision(latestSub.id)}
                            disabled={actionLoading === 'revision'}
                            className="bg-orange-500 text-white text-xs font-semibold px-3 py-2 rounded-lg hover:bg-orange-600 disabled:opacity-60 flex items-center gap-1.5"
                          >
                            {actionLoading === 'revision' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                            Send Revision Request
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Step 4: Release payment */}
                  {contract.status === 'completed' && payment !== 'none' && (
                    <div className={`border rounded-xl p-4 ${
                      payment?.status === 'released'
                        ? 'bg-gray-50 border-gray-200'
                        : 'bg-green-50 border-green-200'
                    }`}>
                      {payment?.status === 'escrowed' ? (
                        <>
                          <p className="text-sm font-semibold text-green-800 mb-1">Work Approved!</p>
                          <p className="text-xs text-green-700 mb-3">Release the escrowed payment to the researcher.</p>
                          <button
                            onClick={handleRelease}
                            disabled={actionLoading === 'release'}
                            className="bg-green-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-60 flex items-center gap-2"
                          >
                            {actionLoading === 'release' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <DollarSign className="w-3.5 h-3.5" />}
                            Release Payment ({formatCurrency(Number(payment.amount))})
                          </button>
                        </>
                      ) : payment?.status === 'released' ? (
                        <>
                          <p className="text-sm font-semibold text-gray-700 mb-1">Payment Released</p>
                          <p className="text-xs text-gray-500">
                            {formatCurrency(Number(payment.amount))} was sent to the researcher.
                          </p>
                        </>
                      ) : (
                        <>
                          <p className="text-sm font-semibold text-green-800 mb-1">Work Approved</p>
                          <p className="text-xs text-green-700">No escrow on file for this contract.</p>
                        </>
                      )}
                    </div>
                  )}

                  {/* Raise dispute */}
                  {['in_progress', 'submitted', 'revision_requested'].includes(contract.status) && (
                    <div>
                      {!showDisputeForm ? (
                        <button
                          onClick={() => setShowDisputeForm(true)}
                          className="flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 font-medium"
                        >
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Raise a Dispute
                        </button>
                      ) : (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-4 space-y-2">
                          <p className="text-sm font-semibold text-red-800">Open Dispute</p>
                          <textarea
                            value={disputeReason}
                            onChange={e => setDisputeReason(e.target.value)}
                            placeholder="Describe the issue in detail (min 20 chars)..."
                            className="w-full border border-red-200 rounded-lg px-3 py-2 text-sm h-24 resize-none outline-none"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={handleDispute}
                              disabled={actionLoading === 'dispute'}
                              className="bg-red-600 text-white text-xs font-semibold px-3 py-2 rounded-lg hover:bg-red-700 disabled:opacity-60 flex items-center gap-1.5"
                            >
                              {actionLoading === 'dispute' ? <Loader2 className="w-3 h-3 animate-spin" /> : <AlertTriangle className="w-3 h-3" />}
                              Submit Dispute
                            </button>
                            <button onClick={() => setShowDisputeForm(false)} className="text-xs text-medGrey hover:text-charcoal">Cancel</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* RESEARCHER ACTIONS */}
              {isResearcher && (
                <div className="space-y-3">
                  {/* Start contract */}
                  {contract.status === 'accepted' && (
                    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                      <p className="text-sm font-semibold text-blue-800 mb-1">Contract Accepted</p>
                      <p className="text-xs text-blue-700 mb-3">Once the student funds escrow, you can start working.</p>
                      <button
                        onClick={handleStart}
                        disabled={actionLoading === 'start'}
                        className="bg-blue-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2"
                      >
                        {actionLoading === 'start' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                        Start Working
                      </button>
                    </div>
                  )}

                  {/* Submit work */}
                  {contract.status === 'in_progress' && (
                    <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
                      <p className="text-sm font-semibold text-indigo-800 mb-1">Submit Your Work</p>
                      {!showSubmitForm ? (
                        <button
                          onClick={() => setShowSubmitForm(true)}
                          className="bg-indigo-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-indigo-700 flex items-center gap-2"
                        >
                          <FileText className="w-3.5 h-3.5" /> Submit Work
                        </button>
                      ) : (
                        <div className="space-y-2">
                          <textarea
                            value={submissionNotes}
                            onChange={e => setSubmissionNotes(e.target.value)}
                            placeholder="Describe what you've delivered (min 10 chars)..."
                            className="w-full border border-divider rounded-lg px-3 py-2 text-sm h-24 resize-none outline-none focus:border-steelBlue"
                          />
                          <p className="text-xs text-medGrey">Note: File upload requires S3 configuration.</p>
                          <div className="flex gap-2">
                            <button
                              onClick={handleSubmit}
                              disabled={actionLoading === 'submit'}
                              className="bg-indigo-600 text-white text-xs font-semibold px-3 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-60 flex items-center gap-1.5"
                            >
                              {actionLoading === 'submit' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                              Submit
                            </button>
                            <button onClick={() => setShowSubmitForm(false)} className="text-xs text-medGrey hover:text-charcoal">Cancel</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Revision requested */}
                  {contract.status === 'revision_requested' && latestSub && (
                    <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
                      <p className="text-sm font-semibold text-orange-800 mb-1">Revision Requested</p>
                      <p className="text-xs text-orange-700 mb-3">
                        The student has requested changes. Submit revised work when ready.
                      </p>
                      {!showSubmitForm ? (
                        <button onClick={() => setShowSubmitForm(true)} className="bg-orange-500 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-orange-600 flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5" /> Submit Revision
                        </button>
                      ) : (
                        <div className="space-y-2">
                          <textarea
                            value={submissionNotes}
                            onChange={e => setSubmissionNotes(e.target.value)}
                            placeholder="Describe the revisions made (min 10 chars)..."
                            className="w-full border border-divider rounded-lg px-3 py-2 text-sm h-20 resize-none outline-none"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={handleSubmit}
                              disabled={actionLoading === 'submit'}
                              className="bg-orange-500 text-white text-xs font-semibold px-3 py-2 rounded-lg hover:bg-orange-600 disabled:opacity-60 flex items-center gap-1.5"
                            >
                              {actionLoading === 'submit' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                              Submit Revision
                            </button>
                            <button onClick={() => setShowSubmitForm(false)} className="text-xs text-medGrey hover:text-charcoal">Cancel</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Researcher can also raise dispute */}
                  {['in_progress', 'submitted', 'revision_requested'].includes(contract.status) && (
                    <div>
                      {!showDisputeForm ? (
                        <button onClick={() => setShowDisputeForm(true)} className="flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 font-medium">
                          <AlertTriangle className="w-3.5 h-3.5" /> Raise a Dispute
                        </button>
                      ) : (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-4 space-y-2">
                          <p className="text-sm font-semibold text-red-800">Open Dispute</p>
                          <textarea
                            value={disputeReason}
                            onChange={e => setDisputeReason(e.target.value)}
                            placeholder="Describe the issue in detail (min 20 chars)..."
                            className="w-full border border-red-200 rounded-lg px-3 py-2 text-sm h-20 resize-none outline-none"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={handleDispute}
                              disabled={actionLoading === 'dispute'}
                              className="bg-red-600 text-white text-xs font-semibold px-3 py-2 rounded-lg hover:bg-red-700 disabled:opacity-60 flex items-center gap-1.5"
                            >
                              {actionLoading === 'dispute' ? <Loader2 className="w-3 h-3 animate-spin" /> : <AlertTriangle className="w-3 h-3" />}
                              Submit Dispute
                            </button>
                            <button onClick={() => setShowDisputeForm(false)} className="text-xs text-medGrey hover:text-charcoal">Cancel</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Submissions history */}
              {submissions.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-medGrey uppercase tracking-wide mb-2">Submission History</h4>
                  <div className="space-y-2">
                    {submissions.map((sub) => (
                      <div key={sub.id} className="bg-lightGrey rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                            sub.status === 'approved' ? 'bg-green-100 text-green-700' :
                            sub.status === 'revision_requested' ? 'bg-orange-100 text-orange-700' :
                            'bg-purple-100 text-purple-700'
                          }`}>{sub.status.replace(/_/g, ' ')}</span>
                          <span className="text-xs text-medGrey">{new Date(sub.submitted_at).toLocaleString()}</span>
                        </div>
                        <p className="text-xs text-charcoal">{sub.submission_notes}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {subsLoading && <div className="flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-medGrey" /></div>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function ContractsPage() {
  const router = useRouter()
  const [user, setUser] = useState<StoredUser | null>(null)
  const [contracts, setContracts] = useState<ContractData[]>([])
  const [wallet, setWallet] = useState<WalletData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const [contractsRes, walletRes] = await Promise.allSettled([getContracts(), getWallet()])
      if (contractsRes.status === 'fulfilled') setContracts(contractsRes.value.data?.items || [])
      if (walletRes.status === 'fulfilled') setWallet(walletRes.value.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load contracts.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!localStorage.getItem('auth_token')) { router.push('/auth/login'); return }
    const userData = localStorage.getItem('user')
    if (userData) setUser(JSON.parse(userData))
    load()
  }, [router, load])

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[900px] mx-auto px-6 py-10">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-display text-3xl font-semibold text-charcoal">My Contracts</h1>
            <p className="text-medGrey mt-1 text-sm">Manage your active and completed research orders</p>
          </div>
          <div className="flex items-center gap-3">
            {wallet && (
              <div className="bg-white border border-divider rounded-xl px-4 py-2 text-sm">
                <span className="text-medGrey">Wallet: </span>
                <span className="font-semibold text-charcoal">{formatCurrency(Number(wallet.balance))}</span>
              </div>
            )}
            <button onClick={load} className="flex items-center gap-1.5 text-sm text-medGrey hover:text-charcoal border border-divider rounded-xl px-3 py-2">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
          </div>
        </motion.div>

        {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-5">{error}</div>}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-ctaBlue" />
          </div>
        ) : contracts.length === 0 ? (
          <div className="bg-white rounded-2xl border border-divider p-12 text-center">
            <div className="w-16 h-16 bg-lightGrey rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="w-7 h-7 text-medGrey" />
            </div>
            <h3 className="font-display text-xl font-semibold text-charcoal mb-2">No contracts yet</h3>
            <p className="text-medGrey text-sm">
              {user?.role === 'student'
                ? 'Post a job and accept a researcher\'s bid to create a contract.'
                : 'Browse the marketplace and place bids to get contracts.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {user && contracts.map(c => (
              <ContractCard key={c.id} contract={c} user={user} wallet={wallet} onRefresh={load} />
            ))}
          </div>
        )}

        {/* Quick deposit link */}
        {user?.role === 'student' && wallet && Number(wallet.balance) === 0 && contracts.some(c => c.status === 'accepted') && (
          <div className="mt-5 bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm px-4 py-3 rounded-lg">
            You have accepted contracts but your wallet is empty.{' '}
            <a href="/wallet" className="font-semibold underline">Deposit funds →</a>
          </div>
        )}
      </div>
    </div>
  )
}
