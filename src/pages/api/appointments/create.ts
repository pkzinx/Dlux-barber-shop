import type { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ detail: 'Method not allowed' })
  }
  const {
    barberId,
    barberName,
    clientName,
    clientPhone,
    serviceId,
    serviceTitle,
    startDatetime,
    endDatetime,
    notes,
  } = req.body || {}

  // Flexibiliza: aceita nomes/títulos, desde que haja dados suficientes para criar
  if ((!barberId && !barberName) || !clientName || !clientPhone || (!serviceId && !serviceTitle) || !startDatetime) {
    return res.status(400).json({ detail: 'Missing required fields' })
  }
  
  const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

  try {
    const resp = await fetch(`${BACKEND_URL}/api/appointments/public/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        barberId,
        barberName,
        clientName,
        clientPhone,
        serviceId,
        serviceTitle,
        startDatetime,
        endDatetime,
        notes,
      }),
    })
    const data = await resp.json()
    if (!resp.ok) {
      return res.status(resp.status).json(data)
    }
    return res.status(201).json(data)
  } catch (e: any) {
    return res.status(500).json({ detail: e?.message || 'Server error' })
  }
}