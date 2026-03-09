'use client'

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, Loader2, Minus, Plus } from 'lucide-react'
import { createJob } from '@/lib/api'
import {
  PRICING_TABLE,
  DEADLINE_LABELS,
  DEADLINE_KEYS,
  ACADEMIC_LEVEL_PRICING_KEY,
  deadlineKeyToIso,
  type AcademicLevelKey,
  type DeadlineKey,
} from '@/lib/pricing'
import { formatCurrency } from '@/lib/utils'

const SUBJECTS = [
  'Computer Science', 'Economics', 'Medicine', 'Law', 'Engineering',
  'Physics', 'Literature', 'Psychology', 'History', 'Business',
  'Mathematics', 'Biology', 'Chemistry', 'Sociology', 'Political Science',
]

const ACADEMIC_LEVELS = [
  'High School', 'Undergraduate 1-2', 'Undergraduate 3-4',
  'Graduate', 'PhD', 'Professional',
]

const PAPER_TYPES = [
  'Essay', 'Research Paper', 'Thesis', 'Dissertation',
  'Coursework', 'Assignment', 'Case Study', 'Literature Review', 'Lab Report',
]

export default function NewJobPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Pricing inputs — mirroring the homepage calculator exactly
  const [academicLevel, setAcademicLevel] = useState<string>('Undergraduate 1-2')
  const [deadlineKey, setDeadlineKey] = useState<DeadlineKey>('7d')
  const [pages, setPages] = useState(1)
  const [paperType, setPaperType] = useState('Essay')

  // Job details
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [subject, setSubject] = useState('')

  // Editable price (student can override)
  const levelKey: AcademicLevelKey = ACADEMIC_LEVEL_PRICING_KEY[academicLevel] ?? 'ug12'
  const perPage = PRICING_TABLE[deadlineKey][levelKey]
  const suggestedTotal = perPage * pages
  const [customPrice, setCustomPrice] = useState<string>('')

  // Floor: 9.9% below for totals < $50, 6.5% below for $51+
  const discountRate = suggestedTotal < 50 ? 0.099 : 0.065
  const minPrice = Math.max(1, suggestedTotal * (1 - discountRate))

  // When calculator changes, reset any custom override
  const displayPrice = customPrice !== '' ? Number(customPrice) : suggestedTotal
  const customNum = customPrice !== '' ? Number(customPrice) : null
  const isBelowFloor = customNum !== null && customNum < minPrice

  const inputClass = 'w-full border border-divider rounded-lg px-4 py-3 text-sm text-charcoal placeholder:text-medGrey/60 outline-none focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20 transition-all bg-white'

  function handlePages(delta: number) {
    setPages(p => Math.max(1, Math.min(50, p + delta)))
    setCustomPrice('')
  }

  function handleLevelChange(val: string) {
    setAcademicLevel(val)
    setCustomPrice('')
  }

  function handleDeadlineChange(val: DeadlineKey) {
    setDeadlineKey(val)
    setCustomPrice('')
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')

    if (!title || !description || !subject) {
      setError('Please fill in all required fields.')
      return
    }
    if (displayPrice <= 0) {
      setError('Price must be greater than 0.')
      return
    }
    if (isBelowFloor) {
      setError(`Budget cannot be more than ${(discountRate * 100).toFixed(1)}% below the suggested price. Minimum allowed: ${formatCurrency(minPrice)}.`)
      return
    }

    setLoading(true)
    try {
      await createJob({
        title: title.trim(),
        description: description.trim(),
        subject,
        academic_level: academicLevel,
        proposed_price: displayPrice.toFixed(2),
        deadline: deadlineKeyToIso(deadlineKey),
      })
      router.push('/jobs/mine')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create job.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[1100px] mx-auto px-6 py-10">
        <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-medGrey hover:text-charcoal mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="font-display text-3xl font-semibold text-charcoal mb-1">Post a Research Job</h1>
          <p className="text-medGrey text-sm mb-8">Configure your order and describe your assignment — researchers will bid on it.</p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {/* Left column — job details + pricing inputs */}
              <div className="space-y-5">
                <div className="bg-white rounded-2xl border border-divider p-6">
                  <h2 className="font-semibold text-charcoal mb-5">Job Details</h2>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-charcoal mb-1.5">Job Title *</label>
                      <input
                        type="text"
                        value={title}
                        onChange={e => setTitle(e.target.value)}
                        placeholder="e.g. Literature review on machine learning in healthcare"
                        className={inputClass}
                        minLength={5}
                        maxLength={255}
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-charcoal mb-1.5">Description *</label>
                      <textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Describe requirements: topic, length, format, sources, citation style, etc."
                        className={inputClass + ' h-32 resize-none'}
                        minLength={20}
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-charcoal mb-1.5">Subject *</label>
                      <select
                        value={subject}
                        onChange={e => setSubject(e.target.value)}
                        className={inputClass}
                        required
                      >
                        <option value="">Select subject...</option>
                        {SUBJECTS.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Pricing configuration — exact same controls as homepage */}
                <div className="bg-white rounded-2xl border border-divider p-6">
                  <h2 className="font-semibold text-charcoal mb-5">Configure Your Order</h2>

                  <div className="space-y-5">
                    {/* Academic Level */}
                    <div>
                      <label className="block text-sm font-medium text-charcoal mb-2">Academic Level</label>
                      <select
                        value={academicLevel}
                        onChange={e => handleLevelChange(e.target.value)}
                        className={inputClass}
                      >
                        {ACADEMIC_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                      </select>
                    </div>

                    {/* Number of Pages */}
                    <div>
                      <label className="block text-sm font-medium text-charcoal mb-2">
                        Number of Pages
                      </label>
                      <div className="flex items-center gap-0 border border-divider rounded-lg overflow-hidden">
                        <button
                          type="button"
                          onClick={() => handlePages(-1)}
                          disabled={pages <= 1}
                          className="px-4 py-3 bg-lightGrey hover:bg-divider transition-colors text-charcoal disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <div className="flex-1 text-center py-3 text-sm font-semibold text-charcoal border-x border-divider">
                          {pages} {pages === 1 ? 'page' : 'pages'}
                          <span className="text-xs text-medGrey ml-1">(~{pages * 275} words)</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handlePages(1)}
                          disabled={pages >= 50}
                          className="px-4 py-3 bg-lightGrey hover:bg-divider transition-colors text-charcoal disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Deadline */}
                    <div>
                      <label className="block text-sm font-medium text-charcoal mb-2">Deadline</label>
                      <select
                        value={deadlineKey}
                        onChange={e => handleDeadlineChange(e.target.value as DeadlineKey)}
                        className={inputClass}
                      >
                        {DEADLINE_KEYS.map(k => (
                          <option key={k} value={k}>{DEADLINE_LABELS[k]}</option>
                        ))}
                      </select>
                    </div>

                    {/* Paper Type */}
                    <div>
                      <label className="block text-sm font-medium text-charcoal mb-2">Paper Type</label>
                      <select
                        value={paperType}
                        onChange={e => setPaperType(e.target.value)}
                        className={inputClass}
                      >
                        {PAPER_TYPES.map(p => <option key={p} value={p}>{p}</option>)}
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right column — price display (dark, like homepage) + submit */}
              <div className="space-y-5">
                <div className="bg-charcoal rounded-2xl p-8 shadow-sm flex flex-col justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-400 uppercase tracking-widest mb-6">Your Price</p>

                    <AnimatePresence mode="wait">
                      <motion.div
                        key={suggestedTotal}
                        initial={{ opacity: 0, scale: 0.88 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.08 }}
                        transition={{ duration: 0.25, ease: 'easeOut' }}
                      >
                        <span className="font-display text-[64px] font-semibold text-ctaBlue leading-none tracking-tight">
                          {formatCurrency(suggestedTotal)}
                        </span>
                      </motion.div>
                    </AnimatePresence>

                    <p className="text-sm text-gray-400 mt-3">
                      Per page: <span className="text-white font-medium">{formatCurrency(perPage)}</span>
                    </p>

                    {/* Breakdown */}
                    <div className="mt-8 space-y-3">
                      {[
                        { label: 'Academic Level', value: academicLevel },
                        { label: 'Pages', value: `${pages} page${pages > 1 ? 's' : ''}` },
                        { label: 'Deadline', value: DEADLINE_LABELS[deadlineKey] },
                        { label: 'Paper Type', value: paperType },
                      ].map(item => (
                        <div key={item.label} className="flex justify-between items-center text-sm">
                          <span className="text-gray-400">{item.label}</span>
                          <span className="text-white font-medium">{item.value}</span>
                        </div>
                      ))}
                    </div>

                    <div className="border-t border-white/10 my-5" />

                    <div className="flex justify-between items-center text-sm font-semibold">
                      <span className="text-gray-300">Total</span>
                      <span className="text-ctaBlue text-lg">{formatCurrency(suggestedTotal)}</span>
                    </div>
                  </div>

                  {/* Custom price override */}
                  <div className="mt-8">
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      Adjust Budget (USD)
                      <span className="ml-1 text-gray-500 font-normal">— optional override</span>
                    </label>
                    <input
                      type="number"
                      value={customPrice}
                      onChange={e => setCustomPrice(e.target.value)}
                      onBlur={() => {
                        if (customPrice === '') return
                        const val = Number(customPrice)
                        if (val < minPrice) setCustomPrice(minPrice.toFixed(2))
                      }}
                      placeholder={suggestedTotal.toFixed(2)}
                      min={minPrice.toFixed(2)}
                      step="0.01"
                      className={`w-full bg-white/10 border text-white rounded-lg px-4 py-3 text-sm placeholder:text-gray-500 outline-none transition-all ${
                        isBelowFloor
                          ? 'border-red-400 focus:border-red-400'
                          : 'border-white/20 focus:border-ctaBlue'
                      }`}
                    />
                    {isBelowFloor ? (
                      <p className="text-xs text-red-400 mt-1.5">
                        Min allowed: {formatCurrency(minPrice)} ({(discountRate * 100).toFixed(1)}% below suggested)
                      </p>
                    ) : customPrice !== '' && Number(customPrice) !== suggestedTotal ? (
                      <p className="text-xs text-gray-400 mt-1.5">
                        Suggested: {formatCurrency(suggestedTotal)} · Floor: {formatCurrency(minPrice)}
                      </p>
                    ) : (
                      <p className="text-xs text-gray-500 mt-1.5">
                        Max {(discountRate * 100).toFixed(1)}% below suggested · Floor: {formatCurrency(minPrice)}
                      </p>
                    )}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading || isBelowFloor}
                  className="w-full bg-ctaBlue text-white font-semibold py-4 rounded-xl hover:bg-blue-600 disabled:opacity-60 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 text-base shadow-lg hover:shadow-blue-500/30"
                >
                  {loading ? <><Loader2 className="w-4 h-4 animate-spin" />Posting...</> : 'Post Job'}
                </button>
                <p className="text-xs text-medGrey text-center -mt-2">
                  No payment until you approve the work
                </p>
              </div>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  )
}
