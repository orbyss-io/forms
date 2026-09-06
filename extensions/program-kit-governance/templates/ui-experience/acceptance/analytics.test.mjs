import assert from 'node:assert/strict';
import test from 'node:test';
import { createAnalytics, createGa4Adapter } from '../../public/assets/analytics.mjs';

test('no calls before consent; navigation deduplicates; revocation stops subsequent sends', () => {
  const sent = [], lifecycle = [];
  const analytics = createAnalytics({ pages: ['home', 'guide'], events: ['purchase_started'], adapter: {
    activate: () => lifecycle.push('activate'), deactivate: () => lifecycle.push('deactivate'), send: event => sent.push(event)
  } });
  analytics.navigate('home', 'navigation-with-private-local-state');
  analytics.event('purchase_started');
  assert.deepEqual(sent, []); assert.deepEqual(lifecycle, []);
  analytics.setConsent(true); analytics.setConsent(true);
  analytics.navigate('home', 'navigation-with-private-local-state');
  assert.deepEqual(sent, [{ type: 'page_view', page_id: 'home' }]);
  analytics.navigate('guide', 'second'); analytics.event('purchase_started');
  analytics.setConsent(false); analytics.navigate('home', 'third'); analytics.event('purchase_started');
  assert.equal(sent.length, 3); assert.deepEqual(lifecycle, ['activate', 'deactivate']);
  analytics.setConsent(true);
  assert.equal(sent.length, 4);
  assert(!JSON.stringify(sent).includes('private-local-state'));
});

test('unknown identifiers, arbitrary payloads and nonboolean consent cannot leak into events', () => {
  const sent = [];
  const analytics = createAnalytics({ pages: ['home'], events: ['save'], adapter: { send: event => sent.push(event) } });
  analytics.setConsent(true);
  assert.throws(() => analytics.navigate('/account?email=secret', 'x'));
  assert.throws(() => analytics.event({ email: 'secret' }));
  assert.throws(() => analytics.setConsent('true'));
  assert.throws(() => createAnalytics({ pages: ['email@secret'] }));
  assert.deepEqual(sent, []);
});

test('GA4 transport is activated only after consent and disables automatic page views', () => {
  const calls = [];
  const adapter = createGa4Adapter({ measurementId: 'G-TEST', activateTransport: () => {
    calls.push(['activate']); return (...args) => calls.push(args);
  }, deactivateTransport: () => calls.push(['deactivate']) });
  const analytics = createAnalytics({ pages: ['home'], adapter });
  analytics.navigate('home', 'first'); assert.equal(calls.length, 0);
  analytics.setConsent(true);
  assert.equal(calls[1][2].send_page_view, false);
  assert.equal(calls[2][1], 'page_view');
  assert.equal(calls[2][2].page_location, 'https://analytics.invalid/');
  assert.equal(calls[2][2].page_title, '');
  analytics.setConsent(false); analytics.navigate('home', 'second');
  assert.equal(calls.length, 4);
});

test('failed adapter activation leaves the gate closed and can be explicitly retried', () => {
  const sent = []; let fail = true;
  const analytics = createAnalytics({ pages: ['home'], events: ['save'], adapter: {
    activate: () => { if (fail) throw new Error('Unavailable transport'); }, send: event => sent.push(event)
  } });
  assert.throws(() => analytics.setConsent(true)); analytics.event('save'); assert.deepEqual(sent, []);
  fail = false; analytics.setConsent(true); analytics.event('save'); assert.equal(sent.length, 1);
});
