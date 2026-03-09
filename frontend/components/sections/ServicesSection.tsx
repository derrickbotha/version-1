'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  BookOpen,
  GraduationCap,
  FileText,
  BookMarked,
  PenLine,
  ClipboardList,
  ScrollText,
  Layers,
  Library,
} from 'lucide-react'

const services = [
  {
    icon: BookOpen,
    title: 'Custom Writing',
    description: 'Tailored academic content crafted to your exact specifications and guidelines.',
    href: '/services/custom-writing',
  },
  {
    icon: GraduationCap,
    title: 'Thesis Writing',
    description: 'Expert thesis development from proposal through final submission with precision.',
    href: '/services/thesis',
  },
  {
    icon: ScrollText,
    title: 'Dissertation Writing',
    description: 'Comprehensive dissertation support with original research and rigorous methodology.',
    href: '/services/dissertation',
  },
  {
    icon: ClipboardList,
    title: 'Coursework Writing',
    description: 'High-quality coursework assignments delivered on time for any subject area.',
    href: '/services/coursework',
  },
  {
    icon: FileText,
    title: 'Research Paper Writing',
    description: 'Peer-review ready research papers with proper citations and academic rigor.',
    href: '/services/research-paper',
  },
  {
    icon: PenLine,
    title: 'Assignment Writing',
    description: 'Precise, well-structured assignments across all academic disciplines and levels.',
    href: '/services/assignment',
  },
  {
    icon: BookMarked,
    title: 'College Essay Writing',
    description: 'Compelling college essays that tell your story and impress admissions committees.',
    href: '/services/college-essay',
  },
  {
    icon: Layers,
    title: 'Case Study Writing',
    description: 'In-depth case studies with thorough analysis, findings, and recommendations.',
    href: '/services/case-study',
  },
  {
    icon: Library,
    title: 'Literature Review',
    description: 'Comprehensive, synthesized literature reviews from current academic sources.',
    href: '/services/literature-review',
  },
]

export default function ServicesSection() {
  return (
    <section id="services" className="bg-white py-24">
      <div className="max-w-[1280px] mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-14"
        >
          <p className="text-sm font-medium text-medGrey uppercase tracking-widest mb-3">
            What We Offer
          </p>
          <h2 className="font-display text-4xl font-semibold text-charcoal">
            Academic Services for Every Need
          </h2>
          <p className="mt-4 text-lg text-medGrey max-w-2xl mx-auto leading-relaxed">
            From undergraduate essays to doctoral dissertations — our expert researchers cover every
            academic writing need with precision and integrity.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((service, i) => {
            const Icon = service.icon
            return (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.07 }}
                whileHover={{ y: -4 }}
                className="group bg-white border border-divider rounded-2xl p-7 hover:shadow-xl hover:border-steelBlue/30 transition-all duration-300 cursor-default"
              >
                <div className="w-12 h-12 rounded-xl bg-steelBlue/10 flex items-center justify-center mb-5 group-hover:bg-steelBlue/20 transition-colors">
                  <Icon className="w-6 h-6 text-steelBlue" />
                </div>
                <h3 className="font-display text-xl font-semibold text-charcoal mb-2">
                  {service.title}
                </h3>
                <p className="text-sm text-medGrey leading-relaxed mb-5">
                  {service.description}
                </p>
                <Link
                  href={service.href}
                  className="text-sm font-medium text-ctaBlue hover:text-steelBlue transition-colors inline-flex items-center gap-1"
                >
                  Learn More
                  <span className="transition-transform group-hover:translate-x-1">→</span>
                </Link>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
