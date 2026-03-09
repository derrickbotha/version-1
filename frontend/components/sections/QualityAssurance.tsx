'use client'

import { motion } from 'framer-motion'
import { CheckCircle2 } from 'lucide-react'

const guarantees = [
  '100% Human Written',
  'AI-Assisted Research',
  'Zero Plagiarism Guarantee',
  'Accurate Citations (APA, MLA, Chicago)',
  'Strict Confidentiality',
  'On-Time Delivery',
  'Unlimited Free Revisions',
  'Money-Back Guarantee',
]

const tools = [
  { name: 'Turnitin', desc: 'Plagiarism detection' },
  { name: 'Grammarly', desc: 'Grammar & style' },
  { name: 'Zotero', desc: 'Citation management' },
  { name: 'Mendeley', desc: 'Reference manager' },
]

const stats = [
  { value: '52,000+', label: 'Papers Delivered' },
  { value: '99.2%', label: 'On-Time Rate' },
  { value: '4.9/5', label: 'Average Rating' },
]

export default function QualityAssurance() {
  return (
    <section className="bg-charcoal py-24">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-14"
        >
          <p className="text-sm font-medium text-gray-400 uppercase tracking-widest mb-3">
            Our Promise
          </p>
          <h2 className="font-display text-4xl font-semibold text-white">
            Quality You Can Count On
          </h2>
          <p className="mt-4 text-lg text-gray-300 max-w-xl mx-auto">
            We hold ourselves to the highest standards of academic integrity at every step of the
            process.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start mb-16">
          {/* Left: Checklist */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
          >
            <div className="space-y-4">
              {guarantees.map((item, i) => (
                <motion.div
                  key={item}
                  initial={{ opacity: 0, x: -16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.08 }}
                  className="flex items-center gap-4"
                >
                  <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <span className="text-base text-white">{item}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Right: Tools + Stats */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
          >
            <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-400 mb-5">
              Quality Tools We Use
            </h3>
            <div className="grid grid-cols-2 gap-3 mb-10">
              {tools.map((tool) => (
                <div
                  key={tool.name}
                  className="bg-white/10 border border-white/20 rounded-xl px-5 py-4 hover:bg-white/15 transition-colors"
                >
                  <p className="text-white font-semibold text-sm">{tool.name}</p>
                  <p className="text-gray-400 text-xs mt-0.5">{tool.desc}</p>
                </div>
              ))}
            </div>

            <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-400 mb-5">
              Our Track Record
            </h3>
            <div className="grid grid-cols-3 gap-4">
              {stats.map((stat, i) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  className="bg-white/10 border border-white/20 rounded-xl p-5 text-center"
                >
                  <p className="font-display text-2xl font-semibold text-ctaBlue">{stat.value}</p>
                  <p className="text-xs text-gray-400 mt-1">{stat.label}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
