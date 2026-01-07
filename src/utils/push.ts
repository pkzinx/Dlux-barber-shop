import { initializeApp, getApps } from 'firebase/app'
import { getMessaging, getToken, onMessage, isSupported } from 'firebase/messaging'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || '',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || '',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || '',
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || '',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '',
}

function ensureFirebase() {
  if (typeof window === 'undefined') return null
  const apps = getApps()
  if (!apps.length) {
    return initializeApp(firebaseConfig)
  }
  return apps[0]
}

async function messagingSupported(): Promise<boolean> {
  try {
    if (typeof window === 'undefined') return false
    if (!('Notification' in window)) return false
    if (!('serviceWorker' in navigator)) return false
    // localhost over http is allowed; other http origins may fail
    const isSecure = window.location.protocol === 'https:' || window.location.hostname === 'localhost'
    if (!isSecure) return false
    // Require essential Firebase config values
    const required = [
      firebaseConfig.projectId,
      firebaseConfig.messagingSenderId,
      firebaseConfig.appId,
      firebaseConfig.apiKey,
    ]
    if (required.some((v) => !v || v.trim() === '')) return false
    return await isSupported()
  } catch {
    return false
  }
}

export async function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return null
  const reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js')
  // Post config so SW can init firebase compat
  reg?.active?.postMessage({ type: 'INIT_FIREBASE', config: firebaseConfig })
  return reg
}

export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (typeof window === 'undefined') return 'denied'
  if (!('Notification' in window)) return 'denied'
  const perm = await Notification.requestPermission()
  return perm
}

export async function getFcmToken(reg?: ServiceWorkerRegistration): Promise<string | null> {
  try {
    if (!(await messagingSupported())) return null
    ensureFirebase()
    const messaging = getMessaging()
    const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY
    const token = await getToken(messaging, { vapidKey, serviceWorkerRegistration: reg })
    return token || null
  } catch (e) {
    return null
  }
}

export function listenForegroundMessages(callback: (payload: any) => void) {
  try {
    // No need to await; if unsupported, just skip
    messagingSupported().then((supported) => {
      if (!supported) return
      ensureFirebase()
      const messaging = getMessaging()
      onMessage(messaging, (payload) => callback(payload))
    })
  } catch (e) {}
}

export async function registerAppointmentPush(appointmentId: string): Promise<boolean> {
  try {
    if (!(await messagingSupported())) return false
    const perm = await requestNotificationPermission()
    if (perm !== 'granted') return false
    const reg = await registerServiceWorker()
    const token = await getFcmToken(reg || undefined)
    if (!token) return false
    const resp = await fetch(`/api/appointments/${appointmentId}/subscribe/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ appointmentId, token }),
    })
    return resp.ok
  } catch (e) {
    return false
  }
}