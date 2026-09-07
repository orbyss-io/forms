declare module "orbyss-forms:validator" {
  export function validate(data: unknown): boolean;
}

declare module "./schema.mjs" {
  export const schema: import("@orbyss-io/forms-contracts").JsonObject;
}
