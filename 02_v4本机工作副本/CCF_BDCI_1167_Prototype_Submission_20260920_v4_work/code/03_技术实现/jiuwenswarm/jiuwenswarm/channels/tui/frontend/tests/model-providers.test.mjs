import assert from "node:assert/strict";
import test from "node:test";

import { MODEL_PROVIDER_OPTIONS } from "../dist/core/modelProviders.js";

test("TUI exposes all supported primary providers", () => {
  for (const provider of ["OpenAI", "OpenAICompatible", "Anthropic", "Gemini", "DashScope", "DeepSeek"]) {
    assert.ok(MODEL_PROVIDER_OPTIONS.includes(provider), provider);
  }
});
