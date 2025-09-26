const path = require('path');

const ROOT_DIR = __dirname;
const SHARE_PORT = process.env.SHARE_SERVICE_PORT || '4076';
const SHARE_PUBLIC_URL = process.env.SHARE_PUBLIC_URL || process.env.BASE_URL || '';
const PUBLIC_APP_URL = process.env.PUBLIC_APP_URL || process.env.BASE_URL || '';

module.exports = {
  apps: [
    {
      name: 'sea-mom',
      cwd: ROOT_DIR,
      script: path.join(ROOT_DIR, '.venv', 'bin', 'python'),
      args: '-m streamlit run sea_airdrop_dashboard.py --server.address 0.0.0.0 --server.port 4075',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production',
        SHARE_SERVICE_URL: process.env.SHARE_SERVICE_URL || `http://127.0.0.1:${SHARE_PORT}`,
        SHARE_PUBLIC_BASE: process.env.SHARE_PUBLIC_BASE || SHARE_PUBLIC_URL,
      },
    },
    {
      name: 'sea-mom-share',
      cwd: path.join(ROOT_DIR, 'share-service'),
      script: 'npm',
      args: 'run start',
      autorestart: true,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production',
        SHARE_SERVICE_PORT: SHARE_PORT,
        SHARE_PUBLIC_URL,
        PUBLIC_APP_URL,
      },
    },
  ],
};
