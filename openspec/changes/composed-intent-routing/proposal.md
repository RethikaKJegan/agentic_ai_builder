# Canonicalize composed analysis and delivery

Hosted planning failed before composition with OVERVIEW_INTENT_INVALID because
the interpreter combined a population/investigation label with external actions.
Preserve the validated analysis scope and side effects but canonicalize this
combination to one_time or recurring according to its existing recurrence.
Improve transport instructions to prevent the contradiction. Do not add writes,
change recipients, suppress negations, retry historical jobs or bypass approvals.
