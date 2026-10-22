export const BEHAVIOUR_LANGUAGES = [
  "English",
  "Hindi",
  "Tamil",
  "Telugu",
  "Spanish",
  "French",
  "German",
] as const;
export type BehaviourGroup = "communication" | "safety" | "boundaries";
export type BehaviourToggle =
  | "preferredLanguage"
  | "formalTone"
  | "conciseResponses"
  | "screenAbusiveLanguage"
  | "avoidHostileResponses"
  | "requireSupportingEvidence"
  | "strictOutputFormat"
  | "clarifyUncertainty";
export type AgentBehaviourPreferences = Record<BehaviourToggle, boolean> & {
  language: (typeof BEHAVIOUR_LANGUAGES)[number];
  presets: Record<BehaviourGroup, string | null>;
};
export const DEFAULT_AGENT_BEHAVIOUR: AgentBehaviourPreferences = {
  preferredLanguage: false,
  formalTone: false,
  conciseResponses: false,
  screenAbusiveLanguage: false,
  avoidHostileResponses: false,
  requireSupportingEvidence: false,
  strictOutputFormat: false,
  clarifyUncertainty: false,
  language: "English",
  presets: { communication: null, safety: null, boundaries: null },
};
type BehaviourPreset = { name: string; values: Partial<Record<BehaviourToggle, boolean>> };
export const BEHAVIOUR_PRESETS: Record<BehaviourGroup, readonly BehaviourPreset[]> = {
  communication: [
    { name: "Professional", values: { formalTone: true, conciseResponses: false } },
    { name: "Friendly", values: { formalTone: false, conciseResponses: false } },
    { name: "Concise", values: { formalTone: false, conciseResponses: true } },
  ],
  safety: [
    {
      name: "Respectful",
      values: {
        screenAbusiveLanguage: true,
        avoidHostileResponses: true,
        requireSupportingEvidence: false,
      },
    },
    {
      name: "Evidence-led",
      values: {
        screenAbusiveLanguage: false,
        avoidHostileResponses: true,
        requireSupportingEvidence: true,
      },
    },
    {
      name: "Strict",
      values: {
        screenAbusiveLanguage: true,
        avoidHostileResponses: true,
        requireSupportingEvidence: true,
      },
    },
  ],
  boundaries: [
    { name: "Flexible", values: { strictOutputFormat: false, clarifyUncertainty: false } },
    { name: "Structured", values: { strictOutputFormat: true, clarifyUncertainty: false } },
    { name: "Strict format", values: { strictOutputFormat: true, clarifyUncertainty: true } },
  ],
};
