export interface DefaultModelFields {
  api_base?: string;
  api_key?: string;
  model_name?: string;
  model_provider?: string;
}

const LEGACY_REQUIRED_FIELDS = ["api_base", "api_key", "model", "model_provider"] as const;

/**
 * The model editor persists its values through models.defaults.  Older config
 * snapshots also expose a separate set of default-model fields; once at least
 * one model entry exists those legacy fields must not block saving.
 */
export function missingRequiredDefaultModelFields(
  legacyConfig: Record<string, string>,
  models: DefaultModelFields[],
): string[] {
  if (models.length > 0) {
    return [];
  }

  return LEGACY_REQUIRED_FIELDS.filter((key) => !(legacyConfig[key] ?? "").trim());
}
