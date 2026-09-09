from pathlib import Path

P = Path('index.html')

# The canonical page script intentionally keeps state in top-level `let` bindings.
# Those bindings are not properties of window, but several independent UI modules
# (the timer, stats panel, and related-coverage decorator) need a shared public bridge.
# Define accessors instead of copying the values so both sides always see the same state.
BRIDGE = r'''<script id="shared-page-state-bridge-v1">
(function(){
  'use strict';
  function bridge(name){
    try{
      if(typeof window[name] === 'undefined'){
        Object.defineProperty(window,name,{configurable:true,enumerable:false,get:function(){
          try{return eval(name)}catch(e){return undefined}
        },set:function(v){
          try{eval(name+' = v')}catch(e){}
        }});
      }
    }catch(e){console.warn('State bridge unavailable for',name,e)}
  }
  ['allItems','lastSuccessfulPull','nextScheduledPull','pullInProgress'].forEach(bridge);
})();
</script>'''

s = P.read_text(encoding='utf-8')
marker = '<script id="shared-page-state-bridge-v1">'
while marker in s:
    a = s.find(marker)
    b = s.find('</script>', a)
    if b < 0:
        break
    s = s[:a] + s[b + 9:]

if '</body>' not in s:
    raise SystemExit('Missing </body> in index.html')
s = s.replace('</body>', BRIDGE + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Installed shared page-state bridge for timer, stats, bookmarks, and related coverage.')