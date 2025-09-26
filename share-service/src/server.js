const path = require('path');
const fs = require('fs');
const fsp = require('fs/promises');
const express = require('express');
const dotenv = require('dotenv');
const { Resvg } = require('@resvg/resvg-js');
const { nanoid } = require('nanoid');
const { z } = require('zod');

const { buildCardSvg } = require('./card-template');

dotenv.config({ path: path.resolve(__dirname, '..', '..', '.env') });

const app = express();
app.use(express.json({ limit: '1mb' }));

const CACHE_ROOT = path.resolve(__dirname, '..', 'cache');
const CARD_DIR = path.join(CACHE_ROOT, 'cards');
const META_DIR = path.join(CACHE_ROOT, 'meta');

for (const dir of [CACHE_ROOT, CARD_DIR, META_DIR]) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

const PORT = parseInt(process.env.SHARE_SERVICE_PORT || '4076', 10);
const PUBLIC_URL = (process.env.SHARE_PUBLIC_URL || '').replace(/\/$/, '');
const APP_URL = (process.env.PUBLIC_APP_URL || process.env.BASE_URL || '').replace(/\/$/, '');
const BRAND_NAME = process.env.SHARE_BRAND_NAME || 'Sea Mom Flex';
const TAG_LINE = process.env.SHARE_TAG_LINE || '“See, mom? I told you those 2021 NFT flips would pay off.”';

const escapeHtml = (value = '') =>
  String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const shareRequestSchema = z.object({
  wallet: z.string().min(1).max(128),
  payoutUsd: z.number().nonnegative(),
  payoutTokens: z.number().nonnegative(),
  tokenPrice: z.number().nonnegative(),
  cohortLabel: z.string().min(1).max(128),
  cohortWallets: z.number().nonnegative().optional(),
  percentileLabel: z.string().min(1).max(128),
  sharePct: z.number().nonnegative(),
  fdvBillion: z.number().nonnegative(),
  ogPoolPct: z.number().nonnegative(),
  tradeCount: z.number().nonnegative().optional(),
  totalEth: z.number().nonnegative().optional(),
  totalUsd: z.number().nonnegative().optional(),
  asOf: z.string().optional(),
});

const metaFileFor = (id) => path.join(META_DIR, `${id}.json`);
const cardFileFor = (id) => path.join(CARD_DIR, `${id}.png`);

const buildPublicPath = (segment) => {
  const safeSegment = segment.startsWith('/') ? segment : `/${segment}`;
  return PUBLIC_URL ? `${PUBLIC_URL}${safeSegment}` : safeSegment;
};

app.get('/healthz', (_req, res) => {
  res.json({ status: 'ok' });
});

app.use('/cards', express.static(CARD_DIR, {
  maxAge: '2h',
  setHeaders: (res) => {
    res.setHeader('Cache-Control', 'public, max-age=7200, immutable');
  },
}));

async function renderCardAssets({ shareId, payload, createdAt }) {
  const renderTimestamp = new Date().toISOString();
  const svg = buildCardSvg({
    ...payload,
    brandName: BRAND_NAME,
    tagLine: TAG_LINE,
  });

  const renderer = new Resvg(svg, {
    fitTo: { mode: 'width', value: 1200 },
    font: { loadSystemFonts: true },
    background: '#0f172a',
  });

  const pngData = renderer.render().asPng();
  await fsp.writeFile(cardFileFor(shareId), pngData);

  const metadata = {
    id: shareId,
    createdAt: createdAt || renderTimestamp,
    updatedAt: renderTimestamp,
    payload,
    imagePath: `/cards/${shareId}.png`,
    brandName: BRAND_NAME,
    tagLine: TAG_LINE,
  };

  await fsp.writeFile(metaFileFor(shareId), JSON.stringify(metadata, null, 2), 'utf-8');
  return metadata;
}

