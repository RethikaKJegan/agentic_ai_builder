# Account for the complete intent-routing envelope

The Subway discovery index has its own 180 KB bound, but intent routing adds
retrieved knowledge, resolved account inputs, tools and event descriptors before
enforcing a 220 KB bound. Individually valid components can exceed that total.
The reported procurement-and-email prompt hits this before any model call.

Allocate discovery's byte allowance from the actual remaining serialized context
after all sibling components are assembled. Preserve the existing total and
component ceilings, every source descriptor/relationship, account inputs,
knowledge and query completeness. No prompt-specific rules, limits increase,
permission change, source write or user-prompt workaround.

Reproduce full intent preparation on a private copy of the live Subway store,
with controlled intent responses and no network/provider calls. Add varied-prompt
and sibling-size regression checks, then deploy the backend-only correction.
