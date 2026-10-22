"use client";
import { useEffect, useRef, useState } from "react";
import { MessageSquare, ShieldCheck, SlidersHorizontal, ArrowRight } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { useMesh } from "@/domain/store";
import {
  BEHAVIOUR_LANGUAGES,
  BEHAVIOUR_PRESETS,
  type AgentBehaviourPreferences,
  type BehaviourGroup,
  type BehaviourToggle,
} from "@/domain/agent-behaviour";
import type { api } from "@/api/client";

type Policies = NonNullable<Awaited<ReturnType<typeof api.monitoring>>["policies"]>;
const groups = [
  {
    id: "communication",
    title: "Communication",
    description: "Choose how agents speak and respond.",
    icon: MessageSquare,
    controls: [
      {
        key: "preferredLanguage",
        label: "Preferred language",
        description: "Request replies in your chosen language.",
      },
      {
        key: "formalTone",
        label: "Formal tone",
        description: "Request professional, measured wording.",
      },
      {
        key: "conciseResponses",
        label: "Concise responses",
        description: "Request shorter, focused answers.",
      },
    ],
  },
  {
    id: "safety",
    title: "Behaviour & Safety",
    description: "Set expectations for respectful, grounded responses.",
    icon: ShieldCheck,
    controls: [
      {
        key: "screenAbusiveLanguage",
        label: "Screen abusive language",
        description: "Request screening for abusive or offensive wording.",
      },
      {
        key: "avoidHostileResponses",
        label: "Avoid hostile responses",
        description: "Request respectful, non-threatening language.",
      },
      {
        key: "requireSupportingEvidence",
        label: "Require supporting evidence",
        description: "Request sources and acknowledge missing evidence.",
      },
    ],
  },
  {
    id: "boundaries",
    title: "Response Boundaries",
    description: "Choose structure and how uncertainty is handled.",
    icon: SlidersHorizontal,
    controls: [
      {
        key: "strictOutputFormat",
        label: "Strict output format",
        description: "Request the chosen format without extra commentary.",
      },
      {
        key: "clarifyUncertainty",
        label: "Clarify uncertainty",
        description: "Request clarification when instructions are ambiguous.",
      },
    ],
  },
] as const;
export function AgentBehaviourPanel({
  policies,
  onViewLimits,
}: {
  policies: Policies;
  onViewLimits: () => void;
}) {
  const saved = useMesh((state) => state.agentBehaviourPreferences);
  const apply = useMesh((state) => state.applyAgentBehaviourPreferences);
  const [preferences, setPreferences] = useState<AgentBehaviourPreferences>(() =>
    structuredClone(saved),
  );
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const failed = useRef(false);
  useEffect(() => {
    const onFailure = () => {
      failed.current = true;
      setError(
        "Preferences could not be saved in this browser. Check browser storage, then apply again.",
      );
      setMessage("");
    };
    window.addEventListener("mesh-draft-storage-error", onFailure);
    return () => window.removeEventListener("mesh-draft-storage-error", onFailure);
  }, []);
  const dirty = JSON.stringify(preferences) !== JSON.stringify(saved);
  const change = (group: BehaviourGroup, key: BehaviourToggle, value: boolean) => {
    setPreferences((current) => ({
      ...current,
      [key]: value,
      presets: { ...current.presets, [group]: null },
    }));
    setMessage("");
    setError("");
  };
  const policy = policies.find((item) => item.agents.length > 0);
  const agent = policy?.agents[0];
  const cost = agent?.limits["max_estimated_cost_usd"];
  return (
    <section
      aria-label="Agent Behaviour & Safety"
      className="mb-7 space-y-5 rounded-2xl border bg-background p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Agent Behaviour &amp; Safety</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Shape communication, behaviour and response boundaries.
          </p>
        </div>
        <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-medium text-muted-foreground">
          Browser preferences
        </span>
      </div>
      <div className="grid gap-4 xl:grid-cols-3">
        {groups.map((group) => (
          <section
            key={group.id}
            aria-label={group.title}
            className="min-w-0 rounded-xl border p-4"
          >
            <div className="flex items-center gap-2">
              <group.icon className="h-4 w-4 shrink-0 text-primary" />
              <h3 className="text-sm font-semibold">{group.title}</h3>
              <span aria-live="polite" className="ml-auto text-[10px] text-muted-foreground">
                {preferences.presets[group.id] ?? "Custom"}
              </span>
            </div>
            <p className="mt-2 min-h-10 text-xs leading-5 text-muted-foreground">
              {group.description}
            </p>
            <div
              role="group"
              aria-label={`${group.title} presets`}
              className="my-4 flex flex-wrap gap-1.5"
            >
              {BEHAVIOUR_PRESETS[group.id].map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  aria-pressed={preferences.presets[group.id] === preset.name}
                  onClick={() => {
                    setPreferences((current) => ({
                      ...current,
                      ...preset.values,
                      presets: { ...current.presets, [group.id]: preset.name },
                    }));
                    setMessage("");
                    setError("");
                  }}
                  className={`rounded-md border px-2 py-1.5 text-[11px] font-medium transition-colors ${preferences.presets[group.id] === preset.name ? "border-primary bg-primary/5 text-primary" : "text-muted-foreground hover:bg-muted"}`}
                >
                  {preset.name}
                </button>
              ))}
            </div>
            <div className="divide-y">
              {group.controls.map((control) => (
                <div key={control.key} className="py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <label
                        htmlFor={`behaviour-${control.key}`}
                        className="cursor-pointer text-xs font-medium"
                      >
                        {control.label}
                      </label>
                      <p
                        id={`behaviour-${control.key}-hint`}
                        className="mt-1 text-[11px] leading-5 text-muted-foreground"
                      >
                        {control.description}
                      </p>
                    </div>
                    <div className="mt-0.5 flex shrink-0 items-center gap-2">
                      <span aria-hidden className="text-[10px] text-muted-foreground">
                        {preferences[control.key] ? "On" : "Off"}
                      </span>
                      <Switch
                        id={`behaviour-${control.key}`}
                        aria-label={control.label}
                        aria-describedby={`behaviour-${control.key}-hint`}
                        checked={preferences[control.key]}
                        onCheckedChange={(value) => change(group.id, control.key, value)}
                      />
                    </div>
                  </div>
                  {control.key === "preferredLanguage" && preferences.preferredLanguage && (
                    <label className="mt-3 block text-[11px] text-muted-foreground">
                      Response language
                      <select
                        aria-label="Response language"
                        value={preferences.language}
                        onChange={(event) => {
                          setPreferences((current) => ({
                            ...current,
                            language: event.target.value as AgentBehaviourPreferences["language"],
                            presets: { ...current.presets, communication: null },
                          }));
                          setMessage("");
                          setError("");
                        }}
                        className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-xs text-foreground"
                      >
                        {BEHAVIOUR_LANGUAGES.map((language) => (
                          <option key={language} value={language}>
                            {language}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-muted/20 px-4 py-3">
        <div className="min-w-0">
          <h3 className="text-xs font-semibold">Execution limits</h3>
          {agent && policy ? (
            <>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Model calls ≤ {agent.limits.max_llm_calls} · Tool calls ≤{" "}
                {agent.limits.max_tool_calls} · Retries ≤ {agent.limits.max_retries}
                {typeof cost === "number" && Number.isFinite(cost) && cost >= 0
                  ? ` · Estimated cost cap $${cost}`
                  : ""}
              </p>
              <p className="mt-1 break-all text-[10px] text-muted-foreground">
                {policy.workflow_id} · v{policy.version} · {agent.agent_id}
              </p>
            </>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">
              Review available limits by workflow revision.
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onViewLimits}
          className="inline-flex shrink-0 items-center gap-1.5 text-xs font-medium text-primary"
        >
          View all limits
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
        <p className="text-[11px] leading-5 text-muted-foreground">
          Saved in this browser. Live agent execution remains unchanged.
        </p>
        <button
          type="button"
          disabled={!dirty && !error}
          onClick={() => {
            failed.current = false;
            setError("");
            try {
              apply(preferences);
              if (!failed.current) setMessage("Preferences saved in this browser.");
            } catch {
              setError("Preferences could not be saved. Try applying again.");
            }
          }}
          className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground disabled:opacity-40"
        >
          Apply preferences
        </button>
      </div>
      {message && (
        <p role="status" className="text-xs text-emerald-700">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
    </section>
  );
}
