"use client";
import {useState} from "react";
import type {SemanticEdge as OntologyEdge} from "@/api/semantic-kg";
const control = "rounded-lg border bg-background px-3 py-2 text-sm disabled:opacity-40";
export default function KGRelationshipReview({
  edge,
  disabled,
  save,
}: {
  edge: OntologyEdge;
  disabled: boolean;
  save: (body: object) => void;
}) {
  const [predicate, setPredicate] = useState(edge.predicate??"");
  const [reverse, setReverse] = useState(edge.reversed);
  return (
    <form
      className="space-y-3 rounded-xl border p-3"
      onSubmit={(e) => {
        e.preventDefault();
        save({ predicate, reversed: reverse, status: "confirmed" });
      }}
    >
      <h4 className="font-medium">Review business relationship</h4>
      <label className="block text-sm">
        Relationship label
        <input
          aria-label="Relationship label"
          className={`${control} mt-1 w-full`}
          required
          maxLength={80}
          disabled={disabled}
          value={predicate}
          onChange={(e) => setPredicate(e.target.value)}
        />
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          disabled={disabled}
          checked={reverse}
          onChange={(e) => setReverse(e.target.checked)}
        />
        Reverse business direction
      </label>
      <p className="text-xs text-muted-foreground">
        This changes business meaning only. Source field pairs and executable relationship
        permissions remain independently reviewed.
      </p>
      <div className="flex flex-wrap gap-2">
        <button className={control} disabled={disabled || !predicate.trim()}>
          Confirm relationship
        </button>
        <button
          type="button"
          className={control}
          disabled={disabled}
          onClick={() => save({ predicate, reversed: reverse, status: "rejected" })}
        >
          Reject business relationship
        </button>
        <button
          type="button"
          className={control}
          disabled={disabled}
          onClick={() => save({ predicate, reversed: reverse, status: "suggested" })}
        >
          Reset business review
        </button>
      </div>
    </form>
  );
}

