from pathlib import Path
import re

P=Path('scripts/update_news.py')
s=P.read_text(encoding='utf-8')

if 'def region_query_state(' not in s:
    helper = '''\nUS_STATE_NAMES = {\n    'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming'\n}\n\ndef region_query_state(query):\n    candidate=re.sub(r'\\s+news$', '', str(query), flags=re.I).strip()\n    if candidate.lower()=='washington state': candidate='Washington'\n    return candidate if candidate in US_STATE_NAMES else ''\n\n'''
    anchor='MAX_AGE_HOURS = 48\n'
    if anchor not in s: raise SystemExit('Could not locate collector constants')
    s=s.replace(anchor,anchor+helper,1)

old='''                            for item in batch:\n                                item["region"] = region_name\n'''
new='''                            for item in batch:\n                                item["region"] = region_name\n                                item["state"] = region_query_state(region_query)\n'''
if old in s:
    s=s.replace(old,new,1)
elif 'item["state"] = region_query_state(region_query)' not in s:
    raise SystemExit('Could not tag regional items with state')

needle='f\'<region>{xml_escape(item.get("region", ""))}</region>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\''
replacement='f\'<region>{xml_escape(item.get("region", ""))}</region>\', f\'<state>{xml_escape(item.get("state", ""))}</state>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\''
if needle in s:
    s=s.replace(needle,replacement,1)
elif 'f\'<state>{xml_escape(item.get("state", ""))}</state>\'' not in s:
    raise SystemExit('Could not add state element to RSS output')

P.write_text(s,encoding='utf-8')
print('Regional collector now tags each state-specific query result for location-aware State and Local tabs.')
