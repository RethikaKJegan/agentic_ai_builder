# Design

Opt new UI requests into context.execution_input_mode=automatic. Stamp the proposal's extensible metadata with the same marker before validation, including LivePlannerProvider's correction loop. Give automatic proposals a distinct planner identity to preserve older saved workflows.

Use the existing canonical configuration.input/input_mapping for saved settings and metadata.trigger_templates.input_mapping for changing event data. No new shared data shape, runtime defaults, guessed configuration or published-revision migration is needed. For automatic workflows every declared input must have an event mapping, and workflows without trigger templates have no declared runtime inputs.

The workflow list loads the exact published revision before running. Automatic event workflows explain that the source event starts them; automatic manual workflows submit inputs={}. Legacy manually configured workflows retain their existing input flow.
