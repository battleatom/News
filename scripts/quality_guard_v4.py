#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, re
from pathlib import Path
import xml.etree.ElementTree as ET

NEWS=Path('News'); BOX=Path('boxoffice.json')
US_STATES={'alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri','montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york','north carolina','north dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina','south dakota','tennessee','texas','utah','vermont','virginia','washington','west virginia','wisconsin','wyoming'}
STOP={'the','and','for','with','from','into','after','before','about','amid','during','this','that','says','said','new','news','latest','update','report','reports','white','house','world','federal','government'}
SPORTS=('football','basketball','baseball','soccer','nfl','nba','ncaa','game','match','quarterback','team usa','fiba')
SCIENCE=('science','research','study','space','climate','physics','biology','astronomy','nasa','scientist','researchers','laboratory')
CELEB=('actor','actress','singer','rapper','musician','celebrity','star','artist','director','comedian','model','tour','album','movie','film','television','tv')

def txt(n,t): return (n.findtext(t) or '').strip()
def setv(n,t,v):
    e=n.find(t)
    if e is None:e=ET.SubElement(n,t)
    e.text=v

def tokens(s): return {w for w in re.findall(r'[a-z0-9]+',s.lower()) if len(w)>=3 and w not in STOP}
def entities(s):
    out=set()
    for p in re.findall(r'\b[A-Z][A-Za-z0-9’\'\.-]+(?:\s+[A-Z][A-Za-z0-9’\'\.-]+){1,3}\b',s):
        q=p.lower()
        if q not in {'white house','united states','associated press','new york','los angeles'}: out.add(q)
    return out

def same_event(a,b):
    ta,tb=tokens(a),tokens(b)
    if not ta or not tb:return False
    sh=ta&tb; small=min(len(ta),len(tb)); jac=len(sh)/max(1,len(ta|tb))
    ea,eb=entities(a),entities(b)
    return (len(sh)>=3 and (jac>=.34 or len(sh)/small>=.60)) or (bool(ea&eb) and len(sh)>=2 and len(sh)/small>=.45)

def is_us_domestic(item):
    s=(txt(item,'state') or txt(item,'marketState')).lower()
    return s in US_STATES or s in {x[:2] for x in US_STATES}

def preserve_rss(item):
    d=txt(item,'description')
    if len(d)>=70 and 'publisher did not expose enough public article text' not in d.lower() and not txt(item,'rssDescription'):
        setv(item,'rssDescription',d)

def reroute(items):
    moved=0
    for i in items:
        cat=txt(i,'category').lower(); blob=' '.join([txt(i,'title'),txt(i,'description'),txt(i,'source')]).lower()
        if cat=='world' and is_us_domestic(i): setv(i,'category','us'); moved+=1
        elif cat=='federal' and any(k in blob for k in ('canada','canadian','ottawa','canadian federal')) and not any(k in blob for k in ('u.s.','united states','congress','white house')):
            setv(i,'category','world'); moved+=1
        elif cat=='technology' and any(k in blob for k in ('skyrim','playstation','xbox','nintendo','video game','gaming console')):
            setv(i,'category','gaming'); moved+=1
    return moved

def clean_related(items):
    removed=0
    for i in items:
        pt=txt(i,'title')
        for tag in ('relatedArticles','xRelated'):
            rel=i.find(tag)
            if rel is None: continue
            for a in list(rel):
                if not same_event(pt,txt(a,'title')):
                    rel.remove(a); removed+=1
    return removed

def x_valid(topic,item):
    title=txt(item,'title').lower(); blob=title+' '+txt(item,'description').lower()
    if topic=='World': return not is_us_domestic(item) and not any(k in blob for k in SPORTS)
    if topic=='Celebrities & Public Figures': return any(k in blob for k in CELEB) or bool(entities(txt(item,'title')))
    if topic=='Science': return any(k in blob for k in SCIENCE)
    return True

def candidate_for(topic,items,used):
    prefs={
      'World':lambda x:txt(x,'category')=='world' and not is_us_domestic(x) and not any(k in (txt(x,'title')+' '+txt(x,'description')).lower() for k in SPORTS),
      'Celebrities & Public Figures':lambda x:txt(x,'category')=='entertainment' and txt(x,'entertainmentSafety')!='dirty',
      'Science':lambda x:txt(x,'category') in {'technology','underreported','world'} and any(k in (txt(x,'title')+' '+txt(x,'description')).lower() for k in SCIENCE),
    }
    fn=prefs.get(topic)
    if not fn:return None
    for x in items:
        if txt(x,'category')!='x' and txt(x,'link') not in used and fn(x): return x
    return None

def make_x(src,topic):
    n=ET.Element('item')
    for tag in ('title','link','description','pubDate','source','imageUrl','whyMatters','resolvedPublisherUrl'):
        v=txt(src,tag)
        if v:setv(n,tag,v)
    setv(n,'category','x'); setv(n,'xTopic',topic); setv(n,'xSignal','Top public X conversation')
    setv(n,'xWhyTrending','This fixed topic slot is populated by the strongest current conversation supported by independent reporting.')
    setv(n,'xWhatPeopleAreSaying','People on X are discussing the underlying issue from different perspectives. The trend signal identifies the conversation; it does not establish that every claim circulating in it is true.')
    setv(n,'xConfirmed','Independent reporting confirms the underlying news event described above.')
    setv(n,'xUnconfirmed','Specific rumors, screenshots, accusations, and interpretations circulating on X are not treated as facts unless independently verified.')
    setv(n,'guid',hashlib.sha1((txt(src,'link')+'|x|'+topic).encode()).hexdigest())
    return n

