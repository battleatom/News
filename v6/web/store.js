export const PAGE_SIZE=20;
const BOOKMARK_KEY="underreported-v6-bookmarks";
const ACTIVE_TAB_KEY="underreported-v6-active-tab";
const UNDERREPORTED_SORTS=new Set(["signal","newest","oldest","most-sources","least-sources"]);
function readBookmarks(){try{return JSON.parse(localStorage.getItem(BOOKMARK_KEY)||"[]")}catch{return[]}}
function writeBookmarks(rows){try{localStorage.setItem(BOOKMARK_KEY,JSON.stringify(rows))}catch{}}
function readActiveTab(){try{return localStorage.getItem(ACTIVE_TAB_KEY)||"top"}catch{return"top"}}
function writeActiveTab(category){try{localStorage.setItem(ACTIVE_TAB_KEY,category)}catch{}}
function norm(value){return String(value||"").toLowerCase().replace(/\s+/g," ").trim()}
function suppressed(story,pools,category){const url=norm(story.url),title=norm(story.title),source=norm(story.source);const same=(record,requireCategory)=>{if(!record||record.serverCount)return false;if(requireCategory&&norm(record.category||record.tab)!==norm(category))return false;const recordUrl=norm(record.url_key||record.urlKey||record.url);if(recordUrl&&url&&recordUrl===url)return true;const recordTitle=norm(record.title_key||record.titleKey||record.title),recordSource=norm(record.source_key||record.sourceKey||record.source);return Boolean(recordTitle&&recordSource&&recordTitle===title&&recordSource===source)};return(pools.get("D")||[]).some(record=>same(record,false))||["NR","NW"].some(reason=>(pools.get(reason)||[]).some(record=>same(record,true)))}
export class Store{
  constructor(){this.feed=null;this.nfl={games:[],error:""};this.boxoffice={movies:[],error:""};this.markets={markets:[],error:""};this.status={};this.active=readActiveTab();this.visible=new Map();this.location=null;this.suppressed=new Map([["D",[]],["NR",[]],["NW",[]]]);this.bookmarks=readBookmarks();this.newIds=new Set();this.selectedNfl="";this.underreportedSort="signal"}
  setFeed(feed){this.feed=feed;if(!feed?.categories?.[this.active]&&!["bookmarks","admin"].includes(this.active)){this.active=Object.keys(feed?.categories||{})[0]||"top";writeActiveTab(this.active)}}
  setActive(category){if(["bookmarks","admin"].includes(category)||this.feed?.categories?.[category]){this.active=category;writeActiveTab(category)}if(!this.visible.has(category))this.visible.set(category,PAGE_SIZE)}
  shown(category=this.active){return this.visible.get(category)||PAGE_SIZE}
  loadMore(category=this.active,amount=PAGE_SIZE){this.visible.set(category,this.shown(category)+amount)}
  resetPage(category=this.active){this.visible.set(category,PAGE_SIZE)}
  setUnderreportedSort(value){if(!UNDERREPORTED_SORTS.has(value))return;this.underreportedSort=value;this.resetPage("underreported")}
  rawCategoryPool(category){return[...(this.feed?.stories?.[category]||[]),...(this.feed?.reserves?.[category]||[])]}
  categoryStories(category=this.active){if(category==="bookmarks")return this.bookmarks;if(category==="admin")return[];return this.rawCategoryPool(category).filter(story=>!suppressed(story,this.suppressed,category))}
  allStories(){return Object.keys(this.feed?.categories||{}).flatMap(category=>this.categoryStories(category))}
  bookmarkIds(){return new Set(this.bookmarks.map(row=>row.id))}
  isBookmarked(id){return this.bookmarks.some(row=>row.id===id)}
  toggleBookmark(story){const i=this.bookmarks.findIndex(row=>row.id===id);let saved;if(i>=0){this.bookmarks.splice(i,1);saved=false}else{this.bookmarks.unshift({...story,bookmarked_at:new Date().toISOString()});saved=true}writeBookmarks(this.bookmarks);return saved}
  storyById(id){for(const category of Object.keys(this.feed?.categories||{})){const story=this.rawCategoryPool(category).find(row=>row.id===id);if(story)return story}return this.bookmarks.find(row=>row.id===id)||null}
}
