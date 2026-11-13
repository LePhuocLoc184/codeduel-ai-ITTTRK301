import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // public/src contains legacy app source and otherwise shadows /src/main.jsx.
  // This project currently has no static assets in public, so disable it as a public directory.
  publicDir: false,
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        ws: true,
      },
    },
  },
})
