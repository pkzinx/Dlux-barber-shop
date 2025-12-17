// Firebase Messaging Service Worker
// Uses compat build for simplicity
importScripts('https://www.gstatic.com/firebasejs/9.6.10/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/9.6.10/firebase-messaging-compat.js')

// These values should match NEXT_PUBLIC_FIREBASE_* envs in the client
// The service worker cannot read env vars; they are bundled as literals below if needed.
// For development, you can inline config here, but prefer client-provided initialization.

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'INIT_FIREBASE') {
    try {
      firebase.initializeApp(event.data.config)
      firebase.messaging()
    } catch (e) {
      // Already initialized or failed; ignore
    }
  }
})

try {
  // Attempt to initialize with default values to avoid errors if client forgets to post config
  // You can remove this if you always post INIT_FIREBASE from the page.
  // eslint-disable-next-line no-undef
  if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    // No-op until the page posts the config
  }
} catch (e) {}

// Background messages
try {
  const messaging = firebase.messaging()
  messaging.onBackgroundMessage((payload) => {
    const title = payload.notification?.title || 'Mensagem'
    const body = payload.notification?.body || ''
    const options = {
      body,
      data: payload.data || {},
      icon: '/128.jpg',
      badge: '/128.jpg',
    }
    self.registration.showNotification(title, options)
  })
} catch (e) {
  // ignore
}

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = '/'
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) return client.focus()
      }
      if (clients.openWindow) return clients.openWindow(url)
    })
  )
})