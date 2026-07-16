UNUSED — not part of the demo.

interactions.js was an early attempt at a serverless (Vercel HTTP-interactions)
version of Zima. It is broken and cannot run as-is: it imports
"@vercel/functions" (not installed) and ../src/interactions/router.js and
../src/interactions/verify.js (which do not exist).

The working demo is the GATEWAY bot in src/ (started with `npm run dev` or
`npm start`). This file is kept only for reference. Safe to delete.
