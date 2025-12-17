import type { NextApiRequest, NextApiResponse } from 'next'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ detail: 'Method not allowed' })
  }

  const { appointmentId, token } = req.body || {}
  if (!appointmentId || !token) {
    return res.status(400).json({ detail: 'Missing required fields: appointmentId, token' })
  }

  try {
    const url = `${BACKEND_URL}/api/appointments/${appointmentId}/subscribe/`
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    const data = await resp.json()
    return res.status(resp.status).json(data)
  } catch (e: any) {
    return res.status(500).json({ detail: e?.message || 'Server error' })
  }
}