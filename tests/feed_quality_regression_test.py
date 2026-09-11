#!/usr/bin/env python3
import importlib.util,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
cluster=load('cluster',Path('scripts/cluster_related_coverage.py'));why=load('why',Path('scripts/update_why_matters.py'));vf=cluster.vf
def item(cat,title,source,desc,link,date='Fri, 11 Sep 2026 12:00:00 GMT'):
 x=ET.Element('item')
 for tag,val in [('title',title),('link',link),('description',desc),('pubDate',date),('source',source),('category',cat)]:ET.SubElement(x,tag).text=val
 return x

# Same-event amount + actor fingerprint, without topic-specific hard-coding.
a=item('presidential','Alex Morgan proposes $5,000 payments to supporters','Reuters','The proposal describes a $5,000 payment tied to the same support program.','a')
b=item('presidential','$5,000 support payment proposal from Morgan draws questions','AP News','Officials discussed eligibility for the $5,000 support payment proposal from Alex Morgan.','b')
c=item('presidential','Alex Morgan meets technology executives','BBC','The official met technology executives about a separate issue.','c')
assert cluster.same_event(a,b);assert not cluster.same_event(a,c)

# The same event entering U.S. and Presidential must canonicalize across tabs.
cu=item('us','President Jordan offers $5,000 payments if budget measure passes','Fox News','President Jordan described a $5,000 payment proposal tied to passage of the measure.','cu')
cp=item('presidential','$5,000 payment proposal from President Jordan faces questions','Reuters','The same $5,000 payment proposal from President Jordan is being reviewed after the announcement.','cp')
assert cluster.event_match(cu,cp,allow_cross_tab=True)
assert cluster.canonical_category([cu,cp])=='presidential'
assert cluster.primary_score(cp)>cluster.primary_score(cu)  # neutral wire-service preference

# An unrelated story about the same actor must not bridge into the payment event.
other=item('presidential','President Jordan meets technology executives','CNN','The president met technology executives about a separate software policy discussion.','other')
assert not cluster.event_match(cp,other,allow_cross_tab=True)

# Different explicit dollar amounts are separate events even with the same actor and cash language.
different_amount=item('presidential','President Jordan gave $45,000 in cash gifts to aides','Reuters','President Jordan reported $45,000 in separate personal cash gifts.','different')
assert not cluster.event_match(cu,different_amount,allow_cross_tab=True)

# Commemoration coverage needs a concrete shared event anchor, not just broad anniversary words.
d=item('us','Apollo 11 anniversary marked at July 20 memorial ceremony','CBS News','Families gather July 20 for Apollo 11 remembrance events marking the anniversary.','d')
e=item('us','July 20 events commemorate Apollo 11 anniversary','NBC News','Commemoration ceremonies and tributes mark Apollo 11 on July 20.','e')
assert cluster.same_event(d,e)

# Wire copy republished by another outlet must collapse even with a publisher suffix.
f=item('nm','Chatbot invented fake police testimony in murder appeal, state high court says - Finance Daily','Finance Daily','By Staff WASHINGTON Sept 11 - A defense lawyer appealing a murder conviction submitted a brief containing invented police testimony.','f')
g=item('nm','Chatbot invented fake police testimony in murder appeal, state high court says - Wire Service','Reuters','By Staff WASHINGTON Sept 11 - A defense lawyer appealing a murder conviction submitted a brief containing invented police testimony.','g')
assert vf.syndicated_copy(f,g);assert cluster.same_event(f,g)

# Related-but-distinct stories sharing only a broad actor/entity must remain separate.
h=item('us','Aerospace maker highlights its U.S. factories after trade dispute','Reuters','The manufacturer described its domestic footprint after a trade dispute.','h')
i=item('us','Country announces broad food tariffs in separate trade action','NPR','Officials announced tariffs on agricultural imports under a different measure.','i')
assert not cluster.same_event(h,i)

# More-specific destinations may route at the classifier's normal confidence,
# while equally broad destinations still require the stricter threshold.
assert vf.should_reroute('us',{'action':'reroute','category':'presidential','confidence':0.74})
assert not vf.should_reroute('world',{'action':'reroute','category':'us','confidence':0.74})

w=item('us','Agency issues update','Reuters','The final paraphrased brief says Medicaid benefits and hospital access may change.','w')
assert 'health' in why.why_for(w).lower() or 'care' in why.why_for(w).lower()
loc=(ROOT/'scripts/patch_legislation_location.py').read_text();assert 'coverageItem(' not in loc and 'stateCoverage(' not in loc;assert 'Only official legislative records appear as cards' in loc
full=(ROOT/'scripts/patch_full_why_matters.py').read_text();assert '-webkit-line-clamp:unset' in full and 'overflow:visible' in full
print('Feed quality regression tests passed.')
