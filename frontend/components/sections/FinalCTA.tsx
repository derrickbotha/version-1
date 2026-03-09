'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'

export default function FinalCTA() {
  return (
    <section className="bg-charcoal py-24">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="text-center max-w-3xl mx-auto"
        >
          {/* Decorative element */}
          <div className="flex justify-center mb-8">
            <div className="w-16 h-1 bg-ctaBlue rounded-full" />
          </div>

          <h2 className="font-display text-5xl font-semibold text-white leading-tight mb-6">
            Ready to Start Your Research Project?
          </h2>
          <p className="text-xl text-gray-300 mb-10">
            Join 52,000+ students who trust ResearchPro for premium academic work.
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="#pricing"
              className="bg-ctaBlue text-white text-lg font-semibold py-4 px-10 rounded-xl hover:bg-blue-600 transition-all duration-200 shadow-xl hover:shadow-blue-500/30"
            >
              Get Your Price Instantly
            </Link>
            <Link
              href="#how-it-works"
              className="border-2 border-white/30 text-white text-lg font-medium py-4 px-8 rounded-xl hover:bg-white/10 transition-all duration-200"
            >
              Learn How It Works
            </Link>
          </div>

          {/* Trust indicators */}
          <div className="flex flex-wrap justify-center gap-8 mt-12 text-sm text-gray-400">
            <span className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              No payment required upfront
            </span>
            <span className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              Money-back guarantee
            </span>
            <span className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              Strict confidentiality
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
