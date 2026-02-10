import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to backend during development
      '/api': {
        target: 'http://localhost:8007',
        changeOrigin: true,
        secure: false
      },
      '/health': {
        target: 'http://localhost:8007',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
