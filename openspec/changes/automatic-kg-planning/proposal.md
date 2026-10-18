# Automatic KG selection before workflow creation
Remove the mandatory Overview source preview, checkboxes and Google account picker.
One Generate action invokes server KG retrieval, passes a bounded relevant candidate
catalog to the existing planner, validates its one-to-four dataset selection and
opens the saved workflow. Candidate metadata is not an execution grant. Existing
explicit preview APIs, owned-source checks, stale evidence, join guards and action
approvals remain compatible. Existing configured server Google account behavior is
preserved; no arbitrary account substitution. No automatic external execution.
