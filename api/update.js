// api/update.js
import fetch from 'node-fetch';

const OWNER  = process.env.OWNER;
const REPO   = process.env.REPO;
const BRANCH = process.env.BRANCH;
const TOKEN  = process.env.GITHUB_TOKEN;
const FILE   = 'Roster.txt';

export default async function handler(req, res) {
  if (req.method !== 'PUT') {
    res.setHeader('Allow','PUT');
    return res.status(405).json({ error:'Only PUT allowed' });
  }
  const { content, sha } = req.body;
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE}`;
  const payload = {
    message: `Web 更新 Roster.txt (${new Date().toISOString().slice(0,10)})`,
    content: Buffer.from(content,'utf8').toString('base64'),
    sha,
    branch: BRANCH
  };
  const gh = await fetch(url, {
    method: 'PUT',
    headers: {
      'Accept':'application/vnd.github.v3+json',
      'Authorization':`token ${TOKEN}`,
      'Content-Type':'application/json'
    },
    body: JSON.stringify(payload)
  });
  const j = await gh.json();
  if (!gh.ok) return res.status(gh.status).json(j);
  res.status(200).json(j);
}
