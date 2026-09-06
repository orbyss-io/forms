// Provider-neutral basic consent gate. No module-level network, cookies, URL or storage access.
export function createAnalytics({ pages = [], events = [], adapter = null } = {}) {
  const validateIds = values => {
    if (!Array.isArray(values) || values.some(v => typeof v !== 'string' || !/^[a-z][a-z0-9_-]{0,79}$/.test(v)))
      throw new Error('Analytics identifiers must be approved constant slugs');
    return new Set(values);
  };
  const pageIds = validateIds(pages), eventIds = validateIds(events);
  let consent = false, currentPage = null, currentNavigation = null, lastSent = null;
  const sendPage = () => {
    if (!consent || !adapter || currentPage === null || currentNavigation === lastSent) return;
    adapter.send(Object.freeze({ type: 'page_view', page_id: currentPage }));
    lastSent = currentNavigation;
  };
  return Object.freeze({
    setConsent(granted) {
      if (typeof granted !== 'boolean') throw new Error('Consent must be an explicit boolean');
      if (consent === granted) return;
      if (granted) { adapter?.activate?.(); consent = true; sendPage(); }
      else { consent = false; lastSent = null; adapter?.deactivate?.(); }
    },
    navigate(pageId, navigationId) {
      if (!pageIds.has(pageId) || typeof navigationId !== 'string' || !navigationId)
        throw new Error('Use a catalogued page and a stable navigation identifier');
      // The identifier is local deduplication state; it is never sent to a provider.
      if (currentNavigation === navigationId && currentPage !== pageId)
        throw new Error('A navigation identifier cannot represent two pages');
      currentPage = pageId; currentNavigation = navigationId; sendPage();
    },
    event(eventId) {
      if (!eventIds.has(eventId)) throw new Error('Unknown analytics event');
      if (consent && adapter) adapter.send(Object.freeze({ type: 'event', event_id: eventId }));
    }
  });
}

// Adapter for a consumer-owned gtag transport. This module never injects Google scripts.
// Load the transport only inside activateTransport, after consent. Disable all automatic history
// page views/enhanced measurement in the GA property; do not combine another page-view owner.
export function createGa4Adapter({ measurementId, activateTransport, deactivateTransport }) {
  if (!/^G-[A-Z0-9]+$/.test(measurementId) || typeof activateTransport !== 'function' || typeof deactivateTransport !== 'function')
    throw new Error('GA4 requires an explicit measurement ID and consent-aware transport lifecycle');
  let send = null;
  return Object.freeze({
    activate() {
      send = activateTransport();
      if (typeof send !== 'function') { send = null; throw new Error('Transport must return a synchronous command queue'); }
      send('config', measurementId, { send_page_view: false, allow_google_signals: false,
        allow_ad_personalization_signals: false, page_location: 'https://analytics.invalid/', page_title: '' });
    },
    deactivate() { send = null; deactivateTransport(); },
    send(event) {
      if (!send) return;
      const name = event.type === 'page_view' ? 'page_view' : event.event_id;
      const parameters = { send_to: measurementId, page_location: 'https://analytics.invalid/', page_title: '',
        ...(event.page_id ? { page_id: event.page_id } : {}) };
      send('event', name, parameters);
    }
  });
}
