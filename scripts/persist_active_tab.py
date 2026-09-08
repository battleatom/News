from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

old_state = "let allItems=[],active='top';"
new_state = "let allItems=[],active=localStorage.getItem('underreported-active-tab')||'top';"

if old_state in text:
    text = text.replace(old_state, new_state, 1)

old_click = "b.onclick=()=>{active=key;buildTabs();render(allItems)}"
new_click = "b.onclick=()=>{active=key;localStorage.setItem('underreported-active-tab',active);buildTabs();render(allItems)}"

if old_click in text:
    text = text.replace(old_click, new_click, 1)

path.write_text(text, encoding="utf-8")
print("Persisted the selected news tab across page refreshes.")
