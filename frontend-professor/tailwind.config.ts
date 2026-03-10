import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        charcoal: '#212529',
        steelBlue: '#457B9D',
        ctaBlue: '#007BFF',
        lightGrey: '#F5F7FA',
        medGrey: '#6C757D',
        divider: '#E6E9ED',
        // Professor brand — teal accent instead of blue
        profTeal: '#0D9488',
        profDark: '#134E4A',
        profLight: '#F0FDFA',
      },
      fontFamily: {
        sans: ['Inter', 'Helvetica', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
