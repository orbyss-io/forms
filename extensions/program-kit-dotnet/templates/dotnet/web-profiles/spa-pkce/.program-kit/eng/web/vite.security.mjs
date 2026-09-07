const baseline = Object.freeze({
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
  'X-Content-Type-Options': 'nosniff',
  'Cross-Origin-Opener-Policy': 'same-origin',
});

function exactOrigins(values, label) {
  return [...new Set(values ?? [])].map((value) => {
    const url = new URL(value);
    if (url.pathname !== '/' || url.search || url.hash || !['http:', 'https:'].includes(url.protocol)) {
      throw new Error(`${label} must contain exact HTTP(S) origins only: ${value}`);
    }
    return url.origin;
  }).sort();
}

export function programKitSpaSecurity({ apiOrigins = [], identityOrigins = [] } = {}) {
  const connectSources = [...exactOrigins(apiOrigins, 'apiOrigins'), ...exactOrigins(identityOrigins, 'identityOrigins')];
  const csp = [
    "default-src 'self'", "base-uri 'self'", "object-src 'none'", "frame-ancestors 'none'",
    "form-action 'self'", "script-src 'self'", "style-src 'self'", "img-src 'self' data:",
    "font-src 'self'", `connect-src 'self' ${connectSources.join(' ')}`.trim(),
  ].join('; ');
  const headers = Object.freeze({ ...baseline, 'Content-Security-Policy': csp });
  const middleware = (request, response, next) => {
    for (const [name, value] of Object.entries(headers)) response.setHeader(name, value);
    next();
  };
  return {
    name: 'program-kit-spa-serving-security',
    enforce: 'pre',
    configureServer(server) { server.middlewares.use(middleware); },
    configurePreviewServer(server) { server.middlewares.use(middleware); },
    programKitHeaders: headers,
  };
}