app.post('/cards', async (req, res) => {
  const parseResult = shareRequestSchema.safeParse(req.body);
  if (!parseResult.success) {
    res.status(400).json({ error: 'Invalid payload', details: parseResult.error.flatten() });
    return;
  }

  const payload = parseResult.data;
  const shareId = nanoid(10);

  try {
    const metadata = await renderCardAssets({ shareId, payload });

    res.status(201).json({
      id: shareId,
      created_at: metadata.createdAt,
      updated_at: metadata.updatedAt,
      image_url: buildPublicPath(metadata.imagePath),
      share_url: buildPublicPath(`/share/${shareId}`),
      meta_url: buildPublicPath(`/cards/${shareId}.json`),
    });
  } catch (err) {
    console.error('Failed to generate share card', err);
    res.status(500).json({ error: 'Failed to render share card' });
  }
});

app.get('/cards/:id.json', async (req, res) => {
  const { id } = req.params;
  try {
    const raw = await fsp.readFile(metaFileFor(id), 'utf-8');
    const metadata = JSON.parse(raw);
    res.json(metadata);
  } catch (err) {
    res.status(404).json({ error: 'Share card not found' });
  }
});

app.post('/cards/:id/regenerate', async (req, res) => {
  const { id } = req.params;

  try {
    const raw = await fsp.readFile(metaFileFor(id), 'utf-8');
    const existing = JSON.parse(raw);
    if (!existing || !existing.payload) {
      res.status(400).json({ error: 'Existing card payload not found' });
      return;
    }

    const metadata = await renderCardAssets({
      shareId: id,
      payload: existing.payload,
      createdAt: existing.createdAt,
    });

    res.json({
      id,
      created_at: metadata.createdAt,
      updated_at: metadata.updatedAt,
      image_url: buildPublicPath(metadata.imagePath),
      share_url: buildPublicPath(`/share/${id}`),
      meta_url: buildPublicPath(`/cards/${id}.json`),
    });
  } catch (err) {
    if (err.code === 'ENOENT') {
      res.status(404).json({ error: 'Share card not found' });
      return;
    }
    console.error('Failed to regenerate share card', err);
    res.status(500).json({ error: 'Failed to regenerate share card' });
  }
});

