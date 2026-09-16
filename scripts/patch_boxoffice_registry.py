from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')
old = """  render=locationAwareRender;
  if(previousCanonicalRender){
    canonicalRender=function(items){
      if(active==='boxoffice') return locationAwareRender(items);
      return previousCanonicalRender(items);
    };
  }
"""
new = """  window.__categoryRenderers=window.__categoryRenderers||{};
  window.__categoryRenderers.boxoffice=locationAwareRender;
"""
if old not in s:
    # Idempotent builds may already contain the normalized registry form.
    if new in s:
        print('Box Office is already registered through the canonical category renderer registry.')
    else:
        raise SystemExit('Expected Box Office canonical wrapper was not found; refusing nondeterministic cleanup')
else:
    s = s.replace(old, new, 1)
    P.write_text(s, encoding='utf-8')
    print('Registered Box Office through canonical category renderer registry; removed duplicate canonicalRender wrapper.')
