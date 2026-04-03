import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.omini.app',
  appName: 'Omni Chat',
  webDir: '../dist',
  server: {
    androidScheme: 'https',
  },
}

export default config
