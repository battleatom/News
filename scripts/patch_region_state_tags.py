from pathlib import Path
import re

P=Path('scripts/update_news.py')
s=P.read_text(encoding='utf-8')

if 'def region_query_state(' not in s:
    helper = '''\nUS_STATE_NAMES = {\n    'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming'\n}\n\ndef region_query_state(query):\n    candidate=re.sub(r'\\s+news$', '', str(query), flags=re.I).strip()\n    if candidate.lower()=='washington state': candidate='Washington'\n    return candidate if candidate in US_STATE_NAMES else ''\n\n'''
    anchor='MAX_AGE_HOURS = 48\n'
    if anchor not in s: raise SystemExit('Could not locate collector constants')
    s=s.replace(anchor,anchor+helper,1)

# Canonicalize the regional tagging block so repeated preview builds cannot stack
# duplicate state assignments.
s=re.sub(
    r'(\s+for item in batch:\n\s+item\["region"\] = region_name\n)(?:\s+item\["state"\] = region_query_state\(region_query\)\n)*',
    r'\1                                item["state"] = region_query_state(region_query)\n',
    s,
    count=1,
)
if 'item["state"] = region_query_state(region_query)' not in s:
    raise SystemExit('Could not tag regional items with state')

needle='f\'<region>{xml_escape(item.get("region", ""))}</region>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\''
replacement='f\'<region>{xml_escape(item.get("region", ""))}</region>\', f\'<state>{xml_escape(item.get("state", ""))}</state>\', f\'<whyMatters>{xml_escape(item.get("whyMatters", ""))}</whyMatters>\''
if needle in s:
    s=s.replace(needle,replacement,1)
elif 'f\'<state>{xml_escape(item.get("state", ""))}</state>\'' not in s:
    raise SystemExit('Could not add state element to RSS output')

# A broad region used to retain only 30 stories total. With 5-10 states in one
# region, a busy state could wind up with only 1-2 retained stories. Preserve up
# to eight distinct stories per tagged state first, then fill the remaining
# regional pool by recency. This gives the merged State view enough depth without
# duplicating articles.
if 'def select_region_stories(' not in s:
    helper='''\n\ndef select_region_stories(items, per_state=8, limit=80):\n    ranked = sorted(items, key=lambda x: x["published"], reverse=True)\n    selected, seen = [], set()\n    states = []\n    for item in ranked:\n        state = (item.get("state") or "").strip()\n        if state and state not in states:\n            states.append(state)\n    for state in states:\n        state_items = [item for item in ranked if (item.get("state") or "").strip() == state]\n        for item in select_category_stories(state_items, limit=per_state):\n            k = key(item)\n            if not k or k in seen:\n                continue\n            selected.append(item); seen.add(k)\n            if len(selected) >= limit:\n                return selected\n    for item in ranked:\n        k = key(item)\n        if not k or k in seen:\n            continue\n        selected.append(item); seen.add(k)\n        if len(selected) >= limit:\n            break\n    return selected\n'''
    anchor='\ndef why_matters(item):\n'
    if anchor not in s: raise SystemExit('Could not locate region selector insertion point')
    s=s.replace(anchor,helper+anchor,1)

old='''                region_items = [x for x in category_items if x.get("region") == region_name]\n                selected_by_category[category].extend(select_category_stories(region_items, limit=30))'''
new='''                region_items = [x for x in category_items if x.get("region") == region_name]\n                selected_by_category[category].extend(select_region_stories(region_items, per_state=8, limit=80))'''
if old in s:
    s=s.replace(old,new,1)
elif 'select_region_stories(region_items, per_state=8, limit=80)' not in s:
    raise SystemExit('Could not install deeper per-state regional selection')

P.write_text(s,encoding='utf-8')
print('Regional collector tags state and preserves up to eight stories per state before regional fill.')
