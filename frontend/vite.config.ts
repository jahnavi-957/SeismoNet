import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
    fs: {
      strict: true,
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        // Split the three largest dependency families into their own chunks so no
        // single asset exceeds Vite's 500 kB advisory threshold. No catch-all bucket
        // is used: an "everything else" vendor chunk creates circular chunks with
        // recharts' own dependencies.
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return undefined
          if (/[\\/]node_modules[\\/](react|react-dom|scheduler|react-is)[\\/]/.test(id)) return 'react'
          if (/[\\/]node_modules[\\/](d3-[a-z-]+|internmap|victory-vendor|decimal\.js-light|fast-equals)[\\/]/.test(id)) return 'charts-d3'
          if (/[\\/]node_modules[\\/]recharts[\\/]/.test(id)) return 'charts-recharts'
          return undefined
        }
      }
    }
  }
})
