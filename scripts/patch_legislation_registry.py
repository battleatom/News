from pathlib import Path

P=Path('scripts/patch_site_features.py')
s=P.read_text(encoding='utf-8')
old="['federal','🏛️ Federal Government','#ca8a04'],['nm','🏜️ New Mexico','#0f766e']"
new="['federal','🏛️ Federal Government','#ca8a04'],['legislation','📜 Laws & Legislation','#a16207'],['nm','🏜️ New Mexico','#0f766e']"
count=s.count(old)
if count:
    s=s.replace(old,new)
elif "['legislation','📜 Laws & Legislation','#a16207']" not in s:
    raise SystemExit('Could not insert legislation into canonical site sections')
P.write_text(s,encoding='utf-8')
print(f'Legislation is permanent in canonical tab registry ({count or "already patched"} section definitions updated).')
