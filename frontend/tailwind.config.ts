import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        syn: {
          brand: '#0D7A5F',
          brandLight: '#E6F4F0',
          surface: '#F7F8FA',
          panel: '#FFFFFF',
          ink: '#111827',
          muted: '#6B7280',
          border: '#E5E7EB',
        },
        clinic: {
          canvas: '#f8fafc',
          surface: '#ffffff',
          primary: '#059669',
          primaryHover: '#047857',
          critical: '#dc2626',
          criticalFill: '#fff1f1',
          urgent: '#f59e0b',
          urgentFill: '#fef3c7',
          routine: '#0284c7',
          routineFill: '#e0f2fe',
        },
      },
      keyframes: {
        overtakePulse: {
          '0%, 100%': { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(220, 38, 38, 0)' },
          '50%': { transform: 'scale(1.015)', boxShadow: '0 0 0 6px rgba(220, 38, 38, 0.18)' },
        },
      },
      animation: {
        'overtake-pulse': 'overtakePulse 0.7s ease-in-out 3',
      },
      borderRadius: {
        card: '10px',
        badge: '6px',
      },
    },
  },
  plugins: [],
};

export default config;
