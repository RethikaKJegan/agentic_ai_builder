# One bounded LLM validation correction

Reuse the planner's existing two-attempt loop and supply actionable rule feedback
plus the secret-checked prior draft. Add a shared one-correction wrapper for pure
runtime model calls (coordinator decisions, specialist decisions and ordinary
agent outputs). Only JSON/output-schema failures qualify. Each correction must
reserve another model call and recheck current authority/deadlines. No tool,
external action, uncertain effect, approval, credential or budget error is retried.
Failed calls retain conservative reservations. No schema or permission weakening.
