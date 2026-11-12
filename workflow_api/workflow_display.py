"""Presentation titles never replace executable objectives."""
import re


def short_title(objective):
    stop = set("a an the this that those these is are be to of for by with and or in on at its it me my our please how many what all show create put send email summarize review recorded available".split())
    words = [w for w in re.findall(r"[\w]+(?:[-'][\w]+)*", objective) if w.lower() not in stop]
    words = [w[:35] for w in dict.fromkeys(w.lower() for w in words)][:4]
    if not words:return 'New workflow request'
    words += ['workflow', 'request'][:max(0,3-len(words))]
    return ' '.join(words).capitalize()


def valid_title(value):
    return isinstance(value, str) and 3 <= len(value.split()) <= 4 and len(value) <= 160 and not any(ord(c) < 32 for c in value)


def title_before_planning(objective, provider=None, env=None):
    title = None
    method = getattr(provider, 'workflow_title', None)
    if callable(method):
        try: title = method(objective)
        except Exception: pass
    elif env and env.get('OPENAI_API_KEY') and env.get('OPENAI_MODEL'):
        try:
            from planner.provider import OpenAIStructuredOutputProvider
            from openai import OpenAI
            title = OpenAIStructuredOutputProvider(client=OpenAI(api_key=env['OPENAI_API_KEY'], base_url=env.get('OPENAI_BASE_URL'), max_retries=0, timeout=20), model=env['OPENAI_MODEL']).workflow_title(objective)
        except Exception: pass
    return title.strip() if valid_title(title) else short_title(objective)


def display_title(doc):
    value = doc.get('display_name') or doc.get('overview_intent', {}).get('route', {}).get('display_name')
    return value if isinstance(value,str) and value.strip() else short_title(doc['objective'])
