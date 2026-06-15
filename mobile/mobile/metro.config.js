const http = require('http');
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

config.resolver.extraNodeModules = {
  assert: require.resolve('./assert-shim.js'),
};

// forward /api sang backend local port 3000
config.server = {
  ...config.server,
  enhanceMiddleware: (middleware) => {
    return (req, res, next) => {
      if (!req.url?.startsWith('/api')) {
        return middleware(req, res, next);
      }

      const proxyReq = http.request(
        {
          hostname: '127.0.0.1',
          port: 3000,
          path: req.url,
          method: req.method,
          headers: {
            ...req.headers,
            host: '127.0.0.1:3000',
          },
        },
        (proxyRes) => {
          res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
          proxyRes.pipe(res);
        },
      );

      proxyReq.on('error', (err) => {
        res.statusCode = 502;
        res.setHeader('Content-Type', 'text/plain');
        res.end(`Backend unavailable: ${err.message}`);
      });

      req.pipe(proxyReq);
    };
  },
};

module.exports = config;
