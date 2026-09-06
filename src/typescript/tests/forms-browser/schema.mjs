export const schema = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "urn:program-kit:forms:browser-acceptance:1",
  type: "object",
  properties: {
    name: { type: "string" },
    plan: { type: "string", enum: ["starter", "professional"] }
  },
  required: ["name"],
  additionalProperties: false
};
