import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.omni.app',
  appName: 'Omni Chat',
  webDir: '../dist',
  server: {
    androidScheme: 'https',
  },
}

export default config
