# Preserve knowledge intent through connected execution

The exact hosted definition prompt was classified as knowledge, but the action
planner was shown query tools and generic query guidance. Retrieved source-cited
knowledge was omitted from runtime inputs. The resulting record query failed.

Pin the existing bounded owner-scoped knowledge retrieval, make it the content
step input and citation scope, and restrict knowledge intent to existing content
preparation. Keep population queries, investigations and recurring automation
unchanged. Missing knowledge is a precise clarification, never an invented answer.
Do not rewrite or retry the historical failed run. Improve its recovery explanation
without weakening worker leases or query validation.
