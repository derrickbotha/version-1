'use client'

import { motion } from 'framer-motion'
import { ClipboardList, Users, PenLine, Download, ChevronRight } from 'lucide-react'

const steps = [
  {
    number: 1,
    icon: ClipboardList,
    title: 'Submit Instructions',
    description:
      'Fill out our simple order form with your requirements, deadline, and academic level. Takes under 3 minutes.',
  },
  {
    number: 2,
    icon: Users,
    title: 'Match with Expert',
    description:
      'We match you with the most qualified PhD researcher for your specific subject and requirements.',
  },
  {
    number: 3,
    icon: PenLine,
    title: 'Writing & Review',
    description:
      'Your researcher writes, edits, and proofreads — with unlimited revisions until you are completely satisfied.',
  },
  {
    number: 4,
    icon: Download,
    title: 'Receive Paper',
    description:
      'Download your completed, plagiarism-free paper before your deadline. Guaranteed on-time delivery.',
  },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-white py-24">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-14"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            Simple Process
          </p>
          <h2 className="font-display text-4xl font-semibold text-charcoal">How It Works</h2>
          <p className="mt-4 text-lg text-medGrey max-w-xl mx-auto">
            Get your research paper in four simple steps — from submission to delivery.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative">
          {steps.map((step, i) => {
            const Icon = step.icon
            return (
              <div key={step.number} className="relative flex flex-col items-start">
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: i * 0.15 }}
                  className="bg-lightGrey rounded-2xl p-7 w-full h-full border border-divider hover:border-steelBlue/40 hover:shadow-lg transition-all duration-300"
                >
                  {/* Step number + icon */}
                  <div className="flex items-center justify-between mb-5">
                    <div className="w-12 h-12 rounded-xl bg-steelBlue flex items-center justify-center shadow-sm">
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <span className="text-4xl font-bold text-divider font-display">
                      {String(step.number).padStart(2, '0')}
                    </span>
                  </div>
                  <h3 className="font-display text-xl font-semibold text-charcoal mb-3">
                    {step.title}
                  </h3>
                  <p className="text-sm text-medGrey leading-relaxed">{step.description}</p>
                </motion.div>

                {/* Arrow connector — shown between cards on desktop */}
                {i < steps.length - 1 && (
                  <div className="hidden lg:flex absolute -right-4 top-1/2 -translate-y-1/2 z-10 items-center justify-center w-8 h-8 bg-white border border-divider rounded-full shadow-sm">
                    <ChevronRight className="w-4 h-4 text-steelBlue" />
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* CTA row */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="text-center mt-12"
        >
          <a
            href="#pricing"
            className="inline-flex items-center gap-2 bg-ctaBlue text-white text-base font-medium px-8 py-4 rounded-lg hover:bg-steelBlue transition-all duration-200 shadow-md hover:shadow-lg"
          >
            Start Your Order
            <ChevronRight className="w-4 h-4" />
          </a>
        </motion.div>
      </div>
    </section>
  )
}
