import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    // Fonts stay as files so the app's content security policy can allow them.
    assetsInlineLimit: 0,
    emptyOutDir: true
  }
})
