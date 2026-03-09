'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const testimonials = [
  {
    id: 1,
    quote:
      'Exceptional quality on my economics dissertation. The research depth and citation accuracy were beyond what I expected. Every source was impeccably formatted and the argument was logically airtight.',
    name: 'Emily R.',
    university: 'Harvard University',
    country: 'USA',
    initials: 'ER',
    color: '#457B9D',
    stars: 5,
  },
  {
    id: 2,
    quote:
      'My thesis on sustainable energy policy was delivered two days ahead of schedule. The PhD-level expertise shone through every page. The lit review alone was worth five times what I paid.',
    name: 'Carlos M.',
    university: 'University of Barcelona',
    country: 'Spain',
    initials: 'CM',
    color: '#007BFF',
    stars: 5,
  },
  {
    id: 3,
    quote:
      "The research depth was unparalleled. My supervisor was impressed and said it was one of the best literature reviews she had seen in years. I couldn't have asked for better quality.",
    name: 'Priya S.',
    university: 'London School of Economics',
    country: 'UK',
    initials: 'PS',
    color: '#1D3557',
    stars: 5,
  },
  {
    id: 4,
    quote:
      'Delivered ahead of my deadline with meticulous attention to APA formatting. My nursing research paper was written with genuine clinical expertise. I will use ResearchPro for my entire program.',
    name: 'James K.',
    university: 'University of Toronto',
    country: 'Canada',
    initials: 'JK',
    color: '#457B9D',
    stars: 5,
  },
  {
    id: 5,
    quote:
      'Phenomenal service from start to finish. The researcher communicated proactively and delivered a 40-page dissertation chapter that was publication quality. Absolutely outstanding.',
    name: 'Aisha N.',
    university: 'University of Cape Town',
    country: 'South Africa',
    initials: 'AN',
    color: '#007BFF',
    stars: 5,
  },
]

export default function Testimonials() {
  const [current, setCurrent] = useState(0)
  const [direction, setDirection] = useState(1)

  const goTo = useCallback(
    (idx: number) => {
      setDirection(idx > current ? 1 : -1)
      setCurrent(idx)
    },
    [current]
  )

  useEffect(() => {
    const timer = setInterval(() => {
      setDirection(1)
      setCurrent((c) => (c + 1) % testimonials.length)
    }, 6000)
    return () => clearInterval(timer)
  }, [])

  const t = testimonials[current]

  return (
    <section className="bg-lightGrey py-24 overflow-hidden">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-14"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            Student Reviews
          </p>
          <h2 className="font-display text-4xl font-semibold text-charcoal">
            What Our Students Say
          </h2>
        </motion.div>

        <div className="max-w-3xl mx-auto relative">
          {/* Decorative quote mark */}
          <div className="absolute -top-4 -left-4 font-display text-[120px] leading-none text-steelBlue/10 select-none pointer-events-none">
            &ldquo;
          </div>

          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={t.id}
              custom={direction}
              variants={{
                enter: (dir: number) => ({
                  x: dir > 0 ? 60 : -60,
                  opacity: 0,
                }),
                center: { x: 0, opacity: 1 },
                exit: (dir: number) => ({
                  x: dir > 0 ? -60 : 60,
                  opacity: 0,
                }),
              }}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.4, ease: 'easeInOut' }}
              className="bg-white rounded-2xl border border-divider p-10 shadow-sm relative"
            >
              {/* Stars */}
              <div className="flex gap-1 mb-6">
                {Array.from({ length: t.stars }).map((_, i) => (
                  <svg
                    key={i}
                    className="w-5 h-5 text-yellow-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>

              <p className="text-charcoal text-lg leading-relaxed font-medium italic mb-8 relative z-10">
                &ldquo;{t.quote}&rdquo;
              </p>

              {/* Author */}
              <div className="flex items-center gap-4">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0"
                  style={{ backgroundColor: t.color }}
                >
                  {t.initials}
                </div>
                <div>
                  <p className="font-semibold text-charcoal text-sm">{t.name}</p>
                  <p className="text-medGrey text-sm">
                    {t.university}, {t.country}
                  </p>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Navigation Dots */}
          <div className="flex justify-center gap-2 mt-8">
            {testimonials.map((_, i) => (
              <button
                key={i}
                onClick={() => goTo(i)}
                className={`transition-all duration-200 rounded-full ${
                  i === current
                    ? 'w-8 h-2.5 bg-steelBlue'
                    : 'w-2.5 h-2.5 bg-divider hover:bg-steelBlue/40'
                }`}
                aria-label={`Go to testimonial ${i + 1}`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
