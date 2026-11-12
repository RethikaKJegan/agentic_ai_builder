# Consistent source metadata selection

The intent model chooses datasets and fields independently using unconstrained
string schemas. A generated field can be an invented identifier or can belong to
another owned dataset omitted from the model's dataset list. Existing catalogue
validation correctly rejects both with SUBWAY_QUERY_DENIED before planning.

Constrain the actual model transport to advertised metadata identities. Resolve
selection membership from exact current authorized field/relationship identities,
before workflow approval, without inventing joins or substituting unknown fields.
Treat a selected known field as an implicit selection of its owned source, within
the existing four-dataset ceiling. Retain strict catalogue/query/owner validation.
No name matching, prompt-specific rules or changes to existing saved workflows.

Verify invalid identities remain denied, ownership closure is deterministic and
bounded, and existing multi-source and Simpsons behavior remains compatible.
