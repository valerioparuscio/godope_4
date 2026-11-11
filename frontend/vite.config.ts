import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// The game is served at <site>/game/ (the deploy copies dist/ into the site repo's game/ folder).
const BASE = '/game/'
// The setup screen's own background; also the splash colour while the installed app starts.
const APP_COLOR = '#141414'

export default defineConfig({
  base: BASE,
  plugins: [
    react(),
    // Installable, full-screen app (docs/architecture/pwa.md). The service worker keeps only the app shell
    // (html/js/css/font) and, as they are used, the images; the backend (another origin) and the
    // music are never stored, so a game state is always read live.
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons/apple-touch-icon.png'],
      manifest: {
        id: BASE,
        name: 'DOPE',
        short_name: 'DOPE',
        description: 'Dope Boardgame',
        lang: 'it',
        start_url: BASE,
        scope: BASE,
        display: 'fullscreen',
        display_override: ['fullscreen', 'standalone'],
        // The board is wide (about 1.9:1): the game is meant to be played sideways.
        orientation: 'landscape',
        background_color: APP_COLOR,
        theme_color: APP_COLOR,
        categories: ['games'],
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icons/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Shell only: the hashed images (cards, boards, ...) and the ~50 MB of music stay out of the precache.
        globPatterns: ['**/*.{html,js,css,svg,ttf}'],
        navigateFallback: 'index.html',
        runtimeCaching: [
          {
            // Images are content-hashed, so once stored they never go stale. The API is on another
            // origin and is not matched by any rule here, so it always goes to the network.
            urlPattern: ({ sameOrigin, request }) => sameOrigin && request.destination === 'image',
            handler: 'CacheFirst',
            options: {
              cacheName: 'dope-images',
              expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
    }),
  ],
})
