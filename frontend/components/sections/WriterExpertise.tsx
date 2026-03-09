'use client'

import { motion } from 'framer-motion'
import { BadgeCheck, BookOpen } from 'lucide-react'

const writers = [
  {
    initials: 'SM',
    name: 'Dr. Sarah Mitchell',
    credential: 'PhD Economics',
    years: 12,
    specialty: 'Macroeconomics & Policy',
    highlight: 'Published in 40+ peer-reviewed journals',
    completions: 1840,
    rating: 4.97,
    color: '#457B9D',
  },
  {
    initials: 'JC',
    name: 'Prof. James Chen',
    credential: 'PhD Computer Science',
    years: 9,
    specialty: 'ML & Systems Research',
    highlight: 'Former MIT research associate',
    completions: 1230,
    rating: 4.95,
    color: '#007BFF',
  },
  {
    initials: 'AO',
    name: 'Dr. Amara Osei',
    credential: 'PhD Medicine',
    years: 15,
    specialty: 'Clinical & Biomedical Research',
    highlight: 'Clinical research specialist',
    completions: 2100,
    rating: 4.98,
    color: '#1D3557',
  },
]

const fields = [
  'Economics',
  'Law',
  'Engineering',
  'Medicine',
  'Computer Science',
  'Physics',
  'Literature',
  'Psychology',
  'History',
  'Business',
  'Chemistry',
  'Political Science',
]

export default function WriterExpertise() {
  return (
    <section className="bg-white py-24">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-14"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            Our Team
          </p>
          <h2 className="font-display text-4xl font-semibold text-charcoal">
            Meet Our Expert Researchers
          </h2>
          <p className="mt-4 text-lg text-medGrey max-w-xl mx-auto">
            Every researcher on our platform holds an advanced degree and has been rigorously
            vetted for academic excellence.
          </p>
        </motion.div>

        {/* Writer Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-14">
          {writers.map((writer, i) => (
            <motion.div
              key={writer.name}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className="bg-white border border-divider rounded-2xl p-7 hover:shadow-lg hover:border-steelBlue/30 transition-all duration-300"
            >
              {/* Avatar */}
              <div className="flex items-start gap-4 mb-5">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center text-white text-lg font-bold flex-shrink-0"
                  style={{ backgroundColor: writer.color }}
                >
                  {writer.initials}
                </div>
                <div>
                  <h3 className="font-display text-lg font-semibold text-charcoal leading-tight">
                    {writer.name}
                  </h3>
                  <span
                    className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full mt-1 text-white"
                    style={{ backgroundColor: writer.color }}
                  >
                    <BadgeCheck className="w-3 h-3" />
                    {writer.credential}
                  </span>
                </div>
              </div>

              <div className="mb-4">
                <p className="text-sm text-medGrey flex items-center gap-1.5 mb-1">
                  <BookOpen className="w-3.5 h-3.5" />
                  {writer.specialty}
                </p>
                <p className="text-sm font-medium text-charcoal mt-2">
                  &ldquo;{writer.highlight}&rdquo;
                </p>
              </div>

              <div className="border-t border-divider pt-4 grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-base font-bold text-charcoal">{writer.years}</p>
                  <p className="text-xs text-medGrey">Years Exp.</p>
                </div>
                <div>
                  <p className="text-base font-bold text-charcoal">
                    {writer.completions.toLocaleString()}
                  </p>
                  <p className="text-xs text-medGrey">Papers</p>
                </div>
                <div>
                  <p className="text-base font-bold text-charcoal">{writer.rating}★</p>
                  <p className="text-xs text-medGrey">Rating</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Fields row */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center"
        >
          <p className="text-sm text-medGrey mb-5">
            Expert researchers available across all major disciplines:
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {fields.map((field) => (
              <span
                key={field}
                className="bg-lightGrey border border-divider text-sm text-charcoal px-4 py-1.5 rounded-full hover:bg-steelBlue/10 hover:border-steelBlue hover:text-steelBlue transition-colors cursor-default"
              >
                {field}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
