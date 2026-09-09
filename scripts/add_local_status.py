from pathlib import Path

P = Path('index.html')
s = P.read_text(encoding='utf-8')

STYLE = '''\n<style id="local-status-style">\n.toolbar{gap:9px}.local-status{margin-left:auto;display:flex;align-items:center;gap:9px;min-width:0;color:#475569;font-size:11px;white-space:nowrap}.local-status .local-date,.local-status .local-time{font-weight:700;color:#334155}.local-status .local-weather{display:inline-flex;align-items:center;gap:4px}.local-status .weather-temp{font-weight:800;color:#111827}.local-status .weather-condition{color:#64748b}.local-status .weather-location{color:#94a3b8;max-width:130px;overflow:hidden;text-overflow:ellipsis}.local-status .local-sep{color:#cbd5e1}@media(max-width:700px){.local-status{gap:5px;font-size:10px}.local-status .weather-location{display:none}.local-status .weather-condition{display:none}.local-status .local-sep{display:none}}\n</style>\n'''
HTML = '''<div id="local-status" class="local-status" aria-label="Local date, time and weather"><span class="local-date" id="local-date">—</span><span class="local-sep">·</span><span class="local-time" id="local-time">—</span><span class="local-sep">·</span><span class="local-weather"><span id="weather-icon">☀️</span><span class="weather-temp" id="weather-temp">—°</span><span class="weather-condition" id="weather-condition">Loading weather…</span><span class="weather-location" id="weather-location"></span></span></div>'''
JS = r'''<script id="local-status-v1">
const weatherCodes={0:['☀️','Clear'],1:['🌤️','Mostly clear'],2:['⛅','Partly cloudy'],3:['☁️','Cloudy'],45:['🌫️','Foggy'],48:['🌫️','Foggy'],51:['🌦️','Light drizzle'],53:['🌦️','Drizzle'],55:['🌧️','Heavy drizzle'],56:['🌧️','Freezing drizzle'],57:['🌧️','Freezing drizzle'],61:['🌦️','Light rain'],63:['🌧️','Rain'],65:['🌧️','Heavy rain'],66:['🌨️','Freezing rain'],67:['🌨️','Freezing rain'],71:['🌨️','Light snow'],73:['❄️','Snow'],75:['❄️','Heavy snow'],77:['🌨️','Snow grains'],80:['🌦️','Showers'],81:['🌧️','Showers'],82:['⛈️','Heavy showers'],85:['🌨️','Snow showers'],86:['❄️','Heavy snow showers'],95:['⛈️','Thunderstorm'],96:['⛈️','Thunderstorm'],99:['⛈️','Severe thunderstorm']};
function updateLocalClock(){const d=new Date();const date=document.getElementById('local-date'),time=document.getElementById('local-time');if(!date||!time)return;date.textContent=d.toLocaleDateString([], {weekday:'short',month:'short',day:'numeric'});time.textContent=d.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});}
async function getLocalCoords(){try{if(navigator.geolocation){const p=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:false,maximumAge:900000,timeout:6000}));return {lat:p.coords.latitude,lon:p.coords.longitude};}}catch(e){}try{const r=await fetch('https://ipapi.co/json/',{cache:'no-store'});const d=await r.json();if(d.latitude&&d.longitude)return {lat:Number(d.latitude),lon:Number(d.longitude),city:d.city,state:d.region_code};}catch(e){}return null;}
async function loadLocalWeather(){const icon=document.getElementById('weather-icon'),temp=document.getElementById('weather-temp'),condition=document.getElementById('weather-condition'),location=document.getElementById('weather-location');try{const c=await getLocalCoords();if(!c)throw new Error('location unavailable');const r=await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${encodeURIComponent(c.lat)}&longitude=${encodeURIComponent(c.lon)}&current=temperature_2m,weather_code&temperature_unit=fahrenheit&timezone=auto`,{cache:'no-store'});if(!r.ok)throw new Error('weather unavailable');const d=await r.json();const code=Number(d.current?.weather_code);const w=weatherCodes[code]||['🌡️','Current conditions'];icon.textContent=w[0];temp.textContent=Math.round(Number(d.current?.temperature_2m))+'°';condition.textContent=w[1];if(c.city)location.textContent=c.city+(c.state?', '+c.state:'');}catch(e){condition.textContent='Weather unavailable';}}
updateLocalClock();setInterval(updateLocalClock,1000);loadLocalWeather();setInterval(loadLocalWeather,5*60*1000);
</script>'''

# Remove/reinsert our own blocks so the patch remains idempotent.
import re
s = re.sub(r'\n<style id="local-status-style">.*?</style>\n', '\n', s, flags=re.S)
s = re.sub(r'\n<div id="local-status".*?</div>', '', s, count=1, flags=re.S)
s = re.sub(r'\n<script id="local-status-v1">.*?</script>', '', s, flags=re.S)

if '</head>' not in s or '<div class="toolbar">' not in s:
    raise SystemExit('Expected page structure not found')
s = s.replace('</head>', STYLE + '</head>', 1)
s = s.replace('<div class="toolbar"><button id="refresh" onclick="loadNews(true)">↻ Refresh</button><span id="status">Loading…</span></div>', '<div class="toolbar"><button id="refresh" onclick="loadNews(true)">↻ Refresh</button><span id="status">Loading…</span>' + HTML + '</div>', 1)
s = s.replace('</body>', JS + '\n</body>', 1)
P.write_text(s, encoding='utf-8')
print('Added live local date/time/weather display to the right of Refresh.')