import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

type Persona = Readonly<{ username: string; password: string }>;
type RealmCredential = { type?: unknown; value?: unknown; temporary?: unknown };
type RealmUser = { username?: unknown; enabled?: unknown; credentials?: unknown };
type RealmFixture = {
  displayName?: unknown;
  attributes?: unknown;
  users?: unknown;
};

const realmPath = fileURLToPath(
  new URL('../../../deploy/keycloak/program-kit-realm.json', import.meta.url),
);

function loadRealm(): RealmFixture {
  const value: unknown = JSON.parse(readFileSync(realmPath, 'utf8'));
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('The managed local identity fixture must be a JSON object.');
  }
  const realm = value as RealmFixture;
  const attributes = realm.attributes as Record<string, unknown> | undefined;
  if (
    realm.displayName !== 'Program Kit Local Identity'
    || attributes?.programKitFixture !== 'local-non-production-only'
    || !Array.isArray(realm.users)
  ) {
    throw new Error('The managed identity realm is not explicitly classified as the local non-production fixture.');
  }
  const usernames = realm.users.map(user => user.username);
  const expected = ['local-user', 'local-admin', 'local-wrong-role'];
  if (usernames.length !== expected.length || expected.some(username => !usernames.includes(username))) {
    throw new Error('The managed local identity fixture must contain exactly the three governed personas.');
  }
  return realm;
}

function persona(realm: RealmFixture, username: string): Persona {
  const users = realm.users as RealmUser[];
  const user = users.find(candidate => candidate.username === username);
  const credentials = user?.credentials;
  if (!user || user.enabled !== true || !Array.isArray(credentials)) {
    throw new Error(`The managed local identity fixture has no enabled ${username} persona.`);
  }
  const passwords = (credentials as RealmCredential[]).filter(item => item.type === 'password');
  const credential = passwords.length === 1 ? passwords[0] : undefined;
  if (!credential || typeof credential.value !== 'string' || !credential.value || credential.temporary !== false) {
    throw new Error(`The managed local identity fixture has an invalid ${username} password credential.`);
  }
  return Object.freeze({ username, password: credential.value });
}

const realm = loadRealm();

export const personas = Object.freeze({
  user: persona(realm, 'local-user'),
  admin: persona(realm, 'local-admin'),
  wrongRole: persona(realm, 'local-wrong-role'),
});
