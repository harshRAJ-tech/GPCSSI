import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/cases': 'http://127.0.0.1:8000',
      '/search': 'http://127.0.0.1:8000',
      '/dashboard': 'http://127.0.0.1:8000',
    }
  }
})
