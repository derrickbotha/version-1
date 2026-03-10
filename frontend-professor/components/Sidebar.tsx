'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard, ClipboardList, Star, BookOpen,
  Award, AlertCircle, TrendingUp, User, LogOut, ChevronRight,
  GraduationCap, Briefcase,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV = [
  { label: 'Dashboard',       href: '/dashboard', icon: LayoutDashboard },
  { label: 'Job Marketplace', href: '/jobs',       icon: Briefcase       },
  { label: 'Review Queue',   href: '/queue',        icon: ClipboardList   },
  { label: 'Quality Reviews',href: '/reviews',      icon: Star            },
  { label: 'Assignments',    href: '/assignments',  icon: BookOpen        },
  { label: 'Credentials',    href: '/credentials',  icon: Award           },
  { label: 'Disputes',       href: '/disputes',     icon: AlertCircle     },
  { label: 'Analytics',      href: '/analytics',    icon: TrendingUp      },
]

interface Props { name: string; email: string; status: string }

export default function Sidebar({ name, email, status }: Props) {
  const pathname = usePathname()
  const router   = useRouter()

  function signOut() {
    localStorage.removeItem('prof_token')
    localStorage.removeItem('prof_user')
    router.push('/auth/login')
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-profDark flex flex-col z-40">

      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-profTeal rounded-lg flex items-center justify-center flex-shrink-0">
            <GraduationCap className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <div className="text-white font-semibold text-sm leading-tight">ResearchPro</div>
            <div className="text-profTeal text-[10px] font-medium">Professor Portal</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <p className="px-3 mb-2 text-[10px] font-semibold text-white/30 uppercase tracking-widest">
          Menu
        </p>
        <ul className="space-y-0.5">
          {NAV.map(({ label, href, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    active
                      ? 'bg-profTeal text-white'
                      : 'text-white/70 hover:bg-white/10 hover:text-white'
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {label}
                  {active && <ChevronRight className="w-3.5 h-3.5 ml-auto opacity-60" />}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Bottom account section */}
      <div className="border-t border-white/10 px-3 py-4 space-y-1">
        {/* Approval status badge */}
        {status && (
          <div className={cn(
            'mx-3 mb-2 px-2 py-1 rounded text-[10px] font-semibold text-center uppercase tracking-wide',
            status === 'approved'  ? 'bg-green-900/50 text-green-400'  :
            status === 'pending'   ? 'bg-yellow-900/50 text-yellow-400' :
            status === 'rejected'  ? 'bg-red-900/50 text-red-400'      :
                                     'bg-white/10 text-white/50'
          )}>
            {status}
          </div>
        )}

        <Link
          href="/account"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-white/70 hover:bg-white/10 hover:text-white transition-colors"
        >
          <User className="w-4 h-4 flex-shrink-0" />
          My Profile
        </Link>
        <button
          onClick={signOut}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-white/70 hover:bg-red-900/40 hover:text-red-300 transition-colors"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          Sign Out
        </button>

        {/* User card */}
        <div className="flex items-center gap-3 px-3 py-3 mt-1 rounded-lg bg-white/5">
          <div className="w-8 h-8 rounded-full bg-profTeal/30 flex items-center justify-center flex-shrink-0">
            <span className="text-profTeal text-xs font-bold">
              {name?.[0]?.toUpperCase() ?? 'P'}
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-white truncate">{name}</p>
            <p className="text-[10px] text-white/40 truncate">{email}</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
