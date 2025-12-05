// api/update.js
import fetch from 'node-fetch';

const OWNER  = process.env.OWNER;
const REPO   = process.env.REPO;
const BRANCH = process.env.BRANCH;
const TOKEN  = process.env.GITHUB_TOKEN;

export default async function handler(req, res) {
  if (req.method !== 'PUT') {
    res.setHeader('Allow', 'PUT');
    res.status(405).json({ error: 'Method Not Allowed' });
    return;
  }

  const { content, sha } = req.body;  // 前端傳來的純文字 + sha
  const apiUrl = `https://api.github.com/repos/${OWNER}/${REPO}/contents/roster.txt`;

  const payload = {
    message: `Web 更新排班 ${new Date().toISOString().slice(0,10)}`,
    content: Buffer.from(content, 'utf8').toString('base64'),
    sha,
    branch: BRANCH
  };

  const ghRes = await fetch(apiUrl, {
    method: 'PUT',
    headers: {
      'Accept': 'application/vnd.github.v3+json',
      'Authorization': `token ${TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  const data = await ghRes.json();
  if (!ghRes.ok) {
    res.status(ghRes.status).json(data);
    return;
  }
  res.status(200).json(data);
}
