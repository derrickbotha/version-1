import type { Metadata } from 'next'
import { Playfair_Display, Inter } from 'next/font/google'
import './globals.css'
import AppShell from '@/components/layout/AppShell'

const playfair = Playfair_Display({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-playfair',
  display: 'swap',
})

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'ResearchPro | Premium Academic Research Services',
  description:
    'Work with PhD-level researchers and advanced AI-assisted research tools to produce high-quality academic work. 52,000+ papers completed, 4.9★ rating.',
  keywords:
    'academic research, research writing, dissertation help, thesis writing, PhD writers, essay writing service, academic papers',
  openGraph: {
    title: 'ResearchPro | Premium Academic Research Services',
    description:
      'Work with PhD-level researchers to produce high-quality academic work. 52,000+ papers completed.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${playfair.variable} ${inter.variable}`}>
      <body className="font-sans antialiased bg-white text-charcoal">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
