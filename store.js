export const PAGE_SIZE=6;
const BOOKMARK_KEY="underreported-v6-bookmarks";
const ACTIVE_TAB_KEY="underreported-v6-active-tab";
const SEEN_STORIES_KEY="underreported-v6-seen-stories";
const UNDERREPORTED_SORTS=new Set(["signal","newest","oldest","most-sources","least-sources"]);
const X_SLOTS=[
  ["x-health","health"],
  ["x-technology","technology ai"],
  ["x-celebrities","celebrities public figures celebrity public figures"],
  ["x-world","world"],
  ["x-politics","politics government"],
  ["x-entertainment","entertainment"],
  ["x-sports","sports"],
  ["x-business","business economy"],
  ["x-gaming","gaming"],
  ["x-science","science"]
];
function readBookmarks(){try{return JSON.parse(localStorage.getItem(BOOKMARK_KEY)||"[]")}catch{return[]}}
function writeBookmarks(rows){try{localStorage.setItem(BOOKMARK_KEY,JSON.stringify(rows))}catch{}}
function readActiveTab(){try{return localStorage.getItem(ACTIVE_TAB_KEY)||"top"}catch{return"top"}}
function writeActiveTab(category){try{localStorage.setItem(ACTIVE_TAB_KEY,category)}catch{}}
function readSeenStories(){try{return new Set(JSON.parse(localStorage.getItem(SEEN_STORIES_KEY)||"[]"))}catch{return new Set()}}
function writeSeenStories(ids){try{localStorage.setItem(SEEN_STORIES_KEY,JSON.stringify([...ids].slice(-5000)))}catch{}}
function feedIds(feed){const ids=[];for(const category of Object.keys(feed?.categories||{})){for(const story of [...(feed?.stories?.[category]||[]),...(feed?.reserves?.[category]||[])])if(story?.id)ids.push(story.id)}return ids}
function norm(value){return String(value||"").toLowerCase().replace(/[^a-z0-9]+/g," ").replace(/\s+/g," ").trim()}
function suppressed(story,pools,category){const url=norm(story.url),title=norm(story.title),source=norm(story.source);const same=(record,requireCategory)=>{if(!record||record.serverCount)return false;if(requireCategory&&norm(record.category||record.tab)!==norm(category))return false;const recordUrl=norm(record.url_key||record.urlKey||record.url);if(recordUrl&&url&&recordUrl===url)return true;const recordTitle=norm(record.title_key||record.titleKey||record.title),recordSource=norm(record.source_key||record.sourceKey||record.source);return Boolean(recordTitle&&recordSource&&recordTitle===title&&recordSource===source)};return(pools.get("D")||[]).some(record=>same(record,false))||["NR","NW"].some(reason=>(pools.get(reason)||[]).some(record=>same(record,true)))}
function xSlotId(story,index){
  const direct=String(story?.source_id||story?.sourceId||story?.x_slot||story?.xSlot||"").trim().toLowerCase().replace(/_/g,"-");
  if(direct){
    for(const[id]of X_SLOTS){
      if(direct===id||direct.startsWith(`${id}-`))return id;
    }
  }
  const topic=norm(story?.x_topic||story?.xTopic||story?.topic||story?.slot||"");
  if(topic){
    for(const[id,aliases]of X_SLOTS){
      const terms=aliases.split(" ");
      if(terms.some(term=>term.length>3&&topic.includes(term)))return id;
    }
  }
  const text=norm(`${story?.title||""} ${story?.summary||""}`);
  if(text){
    for(const[id,aliases]of X_SLOTS){
      const terms=aliases.split(" ").filter(term=>term.length>3);
      if(terms.some(term=>text.includes(term)))return id;
    }
  }
  return X_SLOTS[index%X_SLOTS.length][0];
}
function normalizeXPool(rows){
  return rows.map((story,index)=>{
    const source_id=xSlotId(story,index);
    return story?.source_id===source_id?story:{...story,source_id};
  });
}
export class Store{
  constructor(){this.feed=null;this.nfl={games:[],error:""};this.nflStandings={children:[],error:""};this.boxoffice={movies:[],error:""};this.markets={markets:[],error:""};this.status={};this.active=readActiveTab();this.visible=new Map();this.location=null;this.suppressed=new Map([["D",[]],["NR",[]],["NW",[]]]);this.bookmarks=readBookmarks();this.newIds=new Set();this.seenIds=readSeenStories();this.selectedNfl="";this.underreportedSort="signal"}
  setFeed(feed){const incoming=new Set(feedIds(feed));if(this.feed){const previous=new Set(feedIds(this.feed));this.newIds=new Set([...incoming].filter(id=>!previous.has(id)))}else if(this.seenIds.size){this.newIds=new Set([...incoming].filter(id=>!this.seenIds.has(id)))}else{this.newIds=new Set()}this.feed=feed;for(const id of incoming)this.seenIds.add(id);writeSeenStories(this.seenIds);if(!feed?.categories?.[this.active]&&!["bookmarks","admin"].includes(this.active)){this.active=Object.keys(feed?.categories||{})[0]||"top";writeActiveTab(this.active)}}
  setActive(category){if(["bookmarks","admin"].includes(category)||this.feed?.categories?.[category]){this.active=category;writeActiveTab(category)}if(!this.visible.has(category))this.visible.set(category,PAGE_SIZE)}
  shown(category=this.active){return this.visible.get(category)||PAGE_SIZE}
  loadMore(category=this.active,amount=PAGE_SIZE){this.visible.set(category,this.shown(category)+amount)}
  resetPage(category=this.active){this.visible.set(category,PAGE_SIZE)}
  setUnderreportedSort(value){if(!UNDERREPORTED_SORTS.has(value))return;this.underreportedSort=value;this.resetPage("underreported")}
  rawCategoryPool(category){return[...(this.feed?.stories?.[category]||[]),...(this.feed?.reserves?.[category]||[])]}
  categoryStories(category=this.active){if(category==="bookmarks")return this.bookmarks;if(category==="admin")return[];let rows=this.rawCategoryPool(category);if(category==="x"){rows=normalizeXPool(rows);const selected=[];for(const[id]of X_SLOTS){const replacement=rows.find(story=>story.source_id===id&&!suppressed(story,this.suppressed,category));if(replacement)selected.push(replacement)}return selected}rows=rows.filter(story=>!suppressed(story,this.suppressed,category));return rows}
  allStories(){return Object.keys(this.feed?.categories||{}).flatMap(category=>this.categoryStories(category))}
  bookmarkIds(){return new Set(this.bookmarks.map(row=>row.id))}
  isBookmarked(id){return this.bookmarks.some(row=>row.id===id)}
  toggleBookmark(story){const i=this.bookmarks.findIndex(row=>row.id===story.id);let saved;if(i>=0){this.bookmarks.splice(i,1);saved=false}else{this.bookmarks.unshift({...story,bookmarked_at:new Date().toISOString()});saved=true}writeBookmarks(this.bookmarks);return saved}
  storyById(id){for(const category of Object.keys(this.feed?.categories||{})){const story=this.rawCategoryPool(category).find(row=>row.id===id);if(story)return story}return this.bookmarks.find(row=>row.id===id)||null}
}