app.get('/share/:id', async (req, res) => {
  const { id } = req.params;
  try {
    const raw = await fsp.readFile(metaFileFor(id), 'utf-8');
    const metadata = JSON.parse(raw);
    const imageUrl = buildPublicPath(`/cards/${id}.png`);
    const imageUrlEsc = escapeHtml(imageUrl);
    const titleRaw = `${metadata.brandName || BRAND_NAME} · ${metadata.payload ? metadata.payload.percentileLabel : 'Airdrop estimate'}`;
    const descriptionParts = [];
    if (metadata.payload?.payoutUsd) {
      descriptionParts.push(`Projected payout ${metadata.payload.payoutUsd.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: metadata.payload.payoutUsd >= 1000 ? 0 : 2 })}`);
    }
    if (metadata.payload?.cohortLabel) {
      descriptionParts.push(metadata.payload.cohortLabel);
    }
    const descriptionRaw = descriptionParts.join(' · ') || metadata.tagLine || TAG_LINE;
    const title = escapeHtml(titleRaw);
    const description = escapeHtml(descriptionRaw);

    const appUrlHref = APP_URL || '/';
    const appUrlHrefEsc = escapeHtml(appUrlHref);
    const appUrlLabel = APP_URL
      ? escapeHtml(APP_URL.replace(/^https?:\/\//i, ''))
      : 'Sea Mom Estimator';

    const payloadJson = escapeHtml(JSON.stringify(metadata.payload || {}, null, 2));
    const metadataJson = escapeHtml(JSON.stringify(metadata, null, 2));
    const lastRendered = escapeHtml(metadata.updatedAt || metadata.createdAt || 'unknown');

    res.set('Content-Type', 'text/html');
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>${title}</title>
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="${title}" />
  <meta name="twitter:description" content="${description}" />
  <meta name="twitter:image" content="${imageUrlEsc}" />
  <meta property="og:title" content="${title}" />
  <meta property="og:description" content="${description}" />
  <meta property="og:image" content="${imageUrlEsc}" />
  <meta property="og:type" content="website" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: 'Inter', 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; padding:2rem; }
    .wrapper { text-align:center; max-width: 960px; width: 100%; }
    img { width: min(90vw, 960px); border-radius: 24px; box-shadow: 0 20px 40px rgba(15, 23, 42, 0.6); }
    .cta { margin-top: 1.2rem; font-size: 1rem; color: #93c5fd; }
    a { color: #60a5fa; text-decoration:none; }
    .actions { margin-top: 1.5rem; display:flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
    button { background: #2563eb; color: #f8fafc; border: none; border-radius: 999px; padding: 0.6rem 1.4rem; font-size: 0.95rem; font-weight: 600; cursor: pointer; box-shadow: 0 10px 30px rgba(37, 99, 235, 0.25); transition: transform 0.15s ease, box-shadow 0.15s ease; }
    button:hover { transform: translateY(-1px); box-shadow: 0 12px 34px rgba(37, 99, 235, 0.3); }
    button:disabled { opacity: 0.6; cursor: not-allowed; box-shadow: none; }
    .status { margin-top: 0.75rem; font-size: 0.9rem; color: #bfdbfe; }
    details { margin-top: 2rem; text-align: left; background: rgba(15, 23, 42, 0.75); border-radius: 16px; padding: 1.2rem; }
    details > summary { cursor: pointer; font-weight: 600; color: #93c5fd; }
    pre { white-space: pre-wrap; word-break: break-word; font-size: 0.85rem; line-height: 1.45; color: #e2e8f0; }
  </style>
</head>
<body>
  <div class="wrapper">
    <img src="${imageUrlEsc}" alt="${title}" loading="lazy" id="share-image" />
    <div class="status" id="render-info">Last rendered at ${lastRendered}</div>
    <div class="actions">
      <button id="regen-btn">Regenerate image</button>
    </div>
    <div class="status" id="regen-status"></div>
    <div class="cta">View live assumptions at <a href="${appUrlHrefEsc}">${appUrlLabel}</a></div>
    <details>
      <summary>Debug payload</summary>
      <pre>${payloadJson}</pre>
    </details>
    <details>
      <summary>Debug metadata</summary>
      <pre>${metadataJson}</pre>
    </details>
  </div>
  <script>
    const regenBtn = document.getElementById('regen-btn');
    const statusEl = document.getElementById('regen-status');
    const renderInfo = document.getElementById('render-info');
    const imageEl = document.getElementById('share-image');
    const imageUrl = '${imageUrlEsc}';
    regenBtn?.addEventListener('click', async () => {
      if (!regenBtn) return;
      regenBtn.disabled = true;
      statusEl.textContent = 'Regenerating…';
      try {
        const resp = await fetch('/cards/${id}/regenerate', { method: 'POST' });
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || 'Failed to regenerate');
        }
        const data = await resp.json();
        const freshUrl = (data.image_url || imageUrl) + '?t=' + Date.now();
        imageEl.src = freshUrl;
        statusEl.textContent = 'Regenerated successfully.';
        if (data.updated_at) {
          renderInfo.textContent = 'Last rendered at ' + data.updated_at;
        }
      } catch (err) {
        console.error(err);
        statusEl.textContent = 'Regeneration failed: ' + (err.message || err);
      } finally {
        regenBtn.disabled = false;
      }
    });
  </script>
</body>
</html>`);
  } catch (err) {
    res.status(404).send('Share card not found');
  }
});

app.listen(PORT, () => {
  console.log(`Sea Mom share service listening on port ${PORT}`);
});
