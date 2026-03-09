'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const services = [
  { label: 'Custom Writing', href: '/services/custom-writing' },
  { label: 'Thesis Writing', href: '/services/thesis' },
  { label: 'Dissertation Writing', href: '/services/dissertation' },
  { label: 'Coursework Writing', href: '/services/coursework' },
  { label: 'Research Paper Writing', href: '/services/research-paper' },
  { label: 'Assignment Writing', href: '/services/assignment' },
  { label: 'College Essay Writing', href: '/services/college-essay' },
  { label: 'All Services →', href: '/services' },
]

const navLinks = [
  { label: 'Home', href: '/' },
  { label: 'How It Works', href: '/#how-it-works' },
  { label: 'AI Use', href: '/#process' },
  { label: 'Services', href: '#', hasDropdown: true },
  { label: 'Pricing', href: '/#pricing' },
  { label: 'Blog', href: '/blog' },
]

export default function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [servicesOpen, setServicesOpen] = useState(false)
  const pathname = usePathname()
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 10)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setServicesOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    setMobileOpen(false)
    setServicesOpen(false)
  }, [pathname])

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        isScrolled
          ? 'bg-white shadow-sm border-b border-divider'
          : 'bg-white border-b border-divider'
      )}
      style={{ height: '80px' }}
    >
      <div className="max-w-[1280px] mx-auto px-6 h-full flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="font-display text-2xl font-semibold text-charcoal tracking-tight hover:text-steelBlue transition-colors"
        >
          ResearchPro
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden lg:flex items-center gap-8">
          {navLinks.map((link) =>
            link.hasDropdown ? (
              <div key={link.label} className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setServicesOpen((v) => !v)}
                  className={cn(
                    'flex items-center gap-1 text-sm font-medium transition-colors',
                    servicesOpen ? 'text-ctaBlue' : 'text-charcoal hover:text-steelBlue'
                  )}
                >
                  {link.label}
                  <ChevronDown
                    className={cn('w-4 h-4 transition-transform', servicesOpen && 'rotate-180')}
                  />
                </button>

                <AnimatePresence>
                  {servicesOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.18 }}
                      className="absolute top-full left-1/2 -translate-x-1/2 mt-3 w-[320px] bg-white rounded-xl shadow-xl border border-divider overflow-hidden"
                    >
                      <div className="p-2">
                        {services.map((s) => (
                          <Link
                            key={s.href}
                            href={s.href}
                            className="flex items-center px-4 py-2.5 text-sm text-charcoal hover:bg-lightGrey hover:text-steelBlue rounded-lg transition-colors"
                            onClick={() => setServicesOpen(false)}
                          >
                            {s.label}
                          </Link>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'text-sm font-medium transition-colors',
                  pathname === link.href
                    ? 'text-ctaBlue'
                    : 'text-charcoal hover:text-steelBlue'
                )}
              >
                {link.label}
              </Link>
            )
          )}
        </nav>

        {/* Right CTA */}
        <div className="hidden lg:flex items-center gap-4">
          <Link
            href="/auth/login"
            className="text-sm font-medium text-charcoal hover:text-steelBlue transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/auth/register"
            className="bg-ctaBlue text-white text-sm font-medium px-5 py-2.5 rounded-lg hover:bg-steelBlue transition-all duration-200 shadow-sm hover:shadow-md"
          >
            Order Now
          </Link>
        </div>

        {/* Mobile Hamburger */}
        <button
          className="lg:hidden p-2 text-charcoal hover:text-steelBlue transition-colors"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="lg:hidden bg-white border-t border-divider overflow-hidden"
          >
            <div className="max-w-[1280px] mx-auto px-6 py-4 flex flex-col gap-1">
              {navLinks.map((link) =>
                link.hasDropdown ? (
                  <div key={link.label}>
                    <button
                      onClick={() => setServicesOpen((v) => !v)}
                      className="flex items-center gap-1 w-full text-left px-3 py-2.5 text-sm font-medium text-charcoal hover:text-steelBlue hover:bg-lightGrey rounded-lg transition-colors"
                    >
                      {link.label}
                      <ChevronDown
                        className={cn(
                          'w-4 h-4 ml-auto transition-transform',
                          servicesOpen && 'rotate-180'
                        )}
                      />
                    </button>
                    <AnimatePresence>
                      {servicesOpen && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="pl-4"
                        >
                          {services.map((s) => (
                            <Link
                              key={s.href}
                              href={s.href}
                              className="block px-3 py-2 text-sm text-medGrey hover:text-steelBlue hover:bg-lightGrey rounded-lg transition-colors"
                            >
                              {s.label}
                            </Link>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ) : (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      'px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
                      pathname === link.href
                        ? 'text-ctaBlue bg-blue-50'
                        : 'text-charcoal hover:text-steelBlue hover:bg-lightGrey'
                    )}
                  >
                    {link.label}
                  </Link>
                )
              )}
              <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-divider">
                <Link
                  href="/auth/login"
                  className="px-3 py-2.5 text-sm font-medium text-charcoal hover:text-steelBlue hover:bg-lightGrey rounded-lg transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/auth/register"
                  className="bg-ctaBlue text-white text-sm font-medium px-5 py-2.5 rounded-lg hover:bg-steelBlue transition-colors text-center"
                >
                  Order Now
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
