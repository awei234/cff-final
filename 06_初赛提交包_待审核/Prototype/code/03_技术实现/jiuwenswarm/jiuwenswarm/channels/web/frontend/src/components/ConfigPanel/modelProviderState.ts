export const MODEL_PROVIDER_OPTIONS = [
  "OpenAI",
  "OpenAIAccount",
  "OpenAICompatible",
  "OpenRouter",
  "Anthropic",
  "Gemini",
  "DashScope",
  "SiliconFlow",
  "InferenceAffinity",
  "DeepSeek",
] as const;

export type ModelProvider = (typeof MODEL_PROVIDER_OPTIONS)[number];

const DEFAULT_API_BASES: Partial<Record<ModelProvider, string>> = {
  OpenAI: "https://api.openai.com/v1",
  OpenAIAccount: "https://chatgpt.com/backend-api/codex",
  OpenRouter: "https://openrouter.ai/api/v1",
  Anthropic: "https://api.anthropic.com",
  Gemini: "https://generativelanguage.googleapis.com",
  DashScope: "https://dashscope.aliyuncs.com/compatible-mode/v1",
  SiliconFlow: "https://api.siliconflow.cn/v1",
  DeepSeek: "https://api.deepseek.com",
};

export interface ModelProviderFields {
  api_base?: string;
  model_name?: string;
}

export function applyProviderDefaults<T extends ModelProviderFields>(
  current: T,
  provider: string,
): T {
  if (current.api_base?.trim()) return current;
  const defaultApiBase = DEFAULT_API_BASES[provider as ModelProvider];
  return defaultApiBase ? { ...current, api_base: defaultApiBase } : current;
}
