import type { NextApiRequest, NextApiResponse } from 'next'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', ['GET'])
    return res.status(405).json({ detail: 'Method Not Allowed' })
  }

  try {
    const { date, barberId, barberName, serviceId, durationMinutes } = req.query

    const params = new URLSearchParams()
    if (typeof date === 'string') params.set('date', date)
    if (typeof barberId === 'string') params.set('barberId', barberId)
    if (typeof barberName === 'string') params.set('barberName', barberName)
    if (typeof serviceId === 'string') params.set('serviceId', serviceId)
    if (typeof durationMinutes === 'string') params.set('durationMinutes', durationMinutes)

    const url = `${BACKEND_URL}/api/appointments/available-slots/?${params.toString()}`
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } })
    const data = await r.json()
    return res.status(r.status).json(data)
  } catch (e: any) {
    return res.status(500).json({ detail: 'Proxy error', error: e?.message })
  }
}