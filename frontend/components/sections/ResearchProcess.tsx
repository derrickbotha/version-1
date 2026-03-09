'use client'

import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'

const steps = [
  {
    number: '01',
    title: 'Research Brief Submitted',
    description:
      'You submit your assignment details, requirements, academic level, and deadline through our secure order form.',
  },
  {
    number: '02',
    title: 'Academic Database Research',
    description:
      'Our researchers access Elsevier, Springer, IEEE, JSTOR, and 50+ databases to gather authoritative sources.',
  },
  {
    number: '03',
    title: 'AI-Assisted Literature Review',
    description:
      'Advanced AI tools help synthesize hundreds of sources, identify gaps, and structure the theoretical framework.',
  },
  {
    number: '04',
    title: 'PhD-Level Writer Drafting',
    description:
      'A vetted PhD researcher in your subject area drafts the paper with original analysis and argumentation.',
  },
  {
    number: '05',
    title: 'Human Editing & Proofreading',
    description:
      'A dedicated editor reviews for clarity, coherence, argument strength, and adherence to academic style guidelines.',
  },
  {
    number: '06',
    title: 'Plagiarism & AI Detection Checks',
    description:
      'Final checks via Turnitin ensure 0% plagiarism and full compliance with AI content policies before delivery.',
  },
]

export default function ResearchProcess() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section id="process" className="bg-lightGrey py-24">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-16"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            Methodology
          </p>
          <h2 className="font-display text-4xl font-semibold text-charcoal">
            Our Research Methodology
          </h2>
          <p className="mt-4 text-lg text-medGrey max-w-xl mx-auto">
            A rigorous, multi-stage process ensures every paper meets the highest academic
            standards.
          </p>
        </motion.div>

        {/* Desktop: Horizontal timeline */}
        <div ref={ref} className="hidden lg:block relative">
          {/* Connecting line */}
          <div className="absolute top-12 left-[calc(8.33%+16px)] right-[calc(8.33%+16px)] h-0.5 bg-divider z-0" />
          <motion.div
            initial={{ scaleX: 0 }}
            animate={isInView ? { scaleX: 1 } : { scaleX: 0 }}
            transition={{ duration: 1.2, ease: 'easeInOut', delay: 0.3 }}
            style={{ transformOrigin: 'left' }}
            className="absolute top-12 left-[calc(8.33%+16px)] right-[calc(8.33%+16px)] h-0.5 bg-steelBlue z-0"
          />

          <div className="grid grid-cols-6 gap-4 relative z-10">
            {steps.map((step, i) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 30 }}
                animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
                transition={{ duration: 0.6, delay: i * 0.15 + 0.2 }}
                className="flex flex-col items-center text-center"
              >
                {/* Number badge */}
                <div className="w-[52px] h-[52px] rounded-full bg-steelBlue text-white flex items-center justify-center text-sm font-bold mb-6 shadow-lg flex-shrink-0">
                  {step.number}
                </div>
                <h3 className="font-display text-sm font-semibold text-charcoal mb-2 leading-snug">
                  {step.title}
                </h3>
                <p className="text-xs text-medGrey leading-relaxed">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Mobile: Vertical timeline */}
        <div className="lg:hidden relative pl-8">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-divider" />

          <div className="space-y-10">
            {steps.map((step, i) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="relative"
              >
                {/* Circle on line */}
                <div className="absolute -left-8 w-[32px] h-[32px] rounded-full bg-steelBlue text-white flex items-center justify-center text-xs font-bold -translate-x-[16px] shadow">
                  {step.number}
                </div>
                <div className="bg-white rounded-xl border border-divider p-6">
                  <h3 className="font-display text-base font-semibold text-charcoal mb-2">
                    {step.title}
                  </h3>
                  <p className="text-sm text-medGrey leading-relaxed">{step.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
