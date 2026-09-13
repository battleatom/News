#!/usr/bin/env python3
"""Augment the collected feed with configured direct publisher RSS entries.

This is deliberately opportunistic: direct publisher RSS improves fidelity when healthy,
while Google News collection remains the fallback. A direct-feed outage never aborts the
news refresh.
"""
from __future__ import annotations
import email.utils, hashlib, html, json, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'source-registry.json'; FEED=ROOT/'News'; REPORT=ROOT/'direct-rss-report.json'
MAX_PER_SOURCE=8; MAX_AGE=timedelta(hours=48)
TRACK=('utm_','fbclid','gclid','mc_','ref','ref_','source')

def clean(v): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',v or ''))).strip()
def canon(url):
    try:
        p=urlsplit((url or '').strip()); host=p.netloc.lower().removeprefix('www.'); path=re.sub(r'/+$','',p.path) or '/'; keep=[]
        for k,v in parse_qsl(p.query,keep_blank_values=False):
            lk=k.lower()
            if any(lk==x or lk.startswith(x) for x in TRACK): continue
            keep.append((k,v))
        return urlunsplit(((p.scheme or 'https').lower(),host,path,urlencode(sorted(keep)) if keep else '',''))
    except Exception:return (url or '').strip().lower()
def parse_date(v):
    try:
        d=email.utils.parsedate_to_datetime(v or '')
        if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:return None
def atom_text(node,name):
    # Support RSS and Atom without external deps.
    x=node.find(name)
    if x is not None and x.text:return x.text
    for child in node:
        if child.tag.rsplit('}',1)[-1]==name:return child.text or ''
    return ''
def atom_link(node):
    direct=atom_text(node,'link')
    if direct:return direct
    for child in node:
        if child.tag.rsplit('}',1)[-1]=='link' and child.attrib.get('href'): return child.attrib['href']
    return ''
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'UnderreportedNews/5.1 (+RSS quality collector)'})
    with urllib.request.urlopen(req,timeout=12) as r:return r.read()
def entries(root):
    out=[]
    for n in root.iter():
        if n.tag.rsplit('}',1)[-1] in {'item','entry'}: out.append(n)
    return out
def add_item(channel,src,cat,e):
    title=clean(atom_text(e,'title')); link=atom_link(e).strip(); desc=clean(atom_text(e,'description') or atom_text(e,'summary') or atom_text(e,'content'))
    date_raw=atom_text(e,'pubDate') or atom_text(e,'published') or atom_text(e,'updated'); dt=parse_date(date_raw)
    if not title or not link:return None
    now=datetime.now(timezone.utc)
    if dt and (dt>now+timedelta(hours=2) or now-dt>MAX_AGE):return None
    i=ET.SubElement(channel,'item')
    ET.SubElement(i,'title').text=title; ET.SubElement(i,'link').text=link; ET.SubElement(i,'description').text=desc[:1800]
    ET.SubElement(i,'pubDate').text=email.utils.format_datetime(dt or now,usegmt=True); ET.SubElement(i,'source').text=src; ET.SubElement(i,'category').text=cat
    ET.SubElement(i,'resolvedPublisherUrl').text=link; ET.SubElement(i,'collectorSource').text='direct-rss'
    ET.SubElement(i,'guid',{'isPermaLink':'false'}).text=hashlib.sha1((src+'|'+canon(link)).encode()).hexdigest()
    return i

def run(feed=FEED,registry=REGISTRY,report=REPORT):
    cfg=json.loads(Path(registry).read_text(encoding='utf-8')); tree=ET.parse(feed); channel=tree.getroot().find('channel')
    if channel is None:raise SystemExit('Invalid News feed')
    existing_urls=set(); existing_titles=set()
    for i in channel.findall('item'):
        existing_urls.add(canon(i.findtext('resolvedPublisherUrl') or i.findtext('link') or '')); existing_titles.add(clean(i.findtext('title')).lower())
    rows=[]; added=0
    for s in cfg.get('sources',[]):
        url=s.get('directRss');
        if not url:continue
        row={'source':s.get('name'),'url':url,'status':'ok','added':0}
        try:
            root=ET.fromstring(fetch(url))
            for e in entries(root)[:40]:
                title=clean(atom_text(e,'title')).lower(); link=canon(atom_link(e))
                if not title or not link or title in existing_titles or link in existing_urls:continue
                item=add_item(channel,s['name'],s.get('defaultCategory') or s['scope'][0],e)
                if item is None:continue
                existing_titles.add(title); existing_urls.add(link); row['added']+=1; added+=1
                if row['added']>=MAX_PER_SOURCE:break
        except Exception as exc:
            row['status']='degraded'; row['error']=f'{type(exc).__name__}: {exc}'[:240]
        rows.append(row)
    tree.write(feed,encoding='utf-8',xml_declaration=True)
    out={'generatedAt':datetime.now(timezone.utc).isoformat(),'added':added,'sources':rows,'policy':'direct RSS is additive and failure-tolerant; discovery fallback remains enabled'}
    Path(report).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(f'Direct RSS: added {added} article(s) from {len(rows)} configured feed(s).')
    return out
if __name__=='__main__':run()
