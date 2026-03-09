'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  DollarSign, Loader2, TrendingUp, TrendingDown,
  ArrowDownLeft, ArrowUpRight, CreditCard, Trash2,
  Star, AlertCircle, CheckCircle, SendHorizonal,
} from 'lucide-react'
import {
  getWallet, depositToWallet, getWalletTransactions,
  getPaymentMethods, deletePaymentMethod, setDefaultPaymentMethod,
  requestPayout, getPayouts,
  type WalletData, type WalletTransaction, type PaymentMethodData, type WriterPayoutData,
} from '@/lib/api'
import { formatCurrency } from '@/lib/utils'

const txIcons: Record<string, React.ReactNode> = {
  deposit:     <ArrowDownLeft className="w-4 h-4 text-green-500" />,
  escrow_lock: <TrendingDown className="w-4 h-4 text-orange-500" />,
  release:     <TrendingUp className="w-4 h-4 text-purple-500" />,
  refund:      <ArrowDownLeft className="w-4 h-4 text-blue-500" />,
  payout:      <ArrowUpRight className="w-4 h-4 text-rose-500" />,
}

const txLabels: Record<string, string> = {
  deposit:     'Deposit',
  escrow_lock: 'Escrow Locked',
  release:     'Payment Released',
  refund:      'Refund',
  payout:      'Payout',
}

const txSign = (type: string) => ['deposit', 'refund'].includes(type) ? '+' : '-'
const txColor = (type: string) => ['deposit', 'refund'].includes(type) ? 'text-green-600' : 'text-red-500'

const payoutStatusColors: Record<string, string> = {
  pending:    'bg-yellow-100 text-yellow-700',
  processing: 'bg-blue-100 text-blue-700',
  completed:  'bg-green-100 text-green-700',
  failed:     'bg-red-100 text-red-700',
}

