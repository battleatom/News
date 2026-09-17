const LOCATION_KEY="underreported-v6-location";
const REFRESH_MS=15*60*1000;
const FALLBACK={lat:36.7281,lon:-108.2187,city:"Farmington",state:"NM",source:"fallback"};
let lastKey="",lastFetch=0,busy=false;

function weatherLabel(code){
  code=Number(code);
  if(code===0)return["☀️","Clear"];
  if(code<=2)return["🌤️","Partly cloudy"];
  if(code===3)return["☁️","Cloudy"];
  if(code<=48)return["🌫️","Fog"];
  if(code<=57)return["🌦️","Drizzle"];
  if(code<=67)return["🌧️","Rain"];
  if(code<=77)return["🌨️","Snow"];
  if(code<=82)return["🌦️","Showers"];
  if(code<=86)return["🌨️","Snow showers"];
  if(code<=99)return["⛈️","Storm"];
  return["🌡️","Weather"];
}
function forecastDayLabel(date,index){if(index===0)return"Today";if(index===1)return"Tomorrow";const d=new Date(`${date}T12:00:00`);return new Intl.DateTimeFormat(undefined,{weekday:"short"}).format(d)}
function readLocation(){try{const value=JSON.parse(localStorage.getItem(LOCATION_KEY)||"null");if(value&&Number.isFinite(Number(value.lat))&&Number.isFinite(Number(value.lon)))return value}catch{}return FALLBACK}
function ensureStrip(){
  let strip=document.getElementById("weather-forecast-strip");if(strip)return strip;
  const toolbar=document.querySelector(".toolbar");if(!toolbar)return null;
  const old=document.getElementById("weather-status");if(old){old.style.display="none";const sep=old.previousElementSibling;if(sep?.classList.contains("sep"))sep.style.display="none"}
  const style=document.createElement("style");style.id="weather-forecast-style";style.textContent=`#weather-forecast-strip{max-width:var(--max);margin:0 auto;padding:0 18px 8px;overflow-x:auto;overflow-y:hidden;white-space:nowrap;scrollbar-width:none;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;scroll-snap-type:x proximity}#weather-forecast-strip::-webkit-scrollbar{display:none}.weather-forecast-track{display:flex;width:max-content;min-width:100%;gap:7px;align-items:center}.weather-pill{display:inline-flex;align-items:center;gap:6px;flex:0 0 auto;min-height:30px;padding:5px 9px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--text);box-shadow:0 2px 7px rgba(15,23,42,.055);font-size:.64rem;font-weight:800;scroll-snap-align:start}.weather-pill.current{border-color:color-mix(in srgb,var(--accent) 28%,var(--line));background:color-mix(in srgb,var(--accent) 6%,var(--surface))}.weather-icon{font-size:.9rem;line-height:1}.weather-day{font-weight:950}.weather-detail{color:var(--muted);font-weight:700}.weather-rain{color:#2563eb;font-weight:850}.weather-error{color:var(--muted)}@media(max-width:760px){#weather-forecast-strip{padding:0 12px 7px}.weather-forecast-track{min-width:max-content}.weather-pill{min-height:29px;padding:5px 8px;font-size:.62rem}}`;document.head.appendChild(style);
  strip=document.createElement("div");strip.id="weather-forecast-strip";strip.setAttribute("aria-label","Current weather and five-day forecast. Swipe horizontally for more.");strip.innerHTML='<div class="weather-forecast-track"><span class="weather-pill current">🌡️ Weather loading…</span></div>';toolbar.insertAdjacentElement("afterend",strip);return strip;
}
function renderWeather(data){const strip=ensureStrip();if(!strip)return;const currentTemp=Math.round(Number(data.current?.temperature_2m));const[currentIcon,currentText]=weatherLabel(data.current?.weather_code);const current=Number.isFinite(currentTemp)?`<span class="weather-pill current"><span class="weather-icon">${currentIcon}</span><span>${currentTemp}°</span><span class="weather-detail">${currentText}</span></span>`:"";const daily=data.daily||{},dates=daily.time||[];const days=dates.slice(0,5).map((date,i)=>{const[icon]=weatherLabel(daily.weather_code?.[i]);const hi=Math.round(Number(daily.temperature_2m_max?.[i])),lo=Math.round(Number(daily.temperature_2m_min?.[i])),rain=Math.round(Number(daily.precipitation_probability_max?.[i]));const temps=Number.isFinite(hi)&&Number.isFinite(lo)?`${hi}° / ${lo}°`:"";const precip=Number.isFinite(rain)?`<span class="weather-rain">💧 ${rain}%</span>`:"";return`<span class="weather-pill"><span class="weather-icon">${icon}</span><span class="weather-day">${forecastDayLabel(date,i)}</span>${temps?`<span>${temps}</span>`:""}${precip}</span>`}).join("");strip.innerHTML=`<div class="weather-forecast-track">${current}${days}</div>`}
function renderError(){const strip=ensureStrip();if(strip)strip.innerHTML='<div class="weather-forecast-track"><span class="weather-pill weather-error">🌡️ Weather temporarily unavailable</span></div>'}
async function refreshWeather(force=false){if(busy)return;const location=readLocation();const key=`${Number(location.lat).toFixed(3)},${Number(location.lon).toFixed(3)}`;if(!force&&key===lastKey&&Date.now()-lastFetch<REFRESH_MS)return;busy=true;try{const q=new URLSearchParams({lat:String(location.lat),lon:String(location.lon)});let response=await fetch(`/api/weather?${q}`,{cache:"no-store"});if(!response.ok)throw new Error(`weather proxy ${response.status}`);renderWeather(await response.json());lastKey=key;lastFetch=Date.now()}catch(error){console.warn("Weather forecast refresh failed",error);renderError()}finally{busy=false}}
ensureStrip();setTimeout(()=>refreshWeather(true),300);setInterval(()=>refreshWeather(false),15000);document.addEventListener("visibilitychange",()=>{if(!document.hidden)refreshWeather(false)});window.addEventListener("storage",e=>{if(e.key===LOCATION_KEY)refreshWeather(true)});document.addEventListener("v6:locationchange",()=>refreshWeather(true));
