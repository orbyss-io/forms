import { createHash, generateKeyPairSync, randomUUID, sign } from 'node:crypto';

const endpoint = process.env.PROGRAM_KIT_DPOP_TOKEN_ENDPOINT;
if (!endpoint) throw new Error('PROGRAM_KIT_DPOP_TOKEN_ENDPOINT is required.');

const encode = value => Buffer.from(value).toString('base64url');
const decode = token => JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'));

function keyMaterial() {
  const { privateKey, publicKey } = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  const exported = publicKey.export({ format: 'jwk' });
  const jwk = { kty: 'EC', crv: 'P-256', x: exported.x, y: exported.y };
  const canonical = JSON.stringify({ crv: jwk.crv, kty: jwk.kty, x: jwk.x, y: jwk.y });
  const thumbprint = createHash('sha256').update(canonical).digest('base64url');
  return { privateKey, jwk, thumbprint };
}

function proof(material, accessToken) {
  const header = encode(JSON.stringify({ typ: 'dpop+jwt', alg: 'ES256', jwk: material.jwk }));
  const payload = {
    jti: randomUUID(),
    htm: 'POST',
    htu: endpoint,
    iat: Math.floor(Date.now() / 1000),
  };
  if (accessToken) payload.ath = createHash('sha256').update(accessToken, 'ascii').digest('base64url');
  const encodedPayload = encode(JSON.stringify(payload));
  const signature = sign('sha256', Buffer.from(`${header}.${encodedPayload}`, 'ascii'), {
    key: material.privateKey,
    dsaEncoding: 'ieee-p1363',
  }).toString('base64url');
  return `${header}.${encodedPayload}.${signature}`;
}

async function request(form, dpop) {
  const headers = {
    Authorization: `Basic ${Buffer.from('program-kit-dpop-machine:local-dpop-machine-secret').toString('base64')}`,
    'Content-Type': 'application/x-www-form-urlencoded',
  };
  if (dpop) headers.DPoP = dpop;
  const response = await fetch(endpoint, { method: 'POST', headers, body: new URLSearchParams(form) });
  const text = await response.text();
  return { status: response.status, body: text ? JSON.parse(text) : {} };
}

const missing = await request({ grant_type: 'client_credentials', scope: 'program-kit-context' });
if (missing.status < 400) throw new Error(`DPoP-required client accepted no proof: ${JSON.stringify(missing)}`);

const material = keyMaterial();
const acquisitionProof = proof(material);
const issued = await request(
  { grant_type: 'client_credentials', scope: 'program-kit-context' },
  acquisitionProof,
);
if (issued.status !== 200 || issued.body.token_type?.toLowerCase() !== 'dpop') {
  throw new Error(`DPoP client credentials failed: ${JSON.stringify(issued)}`);
}
const claims = decode(issued.body.access_token);
if (claims.cnf?.jkt !== material.thumbprint
    || claims.tenant_id !== 'dpop-machine-fixture'
    || !claims.roles?.includes('user')) {
  throw new Error(`DPoP access token binding/claims mismatch: ${JSON.stringify(claims)}`);
}

const replay = await request(
  { grant_type: 'client_credentials', scope: 'program-kit-context' },
  acquisitionProof,
);
if (replay.status < 400) throw new Error(`Token endpoint accepted a replayed DPoP proof: ${JSON.stringify(replay)}`);

const exchanged = await request(
  {
    grant_type: 'urn:ietf:params:oauth:grant-type:token-exchange',
    subject_token: issued.body.access_token,
    subject_token_type: 'urn:ietf:params:oauth:token-type:access_token',
    requested_token_type: 'urn:ietf:params:oauth:token-type:access_token',
    audience: 'program-kit-api',
    scope: 'program-kit-context',
  },
  proof(material, issued.body.access_token),
);
if (exchanged.status !== 200 || exchanged.body.token_type?.toLowerCase() !== 'dpop') {
  throw new Error(`DPoP token exchange failed: ${JSON.stringify(exchanged)}`);
}
const exchangedClaims = decode(exchanged.body.access_token);
if (exchangedClaims.cnf?.jkt !== material.thumbprint
    || exchangedClaims.sub !== claims.sub
    || exchangedClaims.aud !== 'program-kit-api') {
  throw new Error(`Exchanged DPoP token lost binding, subject, or audience: ${JSON.stringify(exchangedClaims)}`);
}

const attacker = keyMaterial();
const wrongKey = await request(
  {
    grant_type: 'urn:ietf:params:oauth:grant-type:token-exchange',
    subject_token: issued.body.access_token,
    subject_token_type: 'urn:ietf:params:oauth:token-type:access_token',
    audience: 'program-kit-api',
  },
  proof(attacker, issued.body.access_token),
);
if (wrongKey.status < 400) throw new Error(`DPoP exchange accepted the wrong private key: ${JSON.stringify(wrongKey)}`);

console.log('Keycloak issued, exchanged, and protected replay of RFC 9449-bound tokens.');
