"""Shared adaptive context bounds; independent of workflow/case lifecycles."""

DEFAULT_LIMITS=dict(max_reasoning_turns=16,max_plan_revisions=4,max_tokens=1000000,
    max_tool_calls=32,max_llm_calls=64,max_seconds=600,evaluator_output_tokens=2000)


def brief(value, depth=0):
    """Bounded projection only; immutable digests identify complete stored values."""
    if isinstance(value,str):return value[:512]
    if depth>=4 and isinstance(value,(dict,list)):return {'projection_truncated':True}
    if isinstance(value,list):return [brief(v,depth+1) for v in value[:4]]
    if isinstance(value,dict):return {k:brief(v,depth+1) for k,v in list(value.items())[:10]}
    return value
