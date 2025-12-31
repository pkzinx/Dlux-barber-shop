
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method Not Allowed' });
  }

  const secret = req.headers['x-revalidate-secret'];

  if (secret !== process.env.REVALIDATE_SECRET_TOKEN) {
    return res.status(401).json({ message: 'Invalid token' });
  }

  const pathToRevalidate = req.body.path;

  if (!pathToRevalidate) {
    return res.status(400).json({ message: 'Path to revalidate is required' });
  }

  try {
    await res.revalidate(pathToRevalidate);
    return res.json({ revalidated: true });
  } catch (err) {
    return res.status(500).send('Error revalidating');
  }
}
