export interface ProgramKitBffSession {
  authenticated: boolean;
}

export interface ProgramKitAntiforgeryToken {
  headerName: 'X-CSRF-TOKEN';
  formFieldName: '__RequestVerificationToken';
  requestToken: string;
}

export interface ProgramKitBffLogoutOptions {
  antiforgeryPath?: string;
  logoutPath?: string;
  sessionPath?: string;
  signedOutPath?: string;
  popupName?: string;
  localTerminationTimeoutMilliseconds?: number;
}

function localPath(value: string, label: string): string {
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) {
    throw new Error(`${label} must be an application-local absolute path.`);
  }
  return value;
}

async function waitForLocalTermination(path: string, timeoutMilliseconds: number): Promise<void> {
  const deadline = Date.now() + timeoutMilliseconds;
  while (Date.now() < deadline) {
    const response = await fetch(path, { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) throw new Error('The BFF session endpoint did not return a successful response.');
    const session = await response.json() as ProgramKitBffSession;
    if (session.authenticated === false) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('The BFF did not confirm local session termination within the governed timeout.');
}

/**
 * Invoke directly from a trusted user gesture. It opens provider logout in a separate top-level
 * context, then keeps the application window on the deterministic same-origin signed-out route.
 */
export async function beginProgramKitBffLogout(
  options: ProgramKitBffLogoutOptions = {},
): Promise<void> {
  const antiforgeryPath = localPath(options.antiforgeryPath ?? '/bff/antiforgery', 'antiforgeryPath');
  const logoutPath = localPath(options.logoutPath ?? '/bff/logout', 'logoutPath');
  const sessionPath = localPath(options.sessionPath ?? '/bff/user', 'sessionPath');
  const signedOutPath = localPath(options.signedOutPath ?? '/bff/signed-out', 'signedOutPath');
  const popupName = options.popupName ?? 'program-kit-provider-logout';
  const timeout = options.localTerminationTimeoutMilliseconds ?? 5000;
  const providerWindow = window.open('about:blank', popupName);
  if (!providerWindow) throw new Error('Provider logout requires a user-initiated top-level window.');

  try {
    const tokenResponse = await fetch(antiforgeryPath, {
      credentials: 'same-origin',
      cache: 'no-store',
    });
    if (!tokenResponse.ok) throw new Error('The BFF antiforgery endpoint did not succeed.');
    const token = await tokenResponse.json() as ProgramKitAntiforgeryToken;
    if (
      token.headerName !== 'X-CSRF-TOKEN'
      || token.formFieldName !== '__RequestVerificationToken'
      || !token.requestToken
    ) {
      throw new Error('The BFF antiforgery response does not match the managed contract.');
    }

    const form = document.createElement('form');
    form.method = 'post';
    form.action = logoutPath;
    form.target = popupName;
    form.hidden = true;
    const field = document.createElement('input');
    field.type = 'hidden';
    field.name = token.formFieldName;
    field.value = token.requestToken;
    form.append(field);
    document.body.append(form);
    form.submit();
    form.remove();

    await waitForLocalTermination(sessionPath, timeout);
    window.location.assign(`${signedOutPath}?remote=pending`);
  } catch (error) {
    providerWindow.close();
    throw error;
  }
}
