#!/usr/bin/env python3
import importlib.util,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
cluster=load('cluster',Path('scripts/cluster_related_coverage.py'));why=load('why',Path('scripts/update_why_matters.py'))
def item(cat,title,source,desc,link):
 x=ET.Element('item')
 for tag,val in [('title',title),('link',link),('description',desc),('pubDate','Fri, 11 Sep 2026 12:00:00 GMT'),('source',source),('category',cat)]:ET.SubElement(x,tag).text=val
 return x
a=item('presidential','Trump proposes $5,000 payments to supporters','Reuters','The proposal describes a $5,000 payment tied to the same support program.','a')
b=item('presidential','$5,000 support payment proposal draws questions','AP News','Officials discussed eligibility for the $5,000 support payment proposal.','b')
c=item('presidential','Trump meets technology executives','BBC','The president met technology executives about a separate issue.','c')
assert cluster.same_event(a,b);assert not cluster.same_event(a,c)
d=item('us','Nation marks 9/11 anniversary at memorial ceremonies','CBS News','Families gather for remembrance events marking 9/11.','d')
e=item('us','Memorial events commemorate 9/11 across the country','NBC News','Commemoration ceremonies and tributes mark the 9/11 anniversary.','e')
assert cluster.same_event(d,e)
w=item('us','Agency issues update','Reuters','The final paraphrased brief says Medicaid benefits and hospital access may change.','w')
assert 'health' in why.why_for(w).lower() or 'care' in why.why_for(w).lower()
loc=(ROOT/'scripts/patch_legislation_location.py').read_text();assert 'coverageItem(' not in loc and 'stateCoverage(' not in loc;assert 'Only official legislative records appear as cards' in loc
full=(ROOT/'scripts/patch_full_why_matters.py').read_text();assert '-webkit-line-clamp:unset' in full and 'overflow:visible' in full
print('Feed quality regression tests passed.')
