'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  ShoppingBag,
  PlusCircle,
  FileText,
  ScrollText,
  Wallet,
  LogOut,
  User,
  ChevronRight,
  BookOpen,
  Award,
  Star,
  ClipboardList,
  Shield,
  Users,
  TrendingUp,
  Settings,
  AlertCircle,
  CreditCard,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface StoredUser {
  id: string
  role: string
  first_name: string
  last_name?: string
  email?: string
}

interface SidebarProps {
  user: StoredUser
}

const studentLinks = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Marketplace', href: '/marketplace', icon: ShoppingBag },
  { label: 'Post a Job', href: '/jobs/new', icon: PlusCircle },
  { label: 'My Jobs', href: '/jobs/mine', icon: FileText },
  { label: 'Contracts', href: '/contracts', icon: ScrollText },
  { label: 'Wallet', href: '/wallet', icon: Wallet },
]

const researcherLinks = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Browse Jobs', href: '/marketplace', icon: ShoppingBag },
  { label: 'My Jobs', href: '/jobs/mine', icon: FileText },
  { label: 'Contracts', href: '/contracts', icon: ScrollText },
  { label: 'Wallet', href: '/wallet', icon: Wallet },
]

const professorLinks = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Review Queue', href: '/professor/queue', icon: ClipboardList },
  { label: 'Quality Reviews', href: '/professor/reviews', icon: Star },
  { label: 'Assignments', href: '/professor/assignments', icon: BookOpen },
  { label: 'Credentials', href: '/professor/credentials', icon: Award },
  { label: 'Disputes', href: '/professor/disputes', icon: AlertCircle },
  { label: 'Analytics', href: '/professor/analytics', icon: TrendingUp },
]

const adminLinks = [
  { label: 'Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Users', href: '/admin/users', icon: Users },
  { label: 'Professors', href: '/admin/professors', icon: Award },
  { label: 'Jobs', href: '/admin/jobs', icon: FileText },
  { label: 'Contracts', href: '/admin/contracts', icon: ScrollText },
  { label: 'Disputes', href: '/admin/disputes', icon: AlertCircle },
  { label: 'Payouts', href: '/admin/payouts', icon: CreditCard },
  { label: 'Transactions', href: '/admin/transactions', icon: TrendingUp },
  { label: 'Config', href: '/admin/config', icon: Settings },
  { label: 'Audit Log', href: '/admin/audit-log', icon: Shield },
]

function getLinks(role: string) {
  if (role === 'admin' || role === 'super_admin') return adminLinks
  if (role === 'professor') return professorLinks
  if (role === 'researcher') return researcherLinks
  return studentLinks
}

function getSectionLabel(role: string) {
  if (role === 'admin' || role === 'super_admin') return 'Admin Panel'
  if (role === 'professor') return 'Professor Portal'
  if (role === 'researcher') return 'Researcher Menu'
  return 'Student Menu'
}

export default function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const links = getLinks(user.role)

  function handleSignOut() {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
    router.push('/')
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-divider flex flex-col z-40">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-divider">
        <Link
          href="/dashboard"
          className="font-display text-xl font-semibold text-charcoal hover:text-steelBlue transition-colors"
        >
          ResearchPro
        </Link>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <p className="px-3 mb-2 text-[10px] font-semibold text-medGrey uppercase tracking-widest">
          {getSectionLabel(user.role)}
        </p>
        <ul className="space-y-0.5">
          {links.map(({ label, href, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    active
                      ? 'bg-blue-50 text-ctaBlue'
                      : 'text-charcoal hover:bg-lightGrey hover:text-steelBlue'
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {label}
                  {active && <ChevronRight className="w-3.5 h-3.5 ml-auto opacity-50" />}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Account section */}
      <div className="border-t border-divider px-3 py-4 space-y-1">
        <Link
          href="/account"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-charcoal hover:bg-lightGrey hover:text-steelBlue transition-colors"
        >
          <User className="w-4 h-4 flex-shrink-0" />
          Account Settings
        </Link>
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-charcoal hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          Sign Out
        </button>

        {/* User info */}
        <div className="flex items-center gap-3 px-3 py-3 mt-1 rounded-lg bg-lightGrey">
          <div className="w-8 h-8 rounded-full bg-steelBlue/20 flex items-center justify-center flex-shrink-0">
            <span className="text-steelBlue text-xs font-semibold">
              {user.first_name?.[0]?.toUpperCase() ?? '?'}
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-charcoal truncate">
              {user.first_name} {user.last_name ?? ''}
            </p>
            <p className="text-[10px] text-medGrey capitalize">{user.role}</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
