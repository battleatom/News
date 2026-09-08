from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")

# Make the Region tab respond immediately instead of waiting on browser
# geolocation. Detection can still refine the region in the background.
old = "b.onclick=async()=>{active=key;localStorage.setItem('underreported-active-tab',active);buildTabs();if(key==='region')await detectUserRegion();render(allItems)};"
new = "b.onclick=()=>{active=key;localStorage.setItem('underreported-active-tab',active);buildTabs();render(allItems);if(key==='region')detectUserRegion().then(()=>{if(active==='region')render(allItems)}).catch(()=>{});};"
if old not in text:
    raise SystemExit("Region tab click handler not found")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Fixed Region tab to render immediately and detect location asynchronously.")
