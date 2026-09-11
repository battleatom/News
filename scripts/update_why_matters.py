#!/usr/bin/env python3
"""Generate Why It Matters from the final paraphrased content brief."""
from pathlib import Path
import html,re,xml.etree.ElementTree as ET
NEWS=Path('News')
def clean(v):
 v=html.unescape(v or '');v=re.sub(r'<[^>]+>',' ',v);return re.sub(r'\s+',' ',v).strip()
def has(text,*terms):return any(re.search(r'\b'+re.escape(t)+r'\b',text,re.I) for t in terms)
def why_for(item):
 brief=clean(item.findtext('description'));title=clean(item.findtext('title'));cat=clean(item.findtext('category')).lower();text=f'{title} {brief}'.lower()
 # Most-specific domains come first so generic words such as "benefits" cannot
 # override the actual subject expressed by the final paraphrased brief.
 if has(text,'war','airstrike','missile','troops','ceasefire','invasion','attack'):impact='It may affect security, military operations, diplomacy, or civilians connected to the conflict.'
 elif has(text,'court','judge','ruling','lawsuit','appeal','injunction','law'):impact='It may affect legal rights, enforcement, government authority, or what happens next in the case or policy.'
 elif has(text,'recall','outbreak','hospital','medicaid','medicare','health','healthcare','safety'):impact='It may affect public health, access to care, consumer safety, or costs for people and institutions involved.'
 elif has(text,'payment','payments','check','checks','rebate','refund','payout','cash'):impact='It may affect eligibility, household finances, government spending, or the timing and rules of any proposed payment.'
 elif has(text,'election','elections','midterm','ballot','voting','campaign'):impact='It may affect election administration, campaign strategy, voter information, or the political debate around the issue.'
 elif has(text,'breach','hack','cybersecurity','privacy','surveillance','outage','ai','software'):impact='It may affect privacy, security, access to technology, users, or how the technology is regulated and deployed.'
 elif has(text,'wildfire','flood','hurricane','tornado','earthquake','drought','climate'):impact='It may affect public safety, infrastructure, property, emergency response, or environmental conditions.'
 elif cat=='nfl' or has(text,'nfl','quarterback','playoffs','touchdown'):impact='It may affect team availability, standings, roster decisions, or upcoming games.'
 elif cat in {'presidential','federal','us','world','nm','local','region'}:impact='It may affect public policy, government operations, communities, or people directly connected to the development.'
 else:impact='It may affect the people, organizations, services, or decisions directly connected to the development.'
 return 'Why it matters: '+impact
def main():
 tree=ET.parse(NEWS);items=tree.getroot().findall('.//item');updated=0
 for item in items:
  if clean(item.findtext('category')).lower()=='legislation':continue
  if not clean(item.findtext('description')):continue
  node=item.find('whyMatters')
  if node is None:node=ET.SubElement(item,'whyMatters')
  node.text=why_for(item);updated+=1
 tree.write(NEWS,encoding='utf-8',xml_declaration=True);print(f'Why It Matters: {updated} item(s) regenerated from final paraphrased briefs.')
if __name__=='__main__':main()
