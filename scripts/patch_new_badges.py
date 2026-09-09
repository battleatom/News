from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
marker='<script id="new-badge-expiry-v1">'
while marker in s:
    a=s.find(marker); b=s.find('</script>',a)
    if b<0: break
    s=s[:a]+s[b+9:]

script=r'''<script id="new-badge-expiry-v1">
function decorateNewBadges(){
 document.querySelectorAll('.news-item').forEach(card=>{
   const existing=card.querySelector('.new-badge');
   const meta=card.querySelector('.meta span');
   const fresh=meta&&isFresh(meta.textContent);
   if(existing&&!fresh) existing.remove();
   if(!existing&&fresh){const h=card.querySelector('h3');if(h){const badge=document.createElement('span');badge.className='new-badge';badge.textContent='NEW';h.appendChild(badge);}}
 });
}
setInterval(()=>{if(typeof decorateNewBadges==='function')decorateNewBadges();},60*1000);
</script>'''
s=s.replace('</body>',script+'\n</body>',1)
p.write_text(s,encoding='utf-8')
print('NEW badges now expire automatically after one hour.')
