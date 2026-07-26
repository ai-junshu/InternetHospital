import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 本地开发：/api 代理至 backend（8000），与 infra/nginx/dev.conf 一致
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': '/src' },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
