const path = require('path');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '..', '.env') });

module.exports = {
  apps: [
    {
      name: 'sea-mom-share',
      script: 'npm',
      args: 'run start',
      cwd: __dirname,
      autorestart: true,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production',
        SHARE_SERVICE_PORT: process.env.SHARE_SERVICE_PORT || '4076',
      },
      env_development: {
        NODE_ENV: 'development',
        SHARE_SERVICE_PORT: process.env.SHARE_SERVICE_PORT || '4076',
      },
    },
  ],
};
