import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'

// 读取 config.json 获取后端端口
let backendPort = 8000
try {
  const config = JSON.parse(fs.readFileSync('../config.json', 'utf-8'))
  if (config.port) backendPort = config.port
} catch {}
if (process.env.DESKTOP_MODE === 'true') backendPort = 8077

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
})
