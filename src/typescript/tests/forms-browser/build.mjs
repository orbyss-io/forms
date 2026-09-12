import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { build } from "esbuild";
import { createReferenceDeployment, sha256 } from "./deployment.mjs";

const workspace = resolve(import.meta.dirname, "../..");
const output = resolve(workspace, "../../artifacts/forms-browser");
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
const deployment = await createReferenceDeployment();
const { validatorSource: validator, schema } = deployment;
if (sha256(validator) !== deployment.manifest.validator.sha256) throw new Error("Static validator binding mismatch.");
if (/\beval\s*\(|new\s+Function\b/.test(validator)) throw new Error("Generated validator violates the CSP contract.");
await build({
  entryPoints: [resolve(import.meta.dirname, "app.tsx")],
  outfile: resolve(output, "app.js"),
  bundle: true,
  format: "esm",
  platform: "browser",
  target: ["es2022"],
  jsx: "automatic",
  minify: true,
  sourcemap: false,
  define: { "process.env.NODE_ENV": "\"production\"" },
  plugins: [{
    name: "orbyss-forms-precompiled-validator",
    setup(buildApi) {
      buildApi.onResolve({ filter: /^orbyss-forms:validator$/ }, () => ({ path: "validator", namespace: "orbyss-forms" }));
      buildApi.onLoad({ filter: /.*/, namespace: "orbyss-forms" }, () => ({ contents: validator + `\nexport const binding = ${JSON.stringify({ sha256: sha256(validator), schemaSha256: sha256(deployment.fixture.release.candidate.dataSchema.content) })};\n`, loader: "js", resolveDir: workspace }));
      buildApi.onResolve({ filter: /^orbyss-forms:deployment$/ }, () => ({ path: "deployment", namespace: "orbyss-deployment" }));
      buildApi.onLoad({ filter: /.*/, namespace: "orbyss-deployment" }, () => ({ contents: `export default ${JSON.stringify({ releaseJson: deployment.releaseJson, localeJson: deployment.localeJson, manifest: deployment.manifest })}`, loader: "js" }));
    }
  }]
});
await cp(resolve(import.meta.dirname, "index.html"), resolve(output, "index.html"));
const fixtureStyles = await readFile(resolve(import.meta.dirname, "styles.css"), "utf8");
const themeStyles = await readFile(resolve(workspace, "packages/ui-theme/default.css"), "utf8");
await writeFile(resolve(output, "styles.css"), `${themeStyles}\n${fixtureStyles}\n`);
const bundle = await readFile(resolve(output, "app.js"), "utf8");
await writeFile(resolve(output, "build-evidence.json"), JSON.stringify({
  schema: schema.$id,
  release: deployment.manifest.releaseId,
  releaseSha256: deployment.manifest.releaseSha256,
  validatorSha256: deployment.manifest.validator.sha256,
  locales: Object.keys(deployment.manifest.locales),
  bytes: Buffer.byteLength(bundle),
  dynamicCodeGeneration: false,
  sourceMaps: false
}, null, 2));
console.log("Forms engine browser fixture bundled with a precompiled validator and fixture-owned renderer.");
