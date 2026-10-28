import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API serves the built site at / (python -m sentinel up). In development the dev server forwards the API paths to
// it, so there is no CORS and the browser only ever talks to one origin. Mock data is used by default in development
// (see src/api/client.js), so the backend does not have to run while you build pages.
const API = process.env.SENTINEL_API || 'http://127.0.0.1:8000'
const apiPaths = ['/api', '/runs', '/scenarios', '/recordings', '/approvals', '/audit', '/health', '/console']

export default defineConfig({
  base: '/',
  plugins: [react()],
  test: { environment: 'node', include: ['src/**/*.test.js'] },
  // `vite preview` of a production build forwards the API the same way, so a built site can be checked against a real gateway.
  preview: { proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])) },
  server: {
    port: 5174,
    strictPort: true,
    fs: { allow: ['..'] }, // design/tokens.css lives one level up and is shared with the console
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
  },
})
