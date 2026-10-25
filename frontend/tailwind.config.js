/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'seismo-dark': '#0a0a0c',
        'seismo-charcoal': '#0f0f12',
        'seismo-cyan': '#00FFFF',
        'seismo-amber': '#f59e0b',
        'seismo-magenta': '#d946ef',
      },
    },
  },
  plugins: [],
}
