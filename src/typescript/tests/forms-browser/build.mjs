import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { build } from "esbuild";
import { generateStandaloneValidatorModule } from "@orbyss/program-kit-forms-ajv-build";
import { schema } from "./schema.mjs";

const workspace = resolve(import.meta.dirname, "../..");
const output = resolve(workspace, "../../artifacts/forms-browser");
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
const validator = generateStandaloneValidatorModule(schema);
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
    name: "program-kit-precompiled-validator",
    setup(buildApi) {
      buildApi.onResolve({ filter: /^program-kit:validator$/ }, () => ({ path: "validator", namespace: "program-kit" }));
      buildApi.onLoad({ filter: /.*/, namespace: "program-kit" }, () => ({ contents: validator, loader: "js", resolveDir: workspace }));
    }
  }]
});
await cp(resolve(import.meta.dirname, "index.html"), resolve(output, "index.html"));
const fixtureStyles = await readFile(resolve(import.meta.dirname, "styles.css"), "utf8");
const themeStyles = await readFile(resolve(workspace, "packages/ui-theme/default.css"), "utf8");
const formStyles = await readFile(resolve(workspace, "packages/forms-react/styles.css"), "utf8");
await writeFile(resolve(output, "styles.css"), `${themeStyles}\n${fixtureStyles}\n${formStyles}\n`);
const bundle = await readFile(resolve(output, "app.js"), "utf8");
await writeFile(resolve(output, "build-evidence.json"), JSON.stringify({
  schema: schema.$id,
  bytes: Buffer.byteLength(bundle),
  dynamicCodeGeneration: false,
  sourceMaps: false
}, null, 2));
console.log("Forms browser fixture bundled with a precompiled validator.");
