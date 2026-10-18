"""Presentation only: escape user text and preserve its plain-text meaning."""
from html import escape
import re


def email_html(body):
    headings={'Purchasing priority briefing','At a glance','Restock priorities','Watchlist — no confirmed shortage',
              'Market context','Method and coverage','Open the full report','Review meeting'}
    def linked(text):
        return ''.join('<a style="color:#2563eb;word-break:break-word" href="'+escape(part,quote=True)+'">'+escape(part)+'</a>'
                       if re.fullmatch(r'https?://[^\s<>"\']+',part) else escape(part)
                       for part in re.split(r'(https?://[^\s<>"\']+)',text))
    sections=[]
    for paragraph in re.split(r'\n\s*\n',body.strip()):
        lines=paragraph.splitlines()
        if not lines:continue
        first=lines[0]
        if first in headings or re.match(r'^\d+\. ',first):
            sections.append('<section style="margin:0 0 22px"><h2 style="font-size:16px;line-height:1.5;color:#172554;margin:0 0 7px">'+linked(first)+'</h2>'+
                            ('<div style="white-space:pre-line">'+linked('\n'.join(lines[1:]))+'</div>' if len(lines)>1 else '')+'</section>')
        else:
            sections.append('<p style="white-space:pre-line;margin:0 0 18px">'+linked(paragraph)+'</p>')
    return '<!doctype html><html><body style="margin:0;background:#f8fafc"><div style="max-width:680px;margin:24px auto;padding:28px;background:#fff;font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.7;color:#334155">'+''.join(sections)+'</div></body></html>'
