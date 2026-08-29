/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f5ff',
          100: '#e0ecff',
          200: '#c7dcfe',
          300: '#a3c4fd',
          400: '#75a3fa',
          500: '#497df5',
          600: '#2b5aed',
          700: '#1e42d7',
          800: '#002266',
          900: '#001747',
          950: '#000c29',
        }
      }
    },
  },
  plugins: [],
}
