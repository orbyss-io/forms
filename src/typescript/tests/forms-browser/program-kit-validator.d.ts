declare module "orbyss-forms:validator" {
  export function validate(data: unknown): boolean;
  export const binding: { readonly sha256: string; readonly schemaSha256: string };
  export namespace validate {
    const errors: readonly { instancePath: string; keyword: string; message?: string; params: unknown }[] | null;
  }
}

declare module "orbyss-forms:deployment" {
  const value: { releaseJson: string; localeJson: Record<string, string>; manifest: import("@orbyss-io/forms-contracts").FormDeploymentManifest };
  export default value;
}
