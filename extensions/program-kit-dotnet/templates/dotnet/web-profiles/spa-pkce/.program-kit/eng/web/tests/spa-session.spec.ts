import { expect, test } from '@playwright/test';
import {
  createProgramKitLogoutChannel,
  evaluateProgramKitSession,
  localFirstProgramKitLogout,
  type ProgramKitSessionPolicy,
} from '../spa-session.js';

const policy: ProgramKitSessionPolicy = {
  idleMinutes: 30,
  absoluteMinutes: 480,
  absoluteDeadlineClaim: 'auth_time',
  tokenExpiryClaim: 'exp',
  crossTabCoordination: 'required-no-token-payload',
  providerLogoutFailure: 'local-session-remains-cleared',
};

test('silent renewal cannot move the original absolute deadline', () => {
  const decision = evaluateProgramKitSession(policy, {
    nowSeconds: 28_801,
    authTimeSeconds: 0,
    tokenExpiresAtSeconds: 40_000,
    lastActivityAtSeconds: 28_000,
  });
  expect(decision).toEqual({ active: false, reason: 'absolute-expiry' });
});

test('idle and token expiry both terminate the local session', () => {
  expect(evaluateProgramKitSession(policy, {
    nowSeconds: 2_000,
    authTimeSeconds: 0,
    tokenExpiresAtSeconds: 3_000,
    lastActivityAtSeconds: 100,
  })).toEqual({ active: false, reason: 'idle-expiry' });
  expect(evaluateProgramKitSession(policy, {
    nowSeconds: 1_000,
    authTimeSeconds: 0,
    tokenExpiresAtSeconds: 999,
    lastActivityAtSeconds: 900,
  })).toEqual({ active: false, reason: 'token-expiry' });
});

test('provider failure cannot restore locally cleared authentication', async () => {
  let authenticated = true;
  const result = await localFirstProgramKitLogout(
    () => { authenticated = false; },
    () => { throw new Error('provider unavailable'); },
  );
  expect(result).toBe('provider-unavailable');
  expect(authenticated).toBeFalsy();
});

test('cross-tab coordination sends only the fixed signed-out event', async () => {
  let resolveReceived: (() => void) | undefined;
  const received = new Promise<void>((resolve) => { resolveReceived = resolve; });
  const name = `program-kit-test-${Date.now()}`;
  const sender = createProgramKitLogoutChannel(() => undefined, name);
  const receiver = createProgramKitLogoutChannel(() => resolveReceived?.(), name);
  try {
    sender.announceSignOut();
    await received;
  } finally {
    sender.close();
    receiver.close();
  }
});
