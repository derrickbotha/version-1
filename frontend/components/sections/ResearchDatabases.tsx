'use client'

import { motion } from 'framer-motion'

const databases = [
  { name: 'Elsevier', color: '#FF6900' },
  { name: 'Springer Nature', color: '#E4003A' },
  { name: 'IEEE', color: '#00629B' },
  { name: 'Taylor & Francis', color: '#C8102E' },
  { name: 'Wiley', color: '#004488' },
  { name: 'JSTOR', color: '#1A3A5C' },
  { name: 'PubMed', color: '#005B94' },
  { name: 'Scopus', color: '#E37222' },
  { name: 'Web of Science', color: '#003087' },
  { name: 'ScienceDirect', color: '#E67C08' },
  { name: 'Google Scholar', color: '#4285F4' },
  { name: 'Oxford Academic', color: '#002147' },
]

// Duplicate for seamless loop
const allDatabases = [...databases, ...databases]

export default function ResearchDatabases() {
  return (
    <section className="bg-white py-20 overflow-hidden">
      <div className="max-w-[1280px] mx-auto px-6 mb-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            Data Sources
          </p>
          <h2 className="font-display text-4xl font-semibold text-charcoal">
            Global Academic Database Access
          </h2>
          <p className="mt-4 text-lg text-medGrey max-w-xl mx-auto">
            Every paper is backed by research from the world&apos;s leading academic repositories
            and publishing houses.
          </p>
        </motion.div>
      </div>

      {/* Scrolling carousel */}
      <div className="relative w-full overflow-hidden">
        {/* Fade masks */}
        <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-white to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-white to-transparent z-10 pointer-events-none" />

        <div className="carousel-track gap-4 py-3">
          {allDatabases.map((db, i) => (
            <div
              key={`${db.name}-${i}`}
              className="flex-shrink-0 bg-white border border-divider rounded-xl px-8 py-5 flex items-center justify-center min-w-[180px] hover:border-steelBlue hover:shadow-md transition-all duration-300"
            >
              <span
                className="text-sm font-semibold whitespace-nowrap"
                style={{ color: db.color }}
              >
                {db.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
