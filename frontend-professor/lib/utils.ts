import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export function fmtDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function timeUntil(due: string | null): { label: string; urgent: boolean } {
  if (!due) return { label: 'No deadline', urgent: false }
  const diff = new Date(due).getTime() - Date.now()
  const hours = Math.floor(diff / 3_600_000)
  if (hours < 0) return { label: 'OVERDUE', urgent: true }
  if (hours < 4) return { label: `${hours}h left`, urgent: true }
  if (hours < 24) return { label: `${hours}h left`, urgent: false }
  return { label: `${Math.floor(hours / 24)}d left`, urgent: false }
}
