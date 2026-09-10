from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Always start on Top while the page is wiring its renderers. Remember the saved
# tab separately and restore it only after the final runtime setup is complete.
saved_expr = "localStorage.getItem('underreported-active-tab')||'top'"
state_variants = (
    "let allItems=[],active='top';",
    "var allItems=[],active='top';",
    f"let allItems=[],active={saved_expr};",
    f"var allItems=[],active={saved_expr};",
)
replacement = f"let allItems=[],active='top';window.__pendingActiveTab={saved_expr};"
replaced = False
for old in state_variants:
    if old in text:
        text = text.replace(old, replacement, 1)
        replaced = True
        break
if not replaced and "window.__pendingActiveTab=" not in text:
    raise SystemExit('Could not normalize active-tab initialization')

old_click = "b.onclick=()=>{active=key;buildTabs();render(allItems)}"
new_click = "b.onclick=()=>{active=key;localStorage.setItem('underreported-active-tab',active);buildTabs();render(allItems)}"
if old_click in text:
    text = text.replace(old_click, new_click, 1)

path.write_text(text, encoding="utf-8")
print("Normalized persisted-tab startup: Top first, saved tab restored after runtime initialization.")
