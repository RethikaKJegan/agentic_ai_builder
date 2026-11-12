# Conjunctive query semantics

Saved query subway_query_3bf9eea3dfb443f9b9c4a6d07adaea60 combined an ordered negative-value filter and is_null on the same field. Flat filters are AND, so this unsatisfiable query returned zero matches from a full 22,550-record scan and supported a misleading report about two requested alternative categories.

Retain the existing query grammar. Teach connected workflow planning to represent alternative categories as separate existing query-plan/read branches, preserve common constraints, and bind all branch evidence into reporting. Teach query agents that flat predicates are conjunctive and each agent implements its assigned branch. Reject provably contradictory null, equality and compatible ordered predicates before source dispatch. Never rewrite AND to OR, drop filters, change currency/date authority or create unapproved effects.
