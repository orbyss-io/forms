import { Ajv2020, type ErrorObject } from "ajv/dist/2020.js";
import * as standaloneModule from "ajv/dist/standalone/index.js";
import type { JsonObject, JsonValue } from "@orbyss/program-kit-forms-contracts";

export interface AjvValidationIssue {
  readonly path: string;
  readonly keyword: string;
  readonly message: string;
  readonly property?: string;
}

export function compileBuildTimeValidator(schema: JsonObject): (data: JsonValue) => readonly AjvValidationIssue[] {
  const ajv = createProgramKitAjv();
  const validate = ajv.compile(schema);
  return data => {
    const valid = validate(data);
    if (valid) return [];
    return (validate.errors ?? []).map(toIssue);
  };
}

export function generateStandaloneValidatorModule(
  schema: JsonObject,
  exportName = "validate"
): string {
  if (!/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(exportName)) {
    throw new Error("The standalone validator export name must be a JavaScript identifier.");
  }
  const ajv = createProgramKitAjv();
  const schemaId = "urn:program-kit:standalone-validator";
  ajv.addSchema({ ...schema, $id: schemaId }, schemaId);
  const generate = (standaloneModule.default ?? standaloneModule) as unknown as (
    instance: Ajv2020,
    exports: Readonly<Record<string, string>>
  ) => string;
  return generate(ajv, { [exportName]: schemaId });
}

function createProgramKitAjv(): Ajv2020 {
  const ajv = new Ajv2020({
    allErrors: true,
    strict: true,
    allowUnionTypes: false,
    validateFormats: false,
    code: { source: true, esm: true }
  });
  for (const keyword of ["x-i18n", "x-description-i18n"] as const) {
    ajv.addKeyword({ keyword, schemaType: "string", valid: true, errors: false });
  }
  return ajv;
}

function toIssue(error: ErrorObject): AjvValidationIssue {
  const property = error.keyword === "required" && typeof error.params.missingProperty === "string"
    ? error.params.missingProperty
    : error.keyword === "additionalProperties" && typeof error.params.additionalProperty === "string"
      ? error.params.additionalProperty
      : undefined;
  return {
    path: error.instancePath,
    keyword: error.keyword,
    message: error.message ?? "Schema validation failed.",
    ...(property === undefined ? {} : { property })
  };
}
