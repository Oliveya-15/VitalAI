/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Sea-green brand palette (buttons, active menu, accents)
        brand: {
          50: '#effaf6', 100: '#d6f1e8', 200: '#b0e2d2', 300: '#85d0ba', 400: '#5fbca3',
          500: '#4aa98f', 600: '#3d9a83', 700: '#2f7f6b', 800: '#26665a', 900: '#1f5a4b',
        },
        // "Success" greens used by badges/status -> same soft sea-green family
        emerald: {
          50: '#eefaf5', 100: '#d5efe6', 200: '#b3e0d0', 300: '#8accb7', 400: '#66b89e',
          500: '#4aa98f', 600: '#3d9a83', 700: '#2f7d68', 800: '#256452', 900: '#1d4f42',
        },
        // Softer "emergency" red: pastel coral-rose instead of bright red
        red: {
          50: '#fdf3f3', 100: '#fbe3e4', 200: '#f6cfd1', 300: '#eeaeb2', 400: '#e48e94',
          500: '#dc7a80', 600: '#d4636a', 700: '#bf5057', 800: '#9a4046', 900: '#7a3438',
        },
        mint: '#f3faf7',
        ink: '#0f172a',
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}