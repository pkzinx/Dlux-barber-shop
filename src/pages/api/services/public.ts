import type { NextApiRequest, NextApiResponse } from 'next'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET')
    return res.status(405).json({ detail: 'Method Not Allowed' })
  }

  try {
    const url = `${BACKEND_URL}/api/services/public/`
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } })
    if (!r.ok) {
        throw new Error(`Backend returned ${r.status}`)
    }
    const data = await r.json()
    res.setHeader('Cache-Control', 'no-store, max-age=0')
    return res.status(200).json(data)
  } catch (e: any) {
    console.error('API Proxy Error:', e)
    return res.status(500).json({ detail: 'Proxy error', error: e?.message })
  }
}
