// api/roster.js
import fetch from 'node-fetch';

const OWNER  = process.env.OWNER;
const REPO   = process.env.REPO;
const BRANCH = process.env.BRANCH;
const TOKEN  = process.env.GITHUB_TOKEN;

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    res.status(405).json({ error: 'Method Not Allowed' });
    return;
  }

  const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/roster.txt?ref=${BRANCH}`;
  const ghRes = await fetch(url, {
    headers: {
      'Accept': 'application/vnd.github.v3+json',
      'Authorization': `token ${TOKEN}`
    }
  });
  if (!ghRes.ok) {
    const err = await ghRes.json();
    res.status(ghRes.status).json(err);
    return;
  }
  const data = await ghRes.json();
  const text = Buffer.from(data.content, 'base64').toString('utf8');

  res.status(200).json({
    text,
    sha: data.sha
  });
}
