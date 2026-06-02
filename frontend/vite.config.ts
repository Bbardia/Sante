import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: "./", // relative paths so the built app loads under Electron's file:// protocol
  plugins: [react()],
})
