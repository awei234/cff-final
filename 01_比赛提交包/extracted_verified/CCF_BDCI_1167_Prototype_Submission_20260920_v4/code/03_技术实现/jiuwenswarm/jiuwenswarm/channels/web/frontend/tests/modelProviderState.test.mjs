import assert from "node:assert/strict";
import test from "node:test";

import {
  MODEL_PROVIDER_OPTIONS,
  applyProviderDefaults,
} from "../node_modules/.cache/model-provider-state/components/ConfigPanel/modelProviderState.js";

test("provider options expose native and extension providers", () => {
  assert.ok(MODEL_PROVIDER_OPTIONS.includes("Anthropic"));
  assert.ok(MODEL_PROVIDER_OPTIONS.includes("Gemini"));
  assert.ok(MODEL_PROVIDER_OPTIONS.includes("OpenAICompatible"));
  assert.ok(MODEL_PROVIDER_OPTIONS.includes("DeepSeek"));
});

test("provider defaults never overwrite user-entered endpoint or model", () => {
  assert.deepEqual(
    applyProviderDefaults(
      { api_base: "https://proxy.test", model_name: "custom-model" },
      "Gemini",
    ),
    { api_base: "https://proxy.test", model_name: "custom-model" },
  );
  assert.equal(
    applyProviderDefaults({ api_base: "", model_name: "" }, "Anthropic").api_base,
    "https://api.anthropic.com",
  );
});
