// api/roster.js
import fetch from 'node-fetch';

const OWNER  = process.env.OWNER;
const REPO   = process.env.REPO;
const BRANCH = process.env.BRANCH;
const TOKEN  = process.env.GITHUB_TOKEN;
const FILE   = 'Roster.txt';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow','GET');
    return res.status(405).json({ error:'Only GET allowed' });
  }
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE}?ref=${BRANCH}`;
  const gh = await fetch(url, {
    headers: {
      'Accept':'application/vnd.github.v3+json',
      'Authorization':`token ${TOKEN}`
    }
  });
  if (!gh.ok) {
    const e = await gh.json();
    return res.status(gh.status).json(e);
  }
  const j = await gh.json();
  const text = Buffer.from(j.content,'base64').toString('utf8');
  res.status(200).json({ text, sha: j.sha });
}
