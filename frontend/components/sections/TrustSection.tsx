'use client'

import { motion } from 'framer-motion'

const institutions = [
  { name: 'Elsevier', color: '#FF6900' },
  { name: 'Springer Nature', color: '#E4003A' },
  { name: 'IEEE', color: '#00629B' },
  { name: 'JSTOR', color: '#1A3A5C' },
  { name: 'PubMed', color: '#005B94' },
  { name: 'ScienceDirect', color: '#E67C08' },
  { name: 'Google Scholar', color: '#4285F4' },
  { name: 'Taylor & Francis', color: '#C8102E' },
  { name: 'Wiley', color: '#004488' },
  { name: 'Scopus', color: '#E37222' },
  { name: 'Web of Science', color: '#003087' },
  { name: 'Oxford Academic', color: '#002147' },
]

export default function TrustSection() {
  return (
    <section className="bg-lightGrey py-20">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            Research Sources
          </p>
          <h2 className="font-display text-3xl font-semibold text-charcoal">
            Trusted Academic Research Sources
          </h2>
          <p className="mt-4 text-medGrey max-w-xl mx-auto">
            Our researchers draw from the world&apos;s most respected academic databases and
            publishers to deliver authoritative, well-cited work.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {institutions.map((inst, i) => (
            <motion.div
              key={inst.name}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
              className="group bg-white border border-divider rounded-xl px-4 py-5 flex items-center justify-center hover:border-steelBlue hover:shadow-md transition-all duration-300 cursor-default"
            >
              <span
                className="text-sm font-semibold text-center leading-tight opacity-70 group-hover:opacity-100 transition-opacity"
                style={{ color: inst.color }}
              >
                {inst.name}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
