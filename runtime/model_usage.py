"""One confirmed model turn, under the server-owned accounting policy."""
from .service import RuntimeFailure


def validate_confirmed(actual,reservation,*,enforce_usage_budgets=True):
    if (not isinstance(actual,dict) or set(actual)!=set(reservation) or actual.get('llm_calls')!=1 or
            any(type(value) not in (int,float) or value<0 or value!=value or value==float('inf') or
                (value>reservation[key] and not (key in ('tokens','estimated_cost_usd') and not enforce_usage_budgets))
                for key,value in actual.items())):
        raise RuntimeFailure('INVALID_USAGE','Confirmed model usage is invalid or exceeds an enforced reservation.')
