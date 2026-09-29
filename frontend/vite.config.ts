import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': `${import.meta.dirname}/src`,
      '@components': `${import.meta.dirname}/src/components`,
      '@pages': `${import.meta.dirname}/src/pages`,
      '@design-system': `${import.meta.dirname}/src/design-system`,
      '@hooks': `${import.meta.dirname}/src/hooks`,
      '@services': `${import.meta.dirname}/src/services`,
      '@types': `${import.meta.dirname}/src/types`,
      '@utils': `${import.meta.dirname}/src/utils`,
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to FastAPI backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
