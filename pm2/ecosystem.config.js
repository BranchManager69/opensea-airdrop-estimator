const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const SHARE_PORT = process.env.SHARE_SERVICE_PORT || '4076';

module.exports = {
  apps: [
    {
      name: 'opensea',
      cwd: ROOT_DIR,
      script: path.join(ROOT_DIR, '.venv', 'bin', 'python'),
      args: '-m streamlit run sea_airdrop_dashboard.py --server.address 0.0.0.0 --server.port 4075',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production',
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
      },
    },
  ],
};
