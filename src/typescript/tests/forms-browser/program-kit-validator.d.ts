declare module "program-kit:validator" {
  export function validate(data: unknown): boolean;
}

declare module "./schema.mjs" {
  export const schema: import("@orbyss/program-kit-forms-contracts").JsonObject;
}
