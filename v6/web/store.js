export const PAGE_SIZE=20;
export class Store{
  constructor(){this.feed=null;this.nfl={games:[],error:""};this.boxoffice={movies:[],error:""};this.active="top";this.visible=new Map();this.location=null;this.suppressed=new Map([["D",[]],["NR",[]],["NW",[]]])}
  setFeed(feed){this.feed=feed;if(!feed?.categories?.[this.active])this.active=Object.keys(feed?.categories||{})[0]||"top"}
  setActive(category){if(this.feed?.categories?.[category])this.active=category;if(!this.visible.has(category))this.visible.set(category,PAGE_SIZE)}
  shown(category=this.active){return this.visible.get(category)||PAGE_SIZE}
  loadMore(category=this.active,amount=PAGE_SIZE){this.visible.set(category,this.shown(category)+amount)}
  resetPage(category=this.active){this.visible.set(category,PAGE_SIZE)}
  categoryStories(category=this.active){return this.feed?.stories?.[category]||[]}
}
