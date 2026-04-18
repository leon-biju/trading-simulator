import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  base: process.env.NODE_ENV === 'production' ? '/static/' : '/',
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_DJANGO_HOST ?? 'http://localhost:8000', changeOrigin: true },
      '/accounts': { target: process.env.VITE_DJANGO_HOST ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      },
    },
  },
})