def repair_x(root,items):
    channel=root.find('channel'); xs=[x for x in items if txt(x,'category')=='x']; used={txt(x,'link') for x in xs}; fixed=0
    for old in list(xs):
        topic=txt(old,'xTopic')
        if topic in {'World','Celebrities & Public Figures','Science'} and not x_valid(topic,old):
            cand=candidate_for(topic,items,used)
            if cand is not None:
                idx=list(channel).index(old); new=make_x(cand,topic); channel.remove(old); channel.insert(idx,new); used.add(txt(cand,'link')); fixed+=1
    return fixed

def clean_boxoffice():
    if not BOX.exists(): return 0
    try:data=json.loads(BOX.read_text(encoding='utf-8'))
    except Exception:return 0
    changed=0
    for m in data.get('movies',[]):
        d=str(m.get('description') or '').strip(); t=str(m.get('title') or '').lower()
        if not d:continue
        low=d.lower(); title_terms={w for w in re.findall(r'[a-z0-9]+',t) if len(w)>=4}
        movieish=any(k in low for k in (' film ',' movie ',' directed ',' stars ',' starring ',' sequel ',' screenplay '))
        overlap=any(w in low for w in title_terms)
        if low.startswith('running is a method of terrestrial locomotion') or (not movieish and not overlap and len(d)>180):
            m['description']=''; changed+=1
    if changed: BOX.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return changed

def useful_rss(row):
    d=txt(row,'rssDescription'); title=txt(row,'title').lower()
    if len(d)<80:return ''
    low=d.lower()
    if any(x in low for x in ('publisher did not expose enough public article text','accept cookies','subscribe','sign up')):return ''
    if len(tokens(d)&tokens(title))<1:return ''
    return d

def rss_brief(item):
    d=useful_rss(item)
    if not d:return ''
    d=re.sub(r'<[^>]+>',' ',d); d=re.sub(r'\s+',' ',d).strip()
    d=re.sub(r'\baccording to\b','based on',d,flags=re.I); d=re.sub(r'\bsaid\b','reported',d,flags=re.I); d=re.sub(r'\bwill\b','is expected to',d,flags=re.I)
    if len(d)>330:d=d[:327].rsplit(' ',1)[0]+'…'
    opener={'world':'International reporting indicates','us':'U.S. reporting indicates','federal':'Federal reporting indicates','presidential':'White House coverage indicates','nm':'New Mexico reporting indicates','local':'Local reporting indicates','technology':'Technology reporting indicates','gaming':'Gaming reporting indicates','military':'Defense reporting indicates','legislation':'Legislative reporting indicates'}.get(txt(item,'category').lower(),'Reporting indicates')
    return opener+' '+d[0].lower()+d[1:] if d else ''

def final_enhance(items):
    upgraded=whyfix=0
    for i in items:
        if txt(i,'briefSource')=='headline-fallback':
            b=rss_brief(i)
            if b:
                setv(i,'description',b); setv(i,'briefSource','rss-description'); upgraded+=1
        why=txt(i,'whyMatters'); title=txt(i,'title').lower(); cat=txt(i,'category').lower()
        if ('military or diplomatic' in why.lower() or 'regional security' in why.lower()) and cat=='legislation' and any(k in title for k in ('election','act','bill','rights','tax','school','pension','insurance')):
            setv(i,'whyMatters','Why it matters: This measure could change laws, funding, eligibility, regulation, or government responsibilities for the people and organizations it covers.'); whyfix+=1
        if ('military or diplomatic' in why.lower() or 'further escalation' in why.lower()) and cat not in {'military','world','presidential'} and 'wildfire' in title:
            setv(i,'whyMatters','Why it matters: It may affect public safety, emergency response, property, health, and long-term wildfire preparedness.'); whyfix+=1
    return upgraded,whyfix

def assert_clean(items):
    bad_world=[txt(i,'title') for i in items if txt(i,'category')=='world' and is_us_domestic(i)]
    bad_fed=[txt(i,'title') for i in items if txt(i,'category')=='federal' and 'canada' in (txt(i,'title')+' '+txt(i,'description')).lower()]
    if bad_world or bad_fed: raise SystemExit(f'Quality guard failed routing: world={bad_world[:3]} federal={bad_fed[:3]}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['pre','final'],default='pre'); a=ap.parse_args()
    tree=ET.parse(NEWS); root=tree.getroot(); items=list(root.findall('.//item'))
    if a.mode=='pre':
        for i in items: preserve_rss(i)
        moved=reroute(items); related=clean_related(items); xfix=repair_x(root,items); box=clean_boxoffice()
        tree.write(NEWS,encoding='utf-8',xml_declaration=True); items=list(root.findall('.//item')); assert_clean(items)
        print(f'Quality guard pre: rerouted={moved} unrelated-links-removed={related} x-repaired={xfix} boxoffice-cleared={box}')
    else:
        up,why=final_enhance(items); related=clean_related(items); tree.write(NEWS,encoding='utf-8',xml_declaration=True); assert_clean(items)
        print(f'Quality guard final: rss-brief-upgrades={up} why-matters-fixed={why} unrelated-links-removed={related}')
if __name__=='__main__': main()
