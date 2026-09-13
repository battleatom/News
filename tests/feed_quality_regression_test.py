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

cu=item('us','President Jordan offers $5,000 payments if budget measure passes','Fox News','President Jordan described a $5,000 payment proposal tied to passage of the measure.','cu')
cp=item('presidential','$5,000 payment proposal from President Jordan faces questions','Reuters','The same $5,000 payment proposal from President Jordan is being reviewed after the announcement.','cp')
assert cluster.event_match(cu,cp,allow_cross_tab=True)
assert cluster.canonical_category([cu,cp])=='presidential'
assert cluster.primary_score(cp)>cluster.primary_score(cu)

other=item('presidential','President Jordan meets technology executives','CNN','The president met technology executives about a separate software policy discussion.','other')
assert not cluster.event_match(cp,other,allow_cross_tab=True)

different_amount=item('presidential','President Jordan gave $45,000 in cash gifts to aides','Reuters','President Jordan reported $45,000 in separate personal cash gifts.','different')
assert not cluster.event_match(cu,different_amount,allow_cross_tab=True)

d=item('us','Apollo 11 anniversary marked at July 20 memorial ceremony','CBS News','Families gather July 20 for Apollo 11 remembrance events marking the anniversary.','d')
e=item('us','July 20 events commemorate Apollo 11 anniversary','NBC News','Commemoration ceremonies and tributes mark Apollo 11 on July 20.','e')
assert cluster.same_event(d,e)

f=item('nm','Chatbot invented fake police testimony in murder appeal, state high court says - Finance Daily','Finance Daily','By Staff WASHINGTON Sept 11 - A defense lawyer appealing a murder conviction submitted a brief containing invented police testimony.','f')
g=item('nm','Chatbot invented fake police testimony in murder appeal, state high court says - Wire Service','Reuters','By Staff WASHINGTON Sept 11 - A defense lawyer appealing a murder conviction submitted a brief containing invented police testimony.','g')
assert vf.syndicated_copy(f,g);assert cluster.same_event(f,g)

h=item('us','Aerospace maker highlights its U.S. factories after trade dispute','Reuters','The manufacturer described its domestic footprint after a trade dispute.','h')
i=item('us','Country announces broad food tariffs in separate trade action','NPR','Officials announced tariffs on agricultural imports under a different measure.','i')
assert not cluster.same_event(h,i)

assert vf.should_reroute('us',{'action':'reroute','category':'presidential','confidence':0.74})
assert not vf.should_reroute('world',{'action':'reroute','category':'us','confidence':0.74})

w=item('us','Agency issues update','Reuters','The final paraphrased brief says Medicaid benefits and hospital access may change.','w')
assert 'health' in why.why_for(w).lower() or 'care' in why.why_for(w).lower()

# Story-specific Why It Matters: named subject/focus must survive into the final text.
tech_gpu=item('technology','Nvidia unveils RTX 6090 GPU at $999','The Verge','Nvidia outlined a new GPU aimed at PC buyers.','tech-gpu')
tech_gpu_why=why.why_for(tech_gpu)
assert 'Nvidia' in tech_gpu_why and 'RTX 6090' in tech_gpu_why
assert any(term in tech_gpu_why.lower() for term in ('performance','price','hardware'))

tech_other=item('technology','AMD unveils Radeon X990 GPU at $799','Ars Technica','AMD outlined a different GPU for PC buyers.','tech-amd')
assert why.why_for(tech_gpu)!=why.why_for(tech_other)

tech_unclear=item('technology','Acme discusses technology strategy','Reuters','Executives outlined plans without announcing a product, price, security event, or policy change.','tech-unclear')
tech_unclear_why=why.why_for(tech_unclear)
assert 'Acme' in tech_unclear_why and 'does not yet establish a measurable downstream effect' in tech_unclear_why

game_delay=item('gaming','Grand Theft Auto VI delayed into 2027','IGN','Rockstar delayed the release after development changes.','game-delay')
game_delay_why=why.why_for(game_delay)
assert 'Grand Theft Auto VI' in game_delay_why and '2027' in game_delay_why
assert 'release calendar' in game_delay_why.lower()

game_price=item('gaming','Xbox Game Pass Ultimate price increases to $24.99','GameSpot','Microsoft announced a Game Pass subscription price increase for players.','game-price')
game_price_why=why.why_for(game_price)
assert 'Xbox Game Pass Ultimate' in game_price_why and '$24.99' in game_price_why
assert 'subscriber' in game_price_why.lower() and ('cost' in game_price_why.lower() or 'value' in game_price_why.lower())

ent_personal=item('entertainment','Actor and partner announce pregnancy','People','The couple announced they are expecting a baby.','ent-personal')
ent_personal_why=why.why_for(ent_personal)
assert 'Actor and partner' in ent_personal_why and 'personal celebrity update' in ent_personal_why.lower()
assert 'does not establish a broader entertainment-industry consequence' in ent_personal_why

ent_legal=item('entertainment','Zendaya sued over film contract dispute','Variety','The lawsuit concerns a film contract and an active production.','ent-legal')
ent_legal_why=why.why_for(ent_legal)
assert 'Zendaya' in ent_legal_why and 'contract' in ent_legal_why.lower()
ctx=why.why_context(ent_legal)
assert ctx['subject']=='Zendaya' and ctx['event']=='legal dispute or investigation'
assert ctx['affected'] and ctx['consequence'] and ctx['confidence']

loc=(ROOT/'scripts/patch_legislation_location.py').read_text();assert 'coverageItem(' not in loc and 'stateCoverage(' not in loc;assert 'Only official legislative records appear as cards' in loc
full=(ROOT/'scripts/patch_full_why_matters.py').read_text();assert '-webkit-line-clamp:unset' in full and 'overflow:visible' in full
brief_css=(ROOT/'styles/content-briefs.css').read_text()
assert '-webkit-line-clamp' not in brief_css and 'overflow:hidden' not in brief_css and 'overflow:visible' in brief_css
print('Feed quality regression tests passed.')
