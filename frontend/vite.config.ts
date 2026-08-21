import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: "./", // relative paths so the built app loads under Electron's file:// protocol
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: false, // tests import { describe, it, expect, vi } explicitly
    setupFiles: './src/test/setup.ts',
    css: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    restoreMocks: true,
  },
})