export default function WalletPage() {
  const router = useRouter()

  const [user, setUser] = useState<{ role: string } | null>(null)
  const [wallet, setWallet] = useState<WalletData | null>(null)
  const [transactions, setTransactions] = useState<WalletTransaction[]>([])
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodData[]>([])
  const [payouts, setPayouts] = useState<WriterPayoutData[]>([])
  const [loading, setLoading] = useState(true)

  // Deposit
  const [depositAmount, setDepositAmount] = useState('')
  const [depositing, setDepositing] = useState(false)
  const [depositMsg, setDepositMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Payout (researcher)
  const [payoutAmount, setPayoutAmount] = useState('')
  const [payoutProvider, setPayoutProvider] = useState<'stripe' | 'paypal'>('stripe')
  const [payingOut, setPayingOut] = useState(false)
  const [payoutMsg, setPayoutMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const load = useCallback(async (role?: string) => {
    try {
      const [walletRes, txRes, pmRes] = await Promise.allSettled([
        getWallet(), getWalletTransactions(), getPaymentMethods(),
      ])
      if (walletRes.status === 'fulfilled') setWallet(walletRes.value.data)
      if (txRes.status === 'fulfilled') setTransactions(txRes.value.data?.items || [])
      if (pmRes.status === 'fulfilled') setPaymentMethods(pmRes.value.data || [])

      if (role === 'researcher') {
        const pRes = await getPayouts()
        setPayouts(pRes.data?.items || [])
      }
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (!localStorage.getItem('auth_token')) { router.push('/auth/login'); return }
    const u = localStorage.getItem('user')
    const parsed = u ? JSON.parse(u) : null
    setUser(parsed)
    load(parsed?.role)
  }, [router, load])

  async function handleDeposit(e: React.FormEvent) {
    e.preventDefault()
    const amount = Number(depositAmount)
    if (!amount || amount <= 0) { setDepositMsg({ type: 'error', text: 'Enter a valid amount.' }); return }
    setDepositing(true)
    setDepositMsg(null)
    try {
      const res = await depositToWallet({ amount })
      setWallet(res.data)
      setDepositAmount('')
      setDepositMsg({ type: 'success', text: `${formatCurrency(amount)} added to your wallet.` })
      const txRes = await getWalletTransactions()
      setTransactions(txRes.data?.items || [])
    } catch (err) {
      setDepositMsg({ type: 'error', text: err instanceof Error ? err.message : 'Deposit failed.' })
    } finally {
      setDepositing(false)
    }
  }

  async function handleDeleteMethod(id: string) {
    try {
      await deletePaymentMethod(id)
      setPaymentMethods(m => m.filter(p => p.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to remove.')
    }
  }

  async function handleSetDefault(id: string) {
    try {
      const res = await setDefaultPaymentMethod(id)
      setPaymentMethods(m => m.map(p => ({ ...p, is_default: p.id === res.data.id })))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed.')
    }
  }

  async function handlePayout(e: React.FormEvent) {
    e.preventDefault()
    const amount = Number(payoutAmount)
    if (!amount || amount < 10) { setPayoutMsg({ type: 'error', text: 'Minimum payout is $10.' }); return }
    setPayingOut(true)
    setPayoutMsg(null)
    try {
      await requestPayout(amount, payoutProvider)
      setPayoutAmount('')
      setPayoutMsg({ type: 'success', text: `Payout of ${formatCurrency(amount)} requested. Processing within 1–3 business days.` })
      await load(user?.role)
    } catch (err) {
      setPayoutMsg({ type: 'error', text: err instanceof Error ? err.message : 'Payout request failed.' })
    } finally {
      setPayingOut(false)
    }
  }

  const isResearcher = user?.role === 'researcher'

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[900px] mx-auto px-6 py-10">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-3xl font-semibold text-charcoal mb-1">
            {isResearcher ? 'Earnings & Wallet' : 'My Wallet'}
          </h1>
          <p className="text-medGrey text-sm mb-8">Manage your funds, payment methods, and transactions.</p>

          {loading ? (
            <div className="flex items-center justify-center py-24"><Loader2 className="w-8 h-8 animate-spin text-ctaBlue" /></div>
          ) : (
            <div className="space-y-5">

              {/* Balance card */}
              <div className="bg-gradient-to-br from-steelBlue to-ctaBlue rounded-2xl p-8 text-white shadow-lg">
                <p className="text-sm text-white/70 mb-2">Available Balance</p>
                <p className="font-display text-5xl font-semibold tracking-tight">
                  {formatCurrency(Number(wallet?.balance || 0))}
                </p>
                <p className="text-xs text-white/50 mt-3">
                  {isResearcher ? 'Earnings from completed contracts' : 'Funds in escrow are held separately until released'}
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Left: Add Funds */}
                {!isResearcher && (
                  <div className="bg-white rounded-2xl border border-divider p-6">
                    <h2 className="font-semibold text-charcoal mb-1">Add Funds</h2>
                    <p className="text-xs text-medGrey mb-4">Funds are added instantly to your wallet balance.</p>

                    <AnimatePresence>
                      {depositMsg && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                          className={`flex items-center gap-2 text-sm px-3 py-2.5 rounded-lg mb-3 ${depositMsg.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'}`}
                        >
                          {depositMsg.type === 'success' ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                          {depositMsg.text}
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <form onSubmit={handleDeposit} className="space-y-3">
                      <div className="relative">
                        <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-medGrey" />
                        <input
                          type="number" value={depositAmount} onChange={e => setDepositAmount(e.target.value)}
                          placeholder="Amount (USD)" min="1" step="0.01"
                          className="w-full border border-divider rounded-xl pl-9 pr-4 py-3 text-sm outline-none focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20"
                        />
                      </div>
                      <div className="flex gap-2">
                        {[50, 100, 250, 500].map(amt => (
                          <button key={amt} type="button" onClick={() => setDepositAmount(String(amt))}
                            className="text-xs bg-lightGrey text-charcoal font-medium px-3 py-1.5 rounded-lg hover:bg-divider transition-colors">
                            ${amt}
                          </button>
                        ))}
                      </div>
                      <button type="submit" disabled={depositing}
                        className="w-full bg-ctaBlue text-white font-semibold py-3 rounded-xl hover:bg-blue-600 disabled:opacity-60 flex items-center justify-center gap-2 text-sm transition-all">
                        {depositing ? <Loader2 className="w-4 h-4 animate-spin" /> : <DollarSign className="w-4 h-4" />}
                        Add Funds
                      </button>
                    </form>

                    {/* Stripe / PayPal info banners */}
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center gap-2 bg-[#635BFF]/10 border border-[#635BFF]/20 rounded-lg px-3 py-2.5">
                        <CreditCard className="w-4 h-4 text-[#635BFF] flex-shrink-0" />
                        <div>
                          <p className="text-xs font-semibold text-charcoal">Stripe</p>
                          <p className="text-[10px] text-medGrey">All major cards accepted. Instant confirmation.</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 bg-[#003087]/10 border border-[#003087]/20 rounded-lg px-3 py-2.5">
                        <span className="text-[#003087] font-bold text-sm flex-shrink-0">P</span>
                        <div>
                          <p className="text-xs font-semibold text-charcoal">PayPal</p>
                          <p className="text-[10px] text-medGrey">Pay with your PayPal balance or linked card.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Researcher: Request Payout */}
                {isResearcher && (
                  <div className="bg-white rounded-2xl border border-divider p-6">
                    <h2 className="font-semibold text-charcoal mb-1">Request Payout</h2>
                    <p className="text-xs text-medGrey mb-4">Minimum $10 · Processed within 1–3 business days.</p>

                    <AnimatePresence>
                      {payoutMsg && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                          className={`flex items-start gap-2 text-sm px-3 py-2.5 rounded-lg mb-3 ${payoutMsg.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'}`}
                        >
                          {payoutMsg.type === 'success' ? <CheckCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />}
                          {payoutMsg.text}
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <form onSubmit={handlePayout} className="space-y-3">
                      <div className="relative">
                        <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-medGrey" />
                        <input
                          type="number" value={payoutAmount} onChange={e => setPayoutAmount(e.target.value)}
                          placeholder="Amount (USD, min $10)" min="10" step="0.01"
                          className="w-full border border-divider rounded-xl pl-9 pr-4 py-3 text-sm outline-none focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-medGrey mb-1.5">Payout via</label>
                        <div className="flex gap-2">
                          {(['stripe', 'paypal'] as const).map(p => (
                            <button key={p} type="button" onClick={() => setPayoutProvider(p)}
                              className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-all ${payoutProvider === p ? 'bg-ctaBlue text-white border-ctaBlue' : 'bg-white text-charcoal border-divider hover:bg-lightGrey'}`}>
                              {p === 'stripe' ? 'Stripe' : 'PayPal'}
                            </button>
                          ))}
                        </div>
                      </div>
                      <button type="submit" disabled={payingOut}
                        className="w-full bg-green-600 text-white font-semibold py-3 rounded-xl hover:bg-green-700 disabled:opacity-60 flex items-center justify-center gap-2 text-sm transition-all">
                        {payingOut ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizonal className="w-4 h-4" />}
                        Request Payout
                      </button>
                    </form>
                  </div>
                )}

                {/* Saved Payment Methods */}
                <div className="bg-white rounded-2xl border border-divider p-6">
                  <h2 className="font-semibold text-charcoal mb-4">Saved Payment Methods</h2>
                  {paymentMethods.length === 0 ? (
                    <div className="text-center py-6">
                      <CreditCard className="w-8 h-8 text-medGrey mx-auto mb-2" />
                      <p className="text-sm text-medGrey">No saved methods yet.</p>
                      <p className="text-xs text-medGrey mt-1">Methods are saved when you pay via Stripe.</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {paymentMethods.map(pm => (
                        <div key={pm.id} className="flex items-center gap-3 border border-divider rounded-xl px-4 py-3">
                          <CreditCard className="w-4 h-4 text-medGrey flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-charcoal capitalize">
                              {pm.brand || pm.provider} {pm.last4 ? `•••• ${pm.last4}` : ''}
                            </p>
                            {pm.expiry_month && (
                              <p className="text-xs text-medGrey">Expires {pm.expiry_month}/{pm.expiry_year}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-1.5">
                            {pm.is_default ? (
                              <span className="text-xs bg-green-100 text-green-700 font-medium px-2 py-0.5 rounded-full">Default</span>
                            ) : (
                              <button onClick={() => handleSetDefault(pm.id)} title="Set as default"
                                className="p-1.5 text-medGrey hover:text-ctaBlue transition-colors rounded">
                                <Star className="w-3.5 h-3.5" />
                              </button>
                            )}
                            <button onClick={() => handleDeleteMethod(pm.id)} title="Remove"
                              className="p-1.5 text-medGrey hover:text-red-500 transition-colors rounded">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Payout history (researcher only) */}
              {isResearcher && payouts.length > 0 && (
                <div className="bg-white rounded-2xl border border-divider p-6">
                  <h2 className="font-semibold text-charcoal mb-4">Payout History</h2>
                  <div className="space-y-3">
                    {payouts.map(p => (
                      <div key={p.id} className="flex items-center gap-3 py-2 border-b border-divider last:border-0">
                        <div className="w-8 h-8 bg-lightGrey rounded-full flex items-center justify-center flex-shrink-0">
                          <ArrowUpRight className="w-4 h-4 text-rose-500" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-charcoal capitalize">Payout via {p.provider}</p>
                          <p className="text-xs text-medGrey">{new Date(p.created_at).toLocaleString()}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-rose-500">-{formatCurrency(Number(p.amount))}</p>
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${payoutStatusColors[p.status] || 'bg-gray-100 text-gray-600'}`}>
                            {p.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Transaction history */}
              <div className="bg-white rounded-2xl border border-divider p-6">
                <h2 className="font-semibold text-charcoal mb-4">Transaction History</h2>
                {transactions.length === 0 ? (
                  <p className="text-sm text-medGrey text-center py-6">No transactions yet.</p>
                ) : (
                  <div className="space-y-0">
                    {transactions.map(tx => (
                      <div key={tx.id} className="flex items-center gap-3 py-3 border-b border-divider last:border-0">
                        <div className="w-8 h-8 bg-lightGrey rounded-full flex items-center justify-center flex-shrink-0">
                          {txIcons[tx.transaction_type] || <DollarSign className="w-4 h-4 text-medGrey" />}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-charcoal">{txLabels[tx.transaction_type] || tx.transaction_type}</p>
                          <p className="text-xs text-medGrey">{new Date(tx.created_at).toLocaleString()}</p>
                        </div>
                        <span className={`text-sm font-semibold ${txColor(tx.transaction_type)}`}>
                          {txSign(tx.transaction_type)}{formatCurrency(Math.abs(Number(tx.amount)))}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
