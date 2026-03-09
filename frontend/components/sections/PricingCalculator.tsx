'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { Minus, Plus } from 'lucide-react'
import { formatCurrency } from '@/lib/utils'
import { PRICING_TABLE, type AcademicLevelKey as AcademicLevel, type DeadlineKey as Deadline } from '@/lib/pricing'

const academicLevels: { value: AcademicLevel; label: string }[] = [
  { value: 'hs', label: 'High School' },
  { value: 'ug12', label: 'Undergraduate 1-2' },
  { value: 'ug34', label: 'Undergraduate 3-4' },
  { value: 'grad', label: 'Graduate' },
  { value: 'phd', label: 'PhD' },
]

const deadlines: { value: Deadline; label: string }[] = [
  { value: '4h', label: '4 Hours' },
  { value: '8h', label: '8 Hours' },
  { value: '24h', label: '24 Hours' },
  { value: '48h', label: '48 Hours' },
  { value: '3d', label: '3 Days' },
  { value: '5d', label: '5 Days' },
  { value: '7d', label: '7 Days' },
  { value: '14d', label: '14 Days' },
]

const paperTypes = [
  'Essay',
  'Research Paper',
  'Thesis',
  'Dissertation',
  'Coursework',
  'Assignment',
  'Case Study',
  'Literature Review',
  'Lab Report',
]

export default function PricingCalculator() {
  const [level, setLevel] = useState<AcademicLevel>('ug12')
  const [pages, setPages] = useState(1)
  const [deadline, setDeadline] = useState<Deadline>('7d')
  const [paperType, setPaperType] = useState('Essay')
  const [prevPrice, setPrevPrice] = useState<number | null>(null)

  const perPage = PRICING_TABLE[deadline][level]
  const total = perPage * pages

  const handleLevelChange = (v: AcademicLevel) => {
    setPrevPrice(total)
    setLevel(v)
  }

  const handleDeadlineChange = (v: Deadline) => {
    setPrevPrice(total)
    setDeadline(v)
  }

  const handlePagesChange = (newPages: number) => {
    if (newPages < 1 || newPages > 50) return
    setPrevPrice(total)
    setPages(newPages)
  }

  return (
    <section id="pricing" className="bg-lightGrey py-24">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-14"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            Transparent Pricing
          </p>
          <h2 className="font-display text-4xl font-semibold text-charcoal">
            Get Your Instant Price
          </h2>
          <p className="mt-4 text-lg text-medGrey max-w-xl mx-auto">
            No hidden fees. Configure your order below to see the exact price.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {/* Left: Form */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
            className="bg-white rounded-2xl border border-divider p-8 shadow-sm"
          >
            <h3 className="font-display text-xl font-semibold text-charcoal mb-7">
              Configure Your Order
            </h3>

            {/* Academic Level */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-charcoal mb-2">
                Academic Level
              </label>
              <select
                value={level}
                onChange={(e) => handleLevelChange(e.target.value as AcademicLevel)}
                className="w-full border border-divider rounded-lg px-4 py-3 text-sm text-charcoal bg-white transition-colors focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20 outline-none"
              >
                {academicLevels.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Number of Pages */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-charcoal mb-2">
                Number of Pages
              </label>
              <div className="flex items-center gap-0 border border-divider rounded-lg overflow-hidden">
                <button
                  onClick={() => handlePagesChange(pages - 1)}
                  disabled={pages <= 1}
                  className="px-4 py-3 bg-lightGrey hover:bg-divider transition-colors text-charcoal disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Decrease pages"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <div className="flex-1 text-center py-3 text-sm font-semibold text-charcoal border-x border-divider">
                  {pages} {pages === 1 ? 'page' : 'pages'}
                  <span className="text-xs text-medGrey ml-1">
                    (~{pages * 275} words)
                  </span>
                </div>
                <button
                  onClick={() => handlePagesChange(pages + 1)}
                  disabled={pages >= 50}
                  className="px-4 py-3 bg-lightGrey hover:bg-divider transition-colors text-charcoal disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Increase pages"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Deadline */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-charcoal mb-2">
                Deadline
              </label>
              <select
                value={deadline}
                onChange={(e) => handleDeadlineChange(e.target.value as Deadline)}
                className="w-full border border-divider rounded-lg px-4 py-3 text-sm text-charcoal bg-white transition-colors focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20 outline-none"
              >
                {deadlines.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Paper Type */}
            <div className="mb-2">
              <label className="block text-sm font-medium text-charcoal mb-2">
                Paper Type
              </label>
              <select
                value={paperType}
                onChange={(e) => setPaperType(e.target.value)}
                className="w-full border border-divider rounded-lg px-4 py-3 text-sm text-charcoal bg-white transition-colors focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20 outline-none"
              >
                {paperTypes.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          </motion.div>

          {/* Right: Price Display */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
            className="bg-charcoal rounded-2xl p-8 shadow-sm flex flex-col justify-between"
          >
            <div>
              <p className="text-sm font-medium text-gray-400 uppercase tracking-widest mb-6">
                Your Price
              </p>

              {/* Animated price */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={total}
                  initial={{ opacity: 0, scale: 0.88 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.08 }}
                  transition={{ duration: 0.25, ease: 'easeOut' }}
                >
                  <span className="font-display text-[64px] font-semibold text-ctaBlue leading-none tracking-tight">
                    {formatCurrency(total)}
                  </span>
                </motion.div>
              </AnimatePresence>

              <p className="text-sm text-gray-400 mt-3">
                Per page:{' '}
                <span className="text-white font-medium">{formatCurrency(perPage)}</span>
              </p>

              {/* Breakdown */}
              <div className="mt-8 space-y-3">
                {[
                  { label: 'Academic Level', value: academicLevels.find((l) => l.value === level)?.label },
                  { label: 'Pages', value: `${pages} page${pages > 1 ? 's' : ''}` },
                  { label: 'Deadline', value: deadlines.find((d) => d.value === deadline)?.label },
                  { label: 'Paper Type', value: paperType },
                ].map((item) => (
                  <div key={item.label} className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">{item.label}</span>
                    <span className="text-white font-medium">{item.value}</span>
                  </div>
                ))}
              </div>

              <div className="border-t border-white/10 my-5" />

              <div className="flex justify-between items-center text-sm font-semibold">
                <span className="text-gray-300">Total</span>
                <span className="text-ctaBlue text-lg">{formatCurrency(total)}</span>
              </div>
            </div>

            <div className="mt-8">
              <Link
                href={`/auth/register?plan=custom&level=${level}&pages=${pages}&deadline=${deadline}&type=${encodeURIComponent(paperType)}`}
                className="block w-full bg-ctaBlue text-white text-center font-semibold py-4 rounded-xl hover:bg-blue-600 transition-all duration-200 shadow-lg hover:shadow-blue-500/30 text-base"
              >
                Order at this price
              </Link>
              <p className="text-xs text-gray-500 text-center mt-3">
                No payment until you approve the work
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
