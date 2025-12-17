import type { NextApiRequest, NextApiResponse } from 'next'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ detail: 'Method not allowed' })
  }

  const { id, appointmentId } = req.body || {}
  const apptId = id || appointmentId
  if (!apptId) {
    return res.status(400).json({ detail: 'Missing required field: id' })
  }

  try {
    const resp = await fetch(`${BACKEND_URL}/api/appointments/cancel/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: apptId }),
    })
    const data = await resp.json()
    return res.status(resp.status).json(data)
  } catch (e: any) {
    return res.status(500).json({ detail: e?.message || 'Server error' })
  }
}