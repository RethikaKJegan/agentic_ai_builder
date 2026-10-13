"""Keyless search and bounded public HTTPS page reading; no business defaults."""
import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import time
import threading
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin
from connector_extension.catalog import definition, obj, string
from connector_extension.common import Connector, denied
from runtime.service import RuntimeFailure


def public_url(url):
    try:
        p=urlsplit(url)
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError()
        addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError()
        return p,addresses[0][4][0]
    except (ValueError,OSError):denied('PUBLIC_PAGE_REQUIRED','Only public HTTPS websites can be inspected.',400)


class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.hidden=0;self.contacts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'):self.hidden+=1
        if tag=='a':
            href=dict(attrs).get('href','')
            if href.startswith('mailto:'):self.parts.append(href[7:].split('?')[0])
            elif any(word in href.lower() for word in ('contact','enquir','about')):self.contacts.append(href)
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)


def fetch_public_page(url,timeout):
    deadline=time.monotonic()+min(timeout,30);current=url
    for hop in range(4):
        remaining=deadline-time.monotonic()
        if remaining<=0:denied('PAGE_TIMEOUT','Public page reading timed out.',504)
        parsed,ip=public_url(current)
        connection=http.client.HTTPSConnection(parsed.hostname,timeout=min(remaining,10),context=ssl.create_default_context())
        # Pin every checked redirect address, preserving hostname certificate checks.
        def connect():
            sock=socket.create_connection((ip,443),timeout=min(remaining,10))
            connection.sock=connection._context.wrap_socket(sock,server_hostname=parsed.hostname)
        connection.connect=connect
        try:
            connection.request('GET',(parsed.path or '/')+('?' + parsed.query if parsed.query else ''),
                               headers={'User-Agent':'MESH-Supplier-Research/1.0','Accept':'text/html,text/plain','Accept-Encoding':'identity'})
            response=connection.getresponse()
            if response.status in (301,302,303,307,308):
                location=response.getheader('Location')
                if not location or hop==3:denied('PAGE_REDIRECT_LIMIT','Website has an invalid or excessive redirect chain.',502)
                current=urljoin(current,location);continue
            if response.status!=200:
                denied('PAGE_HTTP_'+str(response.status),'Website rejected the public page request.',502)
            mime=response.getheader('Content-Type','').lower()
            if not any(v in mime for v in ('text/html','text/plain')):denied('PAGE_TYPE_UNSUPPORTED','Only HTML and plain text pages are supported.',400)
            content=response.read(2097153)
            if len(content)>2097152:denied('PAGE_TOO_LARGE','Website exceeds the two-MiB page bound.',502)
            decoded=content.decode('utf-8',errors='replace');contacts=[]
            if 'text/html' in mime:
                parser=Text();parser.feed(decoded);decoded=' '.join(parser.parts)
                for href in parser.contacts:
                    contact=urljoin(current,href)
                    if urlsplit(contact).scheme=='https' and urlsplit(contact).hostname==urlsplit(current).hostname and contact not in contacts:
                        contacts.append(contact)
            text=re.sub(r'\s+',' ',decoded).strip()
            # Preserve footer contacts when long navigation/product markup precedes them.
            emails=sorted(set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',text)))[:20]
            excerpt=text if len(text)<=24000 else text[:18000]+' [middle omitted] '+text[-5900:]
            return {'url':current,'text':excerpt,'content_sha256':hashlib.sha256(excerpt.encode()).hexdigest(),
                    'emails':emails,'contact_urls':contacts[:2],'truncated':len(text)>24000}
        except RuntimeFailure:
            raise
        except (OSError, http.client.HTTPException):
            denied('PAGE_UNAVAILABLE','The public website could not be reached; other sources can be inspected.',502)
        finally:connection.close()


SEARCH=definition('supplier_web_search','ddgs','web_search','Search public supplier websites without an API key.',
    obj({'query':string(500),'region':string(20),'max_results':{'type':'integer','minimum':1,'maximum':5}},['query','region','max_results']),
    obj({'results':{'type':'array','maxItems':5,'items':obj({'title':string(500),'url':string(2000),
         'snippet':{'type':'string','maxLength':3000}},['title','url','snippet'])}},['results']),[],'data.read')
PAGE=definition('supplier_read_page','ddgs','read_public_page','Read bounded public HTTPS text and published emails.',
    obj({'url':string(2000)},['url']),
    obj({'url':string(2000),'text':{'type':'string','maxLength':24000},'content_sha256':string(64),
         'emails':{'type':'array','maxItems':20,'items':string(254)},
         'contact_urls':{'type':'array','maxItems':2,'items':string(2000)},'truncated':{'type':'boolean'}},['url','text','content_sha256','emails']),[],'data.read')
for tool in (SEARCH,PAGE):tool['authentication']={'mode':'none','credential_reference_required':False,'scopes':[]}


class SupplierSearchConnector(Connector):
    search_lock=threading.Lock()
    next_search=0.0
    def __init__(self,tool):super().__init__(tool,None)
    def execute(self,grant,inputs,effect_id,deadline):
        if self.definition['tool_id']==PAGE['tool_id']:
            return fetch_public_page(inputs['url'],deadline-time.monotonic())
        from ddgs import DDGS
        for backend in ('auto','bing','duckduckgo'):
            remaining=deadline-time.monotonic()
            if remaining<2:break
            try:
                with self.search_lock:
                    pause=max(0,self.next_search-time.monotonic())
                    if pause>remaining-1:break
                    if pause:time.sleep(pause)
                    type(self).next_search=time.monotonic()+1
                    with DDGS(timeout=min(6,max(1,int(deadline-time.monotonic())))) as search:
                        raw=search.text(inputs['query'],region=inputs['region'],max_results=inputs['max_results'],backend=backend)
                results=[];seen=set()
                for r in raw:
                    url=r.get('href') or r.get('url') or ''
                    if url in seen or not url.startswith('https://') or len(url)>2000:continue
                    seen.add(url)
                    results.append({'title':(r.get('title') or 'Untitled')[:500],'url':url,'snippet':(r.get('body') or '')[:3000]})
                if results:return {'results':results[:inputs['max_results']]}
            except Exception:continue
        denied('SEARCH_UNAVAILABLE','Bounded search backends returned no usable results; other project sections can continue.',503)
