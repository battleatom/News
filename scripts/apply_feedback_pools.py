#!/usr/bin/env python3
"""Apply persistent D/NR/NW feedback pools to the generated RSS feed.

D = suppress the marked article globally.
NR/NW = suppress the marked article only in the recorded category.
V5.2 hardens canonical title/source matching and de-duplicates pool rows in memory.
"""
from __future__ import annotations
import argparse,json,re,sys,urllib.error,urllib.parse,urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

DEFAULT_API='https://bkcrgfkhgjypvzwubwrh.supabase.co/functions/v1/news-feedback'
REASONS=('D','NR','NW')
DROP_Q={'utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','fbclid'}

def normalize_text(v:str|None)->str:
    s=(v or '').lower();s=re.sub(r'^\s*\d+[.)]\s*','',s);s=re.sub(r'\s+',' ',s).strip();return s

def canonical_title(v:str|None)->str:
    s=normalize_text(v)
    # Feed titles commonly append a publisher suffix. Remove it for stable identity.
    s=re.sub(r'\s+-\s+[^-]{2,60}$','',s)
    s=re.sub(r'[^a-z0-9 ]+',' ',s);return re.sub(r'\s+',' ',s).strip()

def canonical_source(v:str|None)->str:
    s=normalize_text(v)
    s=re.sub(r'^the\s+','',s)
    s=re.sub(r'\.(com|org|net)$','',s)
    return re.sub(r'[^a-z0-9]+','',s)

def normalize_url(v:str|None)->str:
    raw=(v or '').strip()
    if not raw:return ''
    try:
        p=urllib.parse.urlsplit(raw)
        if p.scheme not in {'http','https'}:return ''
        pairs=urllib.parse.parse_qsl(p.query,keep_blank_values=True)
        q=urllib.parse.urlencode([(k,v) for k,v in pairs if k.lower() not in DROP_Q])
        return urllib.parse.urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),q,'')).lower()
    except Exception:return raw.rstrip('/').lower()

def item_identity(i:ET.Element)->dict[str,str]:
    title=(i.findtext('title') or '').strip();source=(i.findtext('source') or '').strip();url=(i.findtext('link') or '').strip()
    return {'title':title,'title_key':canonical_title(title),'source':source,'source_key':canonical_source(source),'url':url,'url_key':normalize_url(url),'category':normalize_text(i.findtext('category'))}

def pool_identity(r:dict[str,Any])->dict[str,str]:
    return {'title_key':canonical_title(r.get('title_key') or r.get('title')),'source_key':canonical_source(r.get('source_key') or r.get('source')),'url_key':normalize_url(r.get('url_key') or r.get('url')),'category':normalize_text(r.get('category'))}

def same_article(item:dict[str,str],record:dict[str,Any],*,require_category:bool)->bool:
    r=pool_identity(record)
    if require_category and r['category'] and item['category']!=r['category']:return False
    if r['url_key'] and item['url_key'] and r['url_key']==item['url_key']:return True
    if r['title_key'] and r['title_key']==item['title_key']:
        # A canonical title match is strong enough when sources are equivalent or one source is absent.
        return not r['source_key'] or not item['source_key'] or r['source_key']==item['source_key']
    return False

def matched_reason(item,pools):
    for r in pools.get('D',[]):
        if same_article(item,r,require_category=False):return 'D'
    for reason in ('NR','NW'):
        for r in pools.get(reason,[]):
            if same_article(item,r,require_category=True):return reason
    return None

def dedupe_pool(rows:list[dict[str,Any]],reason:str)->list[dict[str,Any]]:
    out=[];seen=set()
    for r in rows:
        x=pool_identity(r)
        key=(x['url_key'] or x['title_key'],x['source_key'],'' if reason=='D' else x['category'])
        if not key[0] or key in seen:continue
        seen.add(key);out.append(r)
    return out

def fetch_pools(api_url:str,timeout:float=15.0):
    req=urllib.request.Request(api_url,headers={'Accept':'application/json','User-Agent':'underreported-feed/1.0'})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        if resp.status!=200:raise RuntimeError(f'feedback API returned HTTP {resp.status}')
        payload=json.loads(resp.read().decode('utf-8'))
    raw=payload.get('pools') if isinstance(payload,dict) else None
    if not isinstance(raw,dict):raise RuntimeError('feedback API payload has no pools object')
    return {reason:dedupe_pool([x for x in raw.get(reason,[]) if isinstance(x,dict)],reason) for reason in REASONS}

def apply_pools(feed_path:Path,pools):
    tree=ET.parse(feed_path);root=tree.getroot();channel=root.find('channel') if root.tag.lower()=='rss' else None;parent=channel if channel is not None else root
    removed=[]
    for i in list(parent.findall('item')):
        ident=item_identity(i);reason=matched_reason(ident,pools)
        if not reason:continue
        parent.remove(i);removed.append({'reason':reason,'category':ident['category'],'title':ident['title'],'url':ident['url'],'source':ident['source']})
    if removed:
        try:ET.indent(tree,space='  ')
        except AttributeError:pass
        tree.write(feed_path,encoding='utf-8',xml_declaration=True)
    return {'poolCounts':{r:len(pools.get(r,[])) for r in REASONS},'removedCount':len(removed),'removedByReason':{r:sum(1 for x in removed if x['reason']==r) for r in REASONS},'removed':removed}

def main():
    p=argparse.ArgumentParser();p.add_argument('--feed',default='News');p.add_argument('--api',default=DEFAULT_API);p.add_argument('--require-remote',action='store_true');p.add_argument('--report',default='/tmp/feedback-pool-report.json');a=p.parse_args()
    try:pools=fetch_pools(a.api)
    except (OSError,urllib.error.URLError,urllib.error.HTTPError,ValueError,RuntimeError,json.JSONDecodeError) as exc:
        if a.require_remote:print(f'Feedback pool fetch failed: {exc}',file=sys.stderr);return 1
        print(f'Feedback pool fetch failed: {exc}; continuing without suppression.',file=sys.stderr);pools={r:[] for r in REASONS}
    report=apply_pools(Path(a.feed),pools);Path(a.report).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Persistent feedback pools:',report['poolCounts']);print('Removed by feedback:',report['removedByReason']);return 0
if __name__=='__main__':raise SystemExit(main())
