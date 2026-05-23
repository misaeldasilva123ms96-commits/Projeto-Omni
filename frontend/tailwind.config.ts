import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Geist', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        cosmic: {
          void: '#060714',
          panel: '#0d1024',
          card: '#11142b',
          border: 'rgba(144, 102, 255, 0.22)',
          mist: '#191d3f',
        },
        neon: {
          purple: '#b56dff',
          violet: '#7b61ff',
          blue: '#4ea4ff',
          cyan: '#51f6ff',
          aqua: '#37d8ff',
          mint: '#4effc7',
        },
      },
      boxShadow: {
        'neon-purple': '0 0 0 1px rgba(181,109,255,0.18), 0 0 24px rgba(181,109,255,0.25), 0 24px 60px rgba(4,8,32,0.55)',
        'neon-blue': '0 0 0 1px rgba(78,164,255,0.18), 0 0 22px rgba(78,164,255,0.22), 0 24px 60px rgba(4,8,32,0.55)',
        'glass-edge': 'inset 0 1px 0 rgba(255,255,255,0.08), 0 24px 60px rgba(0,0,0,0.4)',
      },
      backgroundImage: {
        'cosmic-gradient': 'radial-gradient(circle at top left, rgba(112, 74, 255, 0.24), transparent 30%), radial-gradient(circle at 80% 18%, rgba(81, 246, 255, 0.14), transparent 22%), radial-gradient(circle at bottom center, rgba(78, 164, 255, 0.12), transparent 34%), linear-gradient(180deg, #03040c 0%, #070917 36%, #0a0d20 100%)',
        'panel-gradient': 'linear-gradient(135deg, rgba(27, 30, 61, 0.78), rgba(12, 15, 34, 0.7))',
        'neon-stroke': 'linear-gradient(135deg, rgba(181,109,255,0.42), rgba(78,164,255,0.32), rgba(81,246,255,0.18))',
      },
      backdropBlur: {
        xs: '2px',
      },
      keyframes: {
        shimmer: {
          '0%': { opacity: '0.45', transform: 'translateX(-6px)' },
          '50%': { opacity: '1', transform: 'translateX(0px)' },
          '100%': { opacity: '0.45', transform: 'translateX(6px)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        pulseRing: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(181,109,255,0.0), 0 0 24px rgba(181,109,255,0.28)' },
          '50%': { boxShadow: '0 0 0 6px rgba(181,109,255,0.08), 0 0 34px rgba(78,164,255,0.3)' },
        },
      },
      animation: {
        shimmer: 'shimmer 3.6s ease-in-out infinite',
        float: 'float 6s ease-in-out infinite',
        'pulse-ring': 'pulseRing 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

export default config
