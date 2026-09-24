# JIT constrained comparison

Fixture UCR comparison with fixed inputs, model adapter, tools, and seeds.

| Seed | Arm | Underlying arm | UCR | Task success |
|---:|---|---|---:|---:|
| 42 | baseline | no-rail | 0.5556 | 1.0 |
| 42 | prompt-only | prompt-only | 0.0 | 1.0 |
| 42 | full-rail | full-rail | 0.0 | 1.0 |
| 42 | jit-constrained | full-rail | 0.0 | 1.0 |
| 43 | baseline | no-rail | 0.5556 | 1.0 |
| 43 | prompt-only | prompt-only | 0.0 | 1.0 |
| 43 | full-rail | full-rail | 0.0 | 1.0 |
| 43 | jit-constrained | full-rail | 0.0 | 1.0 |
| 44 | baseline | no-rail | 0.5556 | 1.0 |
| 44 | prompt-only | prompt-only | 0.0 | 1.0 |
| 44 | full-rail | full-rail | 0.0 | 1.0 |
| 44 | jit-constrained | full-rail | 0.0 | 1.0 |

Evidence coverage is supported claims divided by evaluated claims. Misquote rate is not measured because this fixture contains no quoted external sources.

The fixture measures process evidence behavior. It is not a domain effectiveness result.
