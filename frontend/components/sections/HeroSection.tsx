'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
}

const stagger = {
  animate: {
    transition: {
      staggerChildren: 0.12,
    },
  },
}

export default function HeroSection() {
  return (
    <section className="min-h-screen flex items-center bg-white pt-20">
      <div className="max-w-[1280px] mx-auto px-6 py-20 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left Column */}
          <motion.div
            variants={stagger}
            initial="initial"
            animate="animate"
            className="flex flex-col"
          >
            <motion.div variants={fadeUp} transition={{ duration: 0.8, ease: 'easeOut' }}>
              <span className="inline-flex items-center gap-2 bg-blue-50 text-ctaBlue text-sm font-medium px-4 py-1.5 rounded-full mb-6">
                <span className="w-2 h-2 rounded-full bg-ctaBlue animate-pulse" />
                480+ Expert Researchers Available Now
              </span>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="font-display text-5xl lg:text-[72px] font-semibold text-charcoal leading-[1.1] tracking-tight mb-6"
            >
              Premium Academic Research &{' '}
              <span className="text-steelBlue">Writing Services</span>
            </motion.h1>

            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="text-xl text-medGrey leading-relaxed mb-10 max-w-[520px]"
            >
              Work with PhD-level researchers and advanced AI-assisted research tools to produce
              high-quality academic work that meets the highest scholarly standards.
            </motion.p>

            <motion.div
              variants={fadeUp}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="flex flex-wrap gap-4 mb-12"
            >
              <Link
                href="#pricing"
                className="bg-ctaBlue text-white text-base font-medium px-8 py-4 rounded-lg hover:bg-steelBlue transition-all duration-200 shadow-md hover:shadow-lg"
              >
                Get Instant Price
              </Link>
              <Link
                href="#how-it-works"
                className="border-2 border-charcoal text-charcoal text-base font-medium px-8 py-4 rounded-lg hover:bg-charcoal hover:text-white transition-all duration-200"
              >
                How It Works
              </Link>
            </motion.div>

            {/* Social Proof */}
            <motion.div
              variants={fadeUp}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="flex flex-wrap items-center gap-8"
            >
              {[
                { value: '52,000+', label: 'Papers Completed' },
                { value: '480+', label: 'Expert Writers' },
                { value: '4.9★', label: 'Rating' },
              ].map((stat) => (
                <div key={stat.label} className="flex flex-col">
                  <span className="font-display text-2xl font-semibold text-charcoal">
                    {stat.value}
                  </span>
                  <span className="text-sm text-medGrey">{stat.label}</span>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Right Column — Abstract SVG Illustration */}
          <div className="relative hidden lg:flex items-center justify-center">
            {/* Main SVG illustration */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
              className="relative w-full max-w-[520px]"
            >
              <svg viewBox="0 0 520 480" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-auto">
                {/* Background circle */}
                <circle cx="260" cy="240" r="220" fill="#F5F7FA" />

                {/* Large decorative circle */}
                <circle cx="260" cy="240" r="160" stroke="#E6E9ED" strokeWidth="2" fill="none" />

                {/* Document shapes */}
                <rect x="120" y="100" width="140" height="180" rx="8" fill="white" stroke="#E6E9ED" strokeWidth="1.5" />
                <rect x="132" y="120" width="80" height="8" rx="4" fill="#457B9D" />
                <rect x="132" y="138" width="110" height="6" rx="3" fill="#E6E9ED" />
                <rect x="132" y="152" width="95" height="6" rx="3" fill="#E6E9ED" />
                <rect x="132" y="166" width="105" height="6" rx="3" fill="#E6E9ED" />
                <rect x="132" y="180" width="88" height="6" rx="3" fill="#E6E9ED" />
                <rect x="132" y="194" width="100" height="6" rx="3" fill="#E6E9ED" />
                <rect x="132" y="208" width="76" height="6" rx="3" fill="#E6E9ED" />
                <rect x="132" y="228" width="60" height="24" rx="6" fill="#007BFF" />
                <rect x="144" y="234" width="36" height="12" rx="3" fill="white" opacity="0.8" />

                {/* Second document (rotated slightly) */}
                <g transform="rotate(8 320 260)">
                  <rect x="260" y="120" width="140" height="180" rx="8" fill="white" stroke="#E6E9ED" strokeWidth="1.5" />
                  <rect x="272" y="140" width="90" height="8" rx="4" fill="#212529" />
                  <rect x="272" y="158" width="108" height="6" rx="3" fill="#E6E9ED" />
                  <rect x="272" y="172" width="95" height="6" rx="3" fill="#E6E9ED" />
                  <rect x="272" y="186" width="105" height="6" rx="3" fill="#E6E9ED" />
                  <rect x="272" y="200" width="80" height="6" rx="3" fill="#E6E9ED" />
                  <rect x="272" y="214" width="100" height="6" rx="3" fill="#E6E9ED" />
                  <rect x="272" y="228" width="76" height="6" rx="3" fill="#E6E9ED" />
                </g>

                {/* Connecting dots / network */}
                <circle cx="260" cy="240" r="6" fill="#457B9D" />
                <circle cx="160" cy="320" r="5" fill="#007BFF" />
                <circle cx="360" cy="330" r="5" fill="#007BFF" />
                <circle cx="200" cy="380" r="4" fill="#457B9D" opacity="0.6" />
                <circle cx="330" cy="390" r="4" fill="#457B9D" opacity="0.6" />
                <circle cx="420" cy="280" r="4" fill="#6C757D" opacity="0.5" />
                <circle cx="100" cy="280" r="4" fill="#6C757D" opacity="0.5" />

                {/* Connection lines */}
                <line x1="260" y1="240" x2="160" y2="320" stroke="#457B9D" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
                <line x1="260" y1="240" x2="360" y2="330" stroke="#457B9D" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
                <line x1="160" y1="320" x2="200" y2="380" stroke="#E6E9ED" strokeWidth="1" />
                <line x1="360" y1="330" x2="330" y2="390" stroke="#E6E9ED" strokeWidth="1" />
                <line x1="260" y1="240" x2="420" y2="280" stroke="#E6E9ED" strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />
                <line x1="260" y1="240" x2="100" y2="280" stroke="#E6E9ED" strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />

                {/* Chart bar (bottom) */}
                <rect x="130" y="360" width="20" height="60" rx="4" fill="#457B9D" opacity="0.3" />
                <rect x="158" y="340" width="20" height="80" rx="4" fill="#457B9D" opacity="0.5" />
                <rect x="186" y="350" width="20" height="70" rx="4" fill="#457B9D" opacity="0.4" />
                <rect x="214" y="330" width="20" height="90" rx="4" fill="#007BFF" opacity="0.7" />
                <rect x="242" y="320" width="20" height="100" rx="4" fill="#007BFF" />
                <rect x="270" y="335" width="20" height="85" rx="4" fill="#457B9D" opacity="0.6" />
                <rect x="298" y="355" width="20" height="65" rx="4" fill="#457B9D" opacity="0.4" />
              </svg>
            </motion.div>

            {/* Floating card 1 — PhD Writers */}
            <motion.div
              initial={{ opacity: 0, y: 20, x: -20 }}
              animate={{ opacity: 1, y: 0, x: 0 }}
              transition={{ duration: 0.8, ease: 'easeOut', delay: 0.8 }}
              className="absolute top-12 -left-4 bg-white rounded-xl shadow-xl border border-divider px-5 py-4 flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-steelBlue/10 flex items-center justify-center">
                <svg className="w-5 h-5 text-steelBlue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                  <path d="M6 12v5c3 3 9 3 12 0v-5" />
                </svg>
              </div>
              <div>
                <p className="text-xs text-medGrey">Verified</p>
                <p className="text-sm font-semibold text-charcoal">PhD Writers</p>
              </div>
            </motion.div>

            {/* Floating card 2 — 24/7 Support */}
            <motion.div
              initial={{ opacity: 0, y: 20, x: 20 }}
              animate={{ opacity: 1, y: 0, x: 0 }}
              transition={{ duration: 0.8, ease: 'easeOut', delay: 1.0 }}
              className="absolute bottom-16 -right-4 bg-white rounded-xl shadow-xl border border-divider px-5 py-4 flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-ctaBlue/10 flex items-center justify-center">
                <svg className="w-5 h-5 text-ctaBlue" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
              <div>
                <p className="text-xs text-medGrey">Always Available</p>
                <p className="text-sm font-semibold text-charcoal">24/7 Support</p>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
