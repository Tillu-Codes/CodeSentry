/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: {
          950: '#0a0a14',
          900: '#10101f',
          800: '#161629',
          700: '#1e1e35',
          600: '#272748',
        },
      },
    },
  },
  plugins: [],
}