(()=>{
  const decode=value=>{
    const box=document.createElement('textarea');
    box.innerHTML=String(value??'');
    return box.value;
  };
  const plain=value=>{
    let text=String(value??'');
    for(let i=0;i<3;i++){
      const before=text;
      text=decode(text).replace(/<\/?[a-z][^>]*>/gi,' ');
      if(text===before)break;
    }
    return text.replace(/\s+/g,' ').trim();
  };
  const cleanNode=node=>{
    if(!(node instanceof HTMLElement))return;
    const raw=node.textContent||'';
    if(!/[<>]|&(?:lt|gt|amp|quot|#\d+|#x[0-9a-f]+);/i.test(raw))return;
    const cleaned=plain(raw);
    if(cleaned!==raw.trim())node.textContent=cleaned;
  };
  const clean=root=>{
    if(!(root instanceof Element||root instanceof Document))return;
    if(root.matches?.('.story-summary,.story-why span'))cleanNode(root);
    root.querySelectorAll?.('.story-summary,.story-why span').forEach(cleanNode);
  };
  const feed=document.getElementById('feed');
  if(!feed)return;
  clean(feed);
  new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{
    if(node.nodeType===1)clean(node);
  }))).observe(feed,{childList:true,subtree:true});
  const style=document.createElement('style');
  style.textContent='.story-summary,.story-why span,.story-card h3{overflow-wrap:anywhere;word-break:break-word;min-width:0}';
  document.head.appendChild(style);
})();
