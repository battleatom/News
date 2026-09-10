from pathlib import Path

P=Path('scripts/update_news.py')
s=P.read_text(encoding='utf-8')

if 'PRESIDENTIAL_DIRECT_TERMS =' not in s:
    anchor="US_CONTEXT_TERMS = ('united states', 'u.s.', 'us ', 'america', 'american', 'washington dc', 'washington, d.c.', 'new mexico', 'farmington', 'san juan county', 'arizona', 'colorado', 'utah', 'nevada', 'texas', 'california', 'oregon', 'washington state', 'new york', 'florida', 'georgia', 'illinois', 'ohio', 'congress', 'senate', 'house of representatives', 'white house', 'pentagon', 'supreme court')\n"
    block='''\nPRESIDENTIAL_DIRECT_TERMS = (\n    "donald trump", "president trump", "trump", "white house",\n    "u.s. president", "us president", "president of the united states",\n    "oval office", "trump administration", "vice president vance",\n    "jd vance", "j.d. vance", "karoline leavitt", "white house press secretary",\n)\nPRESIDENTIAL_ACTION_TERMS = (\n    "executive order", "presidential action", "presidential memorandum",\n    "presidential proclamation", "cabinet meeting", "administration official",\n)\n\ndef is_us_presidential_story(title, description=""):\n    title_text = f" {clean(title).lower()} "\n    full_text = f" {clean(title).lower()} {clean(description).lower()} "\n    if any(term in title_text for term in PRESIDENTIAL_DIRECT_TERMS):\n        return True\n    us_context = any(term in full_text for term in ("united states", "u.s.", "american", "white house"))\n    return us_context and any(term in full_text for term in PRESIDENTIAL_ACTION_TERMS)\n\n'''
    if anchor not in s:
        raise SystemExit('Could not locate US context constants for presidential filter')
    s=s.replace(anchor,anchor+block,1)

needle='''        if not source_is_trusted(source):\n            continue\n        item_category = "world" if should_route_to_world(title, desc, category) else category\n'''
replacement='''        if not source_is_trusted(source):\n            continue\n        if category == "presidential" and not is_us_presidential_story(title, desc):\n            continue\n        item_category = "world" if should_route_to_world(title, desc, category) else category\n'''
if needle in s:
    s=s.replace(needle,replacement,1)
elif 'category == "presidential" and not is_us_presidential_story' not in s:
    raise SystemExit('Could not install presidential parser gate')

P.write_text(s,encoding='utf-8')
print('Presidential collector now requires an explicit U.S. presidency / White House signal.')
