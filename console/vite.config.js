import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API serves the built console at /console (python -m sentinel up). In development the dev server forwards
// the API paths to it, so there is no CORS and the browser only ever talks to one origin.
const API = process.env.SENTINEL_API || 'http://127.0.0.1:8000'
const apiPaths = ['/runs', '/scenarios', '/recordings', '/approvals', '/audit', '/killswitch', '/health']

export default defineConfig({
  base: '/console/',
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    fs: { allow: ['..'] }, // design/tokens.css lives one level up and is shared with the website
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
  },
  test: { environment: 'node', include: ['src/**/*.test.js'] },
})
