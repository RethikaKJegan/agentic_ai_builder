# Fulfilment control repair

The recorded acceptance extraction failed before any child/effect with
MODEL_OUTPUT_SCHEMA_INVALID. Tighten the model control transport to match the
existing reason/task bounds and encoded-object shape. Allow one new pure
extraction action for a failed fulfilment schema call, preserving its failed run;
never recover failed writes, unknown submissions or authorization failures.
