const fs = require('fs');
const path = require('path');

let cachedLogoDataUri;

const getLogoDataUri = () => {
  if (cachedLogoDataUri !== undefined) {
    return cachedLogoDataUri;
  }
  try {
    const logoPath = path.resolve(__dirname, '..', '..', 'assets', 'opensea_logomark.png');
    const file = fs.readFileSync(logoPath);
    cachedLogoDataUri = `data:image/png;base64,${file.toString('base64')}`;
  } catch (err) {
    cachedLogoDataUri = null;
  }
  return cachedLogoDataUri;
};

const escapeHtml = (value = '') =>
  String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const formatCurrency = (value) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value);

const formatNumber = (value, { maximumFractionDigits = 1 } = {}) =>
  new Intl.NumberFormat('en-US', {
    maximumFractionDigits,
  }).format(value);

const formatPercent = (value) => `${Number(value).toFixed(1).replace(/\.0$/, '')}%`;

const maskWallet = (wallet) => {
  if (!wallet) return 'n/a';
  const lower = wallet.toLowerCase();
  return lower.slice(0, 6) + '…' + lower.slice(-4);
};

function buildCardSvg(payload) {
  const {
    wallet,
    payoutUsd,
    payoutTokens,
    tokenPrice,
    cohortLabel,
    cohortWallets,
    percentileLabel,
    sharePct,
    fdvBillion,
    ogPoolPct,
    tradeCount,
    totalEth,
    totalUsd,
    tagLine,
    brandName,
    asOf,
  } = payload;

  const maskedWallet = maskWallet(wallet);
  const payoutUsdFmt = formatCurrency(payoutUsd);
  const payoutTokensFmt = `${formatNumber(payoutTokens, { maximumFractionDigits: payoutTokens >= 100 ? 0 : 2 })} SEA`;
  const tokenPriceFmt = `${formatCurrency(tokenPrice)} per SEA`;
  const tradeCountFmt = `${formatNumber(tradeCount, { maximumFractionDigits: 0 })} trades`;
  const totalEthFmt = `${formatNumber(totalEth, { maximumFractionDigits: 2 })} ETH volume`;
  const totalUsdFmt = `${formatCurrency(totalUsd)}`;
  const cohortWalletsFmt = cohortWallets ? `${formatNumber(cohortWallets, { maximumFractionDigits: 0 })} wallets` : '';
  const sharePctFmt = formatPercent(sharePct);
  const ogPoolFmt = formatPercent(ogPoolPct);
  const fdvFmt = `${formatNumber(fdvBillion, { maximumFractionDigits: 1 })}B FDV`;
  const headline = escapeHtml(brandName || 'Sea Mom Flex');
  const tagLineText = escapeHtml(tagLine || '“See, mom? I told you those 2021 NFT flips would pay off.”');
  const cohortLine = escapeHtml([cohortLabel, cohortWalletsFmt].filter(Boolean).join(' • '));
  const tierLine = escapeHtml(
    [percentileLabel, `${sharePctFmt} of OG pool`, `${ogPoolFmt} OG allocation`].filter(Boolean).join('  •  ')
  );
  const metricsLine = escapeHtml([tradeCountFmt, totalEthFmt].filter(Boolean).join('  •  '));
  const footerLine = escapeHtml(`${fdvFmt}  •  Token price ${tokenPriceFmt}`);
  const asOfLine = asOf ? `As of ${escapeHtml(asOf)}` : '';
  const logoUri = getLogoDataUri();

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 1200 630" width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f1a3a" />
      <stop offset="50%" stop-color="#182d5c" />
      <stop offset="100%" stop-color="#0c2647" />
    </linearGradient>
    <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.4" />
      <stop offset="50%" stop-color="#60a5fa" stop-opacity="0.7" />
      <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.4" />
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#0a162f" flood-opacity="0.8" />
    </filter>
  </defs>
  <rect width="1200" height="630" fill="url(#bgGradient)" rx="32" />

  <g transform="translate(70, 80)">
    <text x="0" y="0" fill="#93c5fd" font-family="'Inter', 'Segoe UI', sans-serif" font-size="32" font-weight="600">
      ${headline}
    </text>
    <text x="0" y="48" fill="#bfdbfe" font-family="'Inter', 'Segoe UI', sans-serif" font-size="22" font-weight="400">
      ${tagLineText}
    </text>
    ${logoUri ? `<image href="${logoUri}" x="920" y="-30" width="60" height="60" />` : ''}
  </g>

  <g transform="translate(70, 160)">
    <rect width="1060" height="280" rx="28" fill="rgba(15, 23, 42, 0.55)" filter="url(#shadow)" />
    <rect x="20" y="20" width="1020" height="100" rx="20" fill="rgba(30, 58, 138, 0.45)" stroke="url(#glow)" stroke-width="2" />
    <text x="50" y="87" fill="#dbeafe" font-family="'Inter', 'Segoe UI', sans-serif" font-size="26" font-weight="500">Wallet ${maskedWallet}</text>

    <text x="60" y="205" fill="#f8fafc" font-family="'Inter', 'Segoe UI', sans-serif" font-size="120" font-weight="700">
      ${payoutUsdFmt}
    </text>
    <text x="65" y="250" fill="#cbd5f5" font-family="'Inter', 'Segoe UI', sans-serif" font-size="28" font-weight="500">
      ≈ ${payoutTokensFmt} @ ${tokenPriceFmt}
    </text>

    <g transform="translate(650, 190)">
      <rect width="350" height="120" rx="24" fill="rgba(15, 23, 42, 0.8)" stroke="rgba(96, 165, 250, 0.35)" stroke-width="1.5" />
      <text x="30" y="55" fill="#e2e8f0" font-family="'Inter', 'Segoe UI', sans-serif" font-size="30" font-weight="600">${cohortLine}</text>
      <text x="30" y="92" fill="#cbd5f5" font-family="'Inter', 'Segoe UI', sans-serif" font-size="22" font-weight="500">${tierLine}</text>
    </g>
  </g>

  <g transform="translate(70, 470)">
    <rect width="1060" height="110" rx="24" fill="rgba(15, 23, 42, 0.75)" />
    <text x="40" y="55" fill="#bfdbfe" font-family="'Inter', 'Segoe UI', sans-serif" font-size="26" font-weight="500">${metricsLine}</text>
    <text x="40" y="95" fill="#93c5fd" font-family="'Inter', 'Segoe UI', sans-serif" font-size="22" font-weight="400">${totalUsdFmt}${asOfLine ? ' · ' + asOfLine : ''}</text>
    <text x="650" y="55" fill="#bfdbfe" font-family="'Inter', 'Segoe UI', sans-serif" font-size="26" font-weight="500" text-anchor="start">${footerLine}</text>
  </g>
</svg>`;
}

module.exports = {
  buildCardSvg,
};
