'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  PlusCircle,
  ShoppingBag,
  FileText,
  MessageSquare,
  LogOut,
  User,
  ChevronRight,
} from 'lucide-react'

interface UserData {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'student' | 'researcher'
}

const studentQuickLinks = [
  {
    label: 'Post a Job',
    description: 'Submit a new research assignment',
    href: '/jobs/new',
    icon: PlusCircle,
    color: '#007BFF',
  },
  {
    label: 'Browse Marketplace',
    description: 'Find available research opportunities',
    href: '/marketplace',
    icon: ShoppingBag,
    color: '#457B9D',
  },
  {
    label: 'My Contracts',
    description: 'View your active orders',
    href: '/contracts',
    icon: FileText,
    color: '#1D3557',
  },
  {
    label: 'Messages',
    description: 'Communicate with your researcher',
    href: '/messages',
    icon: MessageSquare,
    color: '#457B9D',
  },
]

const researcherQuickLinks = [
  {
    label: 'Browse Jobs',
    description: 'Find research opportunities to bid on',
    href: '/marketplace',
    icon: ShoppingBag,
    color: '#007BFF',
  },
  {
    label: 'My Contracts',
    description: 'View your active assignments',
    href: '/contracts',
    icon: FileText,
    color: '#457B9D',
  },
  {
    label: 'Messages',
    description: 'Communicate with your clients',
    href: '/messages',
    icon: MessageSquare,
    color: '#1D3557',
  },
  {
    label: 'My Profile',
    description: 'Update your expertise and credentials',
    href: '/profile',
    icon: User,
    color: '#457B9D',
  },
]

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<UserData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    const userData = localStorage.getItem('user')

    if (!token) {
      router.push('/auth/login?redirect=/dashboard')
      return
    }

    if (userData) {
      try {
        setUser(JSON.parse(userData))
      } catch {
        localStorage.removeItem('user')
        localStorage.removeItem('auth_token')
        router.push('/auth/login')
        return
      }
    }

    setLoading(false)
  }, [router])

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-lightGrey flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-ctaBlue border-t-transparent rounded-full animate-spin" />
          <p className="text-medGrey text-sm">Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  const quickLinks = user?.role === 'researcher' ? researcherQuickLinks : studentQuickLinks

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[1280px] mx-auto px-6 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-start justify-between mb-10"
        >
          <div>
            <p className="text-sm text-medGrey mb-1 uppercase tracking-wide font-medium">
              {user?.role === 'researcher' ? 'Researcher Dashboard' : 'Student Dashboard'}
            </p>
            <h1 className="font-display text-4xl font-semibold text-charcoal">
              Welcome back, {user?.first_name || 'there'}
            </h1>
            <p className="text-medGrey mt-2">{user?.email}</p>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-medGrey hover:text-charcoal hover:bg-white border border-divider rounded-lg px-4 py-2.5 transition-all duration-200"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </motion.div>

        {/* Role badge */}
        <div className="mb-8">
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full ${
              user?.role === 'researcher'
                ? 'bg-steelBlue/10 text-steelBlue'
                : 'bg-ctaBlue/10 text-ctaBlue'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            {user?.role === 'researcher' ? 'Verified Researcher' : 'Student Account'}
          </span>
        </div>

        {/* Quick Links Grid */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-charcoal mb-5">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickLinks.map((link, i) => {
              const Icon = link.icon
              return (
                <motion.div
                  key={link.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: i * 0.08 }}
                >
                  <Link
                    href={link.href}
                    className="group bg-white rounded-2xl border border-divider p-6 flex flex-col hover:border-steelBlue/40 hover:shadow-lg transition-all duration-300 h-full"
                  >
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110"
                      style={{ backgroundColor: `${link.color}15` }}
                    >
                      <Icon className="w-5 h-5" style={{ color: link.color }} />
                    </div>
                    <h3 className="font-semibold text-charcoal text-sm mb-1">{link.label}</h3>
                    <p className="text-xs text-medGrey leading-relaxed flex-1">
                      {link.description}
                    </p>
                    <div className="flex items-center gap-1 mt-3 text-xs font-medium text-ctaBlue group-hover:gap-2 transition-all">
                      Open
                      <ChevronRight className="w-3.5 h-3.5" />
                    </div>
                  </Link>
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* Stats placeholder */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="bg-white rounded-2xl border border-divider p-8"
        >
          <h2 className="text-lg font-semibold text-charcoal mb-6">Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {(user?.role === 'researcher'
              ? [
                  { label: 'Active Bids', value: '0' },
                  { label: 'Active Contracts', value: '0' },
                  { label: 'Completed', value: '0' },
                  { label: 'Earnings', value: '$0.00' },
                ]
              : [
                  { label: 'Active Orders', value: '0' },
                  { label: 'Completed', value: '0' },
                  { label: 'In Review', value: '0' },
                  { label: 'Total Spent', value: '$0.00' },
                ]
            ).map((stat) => (
              <div key={stat.label} className="text-center p-4 bg-lightGrey rounded-xl">
                <p className="font-display text-2xl font-semibold text-charcoal">{stat.value}</p>
                <p className="text-xs text-medGrey mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
