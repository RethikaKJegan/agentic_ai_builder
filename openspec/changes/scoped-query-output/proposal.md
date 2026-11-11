# Constrain generated projections and provide precise validation feedback

The saved oil-leak draft run failed after two generated-query validation attempts.
Rejected output was not persisted, so the exact violated rule cannot be established
retrospectively. Current generic feedback hides the validator reason. For catalogues
without authorized relationships, constrain the model's output projection to its
selected dataset using per-dataset schema alternatives. Retain an empty-source
clarification branch and normal source checks. Keep large/relationship catalogues on
the existing schema rather than introducing schema-size or join restrictions.
Return the trusted validator's precise rule in bounded metadata-only feedback. Do
not expose source rows, drop invalid fields or increase retry/budget allowances.
