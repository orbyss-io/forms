import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { generateStandaloneValidatorModule } from "@orbyss-io/forms-ajv-build";
import { dictionaries } from "./locales.mjs";

export const sha256 = content => createHash("sha256").update(content, "utf8").digest("hex");

/** Trusted application build: exact published bytes, complete dictionaries, static validator. */
export async function createReferenceDeployment() {
  const fixture = JSON.parse(await readFile(new URL("../fixtures/published-product.json", import.meta.url), "utf8"));
  const releaseJson = fixture.releaseJson;
  const release = JSON.parse(releaseJson);
  const schema = JSON.parse(release.candidate.dataSchema.content);
  const validatorSource = generateStandaloneValidatorModule(schema);
  if (sha256(release.candidate.dataSchema.content) !== release.candidate.dataSchema.sha256) throw new Error("Published schema digest mismatch.");
  if (/\beval\s*\(|new\s+Function\b/.test(validatorSource)) throw new Error("Validator violates the no-dynamic-code contract.");
  const localeJson = Object.fromEntries(Object.entries(dictionaries).map(([locale, values]) => [locale, JSON.stringify(values)]));
  const manifest = {
    formatVersion: 1, formId: release.candidate.formId.value, releaseId: release.id.value,
    revision: release.candidate.revision.value, releaseSha256: sha256(releaseJson),
    locales: Object.fromEntries(Object.entries(localeJson).map(([locale, content]) => [locale, sha256(content)])),
    validator: { sha256: sha256(validatorSource), schemaSha256: release.candidate.dataSchema.sha256 }, retired: false
  };
  return { fixture, releaseJson, localeJson, manifest, validatorSource, schema };
}
