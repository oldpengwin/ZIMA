import { waitUntil } from '@vercel/functions';
import { routeInteraction } from '../src/interactions/router.js';
import { verifyDiscordRequest } from '../src/interactions/verify.js';

export const config = {
  api: {
    bodyParser: false,
  },
};

async function readRawBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).send('Method not allowed');
  }

  const rawBody = await readRawBody(req);
  const signature = req.headers['x-signature-ed25519'];
  const timestamp = req.headers['x-signature-timestamp'];

  if (!verifyDiscordRequest(rawBody, signature, timestamp)) {
    return res.status(401).send('Invalid request signature');
  }

  let interaction;
  try {
    interaction = JSON.parse(rawBody.toString('utf8'));
  } catch {
    return res.status(400).send('Invalid JSON');
  }

  try {
    const { response, background } = await routeInteraction(interaction);

    res.status(200).json(response);

    if (background) {
      waitUntil(
        background.catch((err) => {
          console.error('Background interaction work failed:', err);
        }),
      );
    }
  } catch (err) {
    console.error('Interaction routing failed:', err);
    return res.status(500).json({
      type: 4,
      data: { content: 'Something went wrong. Please try again.', flags: 64 },
    });
  }
}
