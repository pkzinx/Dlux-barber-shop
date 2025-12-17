import type { NextApiRequest, NextApiResponse } from 'next'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ detail: 'Method not allowed' })
  }

  const { appointmentId, title, body, data } = req.body || {}
  if (!appointmentId) {
    return res.status(400).json({ detail: 'Missing required field: appointmentId' })
  }

  try {
    const url = `${BACKEND_URL}/api/appointments/${appointmentId}/notify_test/`
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, body, data }),
    })
    const json = await resp.json()
    return res.status(resp.status).json(json)
  } catch (e: any) {
    return res.status(500).json({ detail: e?.message || 'Server error' })
  }
}