export const schema = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "urn:orbyss:forms:browser-acceptance:1",
  type: "object",
  properties: {
    name: { type: "string" },
    notes: { type: "string", maxLength: 500 },
    quantity: { type: "integer", minimum: 1, maximum: 20 },
    updates: { type: "boolean" },
    role: { type: "string", enum: ["reader", "writer"] },
    channels: { type: "array", items: { type: "string", enum: ["email", "sms", "push"] }, uniqueItems: true },
    plan: { type: "string", enum: ["starter", "professional"] }
  },
  required: ["name"],
  additionalProperties: false
};
