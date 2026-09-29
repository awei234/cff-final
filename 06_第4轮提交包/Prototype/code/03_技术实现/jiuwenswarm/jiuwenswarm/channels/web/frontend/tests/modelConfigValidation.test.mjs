import test from "node:test";
import assert from "node:assert/strict";

import { missingRequiredDefaultModelFields } from "../node_modules/.cache/model-config-validation/components/ConfigPanel/modelConfigValidation.js";

test("uses configured model entries instead of legacy config fields", () => {
  const missing = missingRequiredDefaultModelFields(
    {
      api_base: "",
      api_key: "",
      model: "",
      model_provider: "",
    },
    [
      {
        api_base: "https://api.deepseek.com",
        api_key: "masked-secret",
        model_name: "deepseek-chat",
        model_provider: "DeepSeek",
      },
    ],
  );

  assert.deepEqual(missing, []);
});

test("falls back to legacy fields when no model entries exist", () => {
  const missing = missingRequiredDefaultModelFields(
    {
      api_base: "https://api.example.com",
      api_key: "",
      model: "example-model",
      model_provider: "OpenAI",
    },
    [],
  );

  assert.deepEqual(missing, ["api_key"]);
});
