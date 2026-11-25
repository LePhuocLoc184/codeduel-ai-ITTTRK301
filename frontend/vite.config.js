import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'

const faviconSvg = readFileSync(new URL('./public/favicon.svg', import.meta.url))

export default defineConfig({
  // public/src contains legacy app source, so expose the favicon explicitly instead.
  publicDir: false,
  plugins: [
    react(),
    {
      name: 'codeduel-favicon',
      configureServer(server) {
        server.middlewares.use('/favicon.svg', (request, response, next) => {
          if (request.method !== 'GET' && request.method !== 'HEAD') return next()
          response.setHeader('Content-Type', 'image/svg+xml')
          if (request.method === 'HEAD') return response.end()
          response.end(faviconSvg)
        })
      },
      generateBundle() {
        this.emitFile({ type: 'asset', fileName: 'favicon.svg', source: faviconSvg })
      },
    },
  ],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        ws: true,
      },
    },
  },
})
