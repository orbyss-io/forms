import { expect, test } from '@playwright/test';
import { beginProgramKitBffLogout } from '../bff-session.js';

const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
const originalDocument = Object.getOwnPropertyDescriptor(globalThis, 'document');
const originalFetch = Object.getOwnPropertyDescriptor(globalThis, 'fetch');

function restore(name: 'window' | 'document' | 'fetch', descriptor: PropertyDescriptor | undefined) {
  if (descriptor) Object.defineProperty(globalThis, name, descriptor);
  else Reflect.deleteProperty(globalThis, name);
}

test.afterEach(() => {
  restore('window', originalWindow);
  restore('document', originalDocument);
  restore('fetch', originalFetch);
});

test('rejects non-local contract paths before opening provider logout', async () => {
  await expect(beginProgramKitBffLogout({ logoutPath: 'https://attacker.example/logout' }))
    .rejects.toThrow('logoutPath must be an application-local absolute path.');
});

test('submits the managed antiforgery form and waits for local termination', async () => {
  const requests: string[] = [];
  const assignments: string[] = [];
  const popup = { close: () => { throw new Error('successful logout must not close the provider window'); } };
  const field = { type: '', name: '', value: '' };
  let submitted = false;
  let removed = false;
  const form = {
    method: '',
    action: '',
    target: '',
    hidden: false,
    append: (value: unknown) => expect(value).toBe(field),
    submit: () => { submitted = true; },
    remove: () => { removed = true; },
  };
  const documentStub = {
    createElement: (name: string) => {
      if (name === 'form') return form;
      if (name === 'input') return field;
      throw new Error(`unexpected element ${name}`);
    },
    body: { append: (value: unknown) => expect(value).toBe(form) },
  };
  const windowStub = {
    open: (url: string, name: string) => {
      expect(url).toBe('about:blank');
      expect(name).toBe('program-kit-provider-logout');
      return popup;
    },
    location: { assign: (value: string) => assignments.push(value) },
  };
  const fetchStub = async (input: string | URL | Request): Promise<Response> => {
    const path = String(input);
    requests.push(path);
    if (path === '/bff/antiforgery') {
      return Response.json({
        headerName: 'X-CSRF-TOKEN',
        formFieldName: '__RequestVerificationToken',
        requestToken: 'governed-token',
      });
    }
    if (path === '/bff/user') return Response.json({ authenticated: false });
    throw new Error(`unexpected request ${path}`);
  };
  Object.defineProperty(globalThis, 'window', { value: windowStub, configurable: true });
  Object.defineProperty(globalThis, 'document', { value: documentStub, configurable: true });
  Object.defineProperty(globalThis, 'fetch', { value: fetchStub, configurable: true });

  await beginProgramKitBffLogout();

  expect(requests).toEqual(['/bff/antiforgery', '/bff/user']);
  expect(form).toMatchObject({
    method: 'post',
    action: '/bff/logout',
    target: 'program-kit-provider-logout',
    hidden: true,
  });
  expect(field).toEqual({
    type: 'hidden',
    name: '__RequestVerificationToken',
    value: 'governed-token',
  });
  expect(submitted).toBe(true);
  expect(removed).toBe(true);
  expect(assignments).toEqual(['/bff/signed-out?remote=pending']);
});

test('closes the provider window when the antiforgery contract fails', async () => {
  let closed = false;
  const windowStub = {
    open: () => ({ close: () => { closed = true; } }),
    location: { assign: () => { throw new Error('failed logout must not navigate'); } },
  };
  Object.defineProperty(globalThis, 'window', { value: windowStub, configurable: true });
  Object.defineProperty(globalThis, 'fetch', {
    value: async () => Response.json({ requestToken: '' }),
    configurable: true,
  });

  await expect(beginProgramKitBffLogout()).rejects.toThrow(
    'The BFF antiforgery response does not match the managed contract.',
  );
  expect(closed).toBe(true);
});
