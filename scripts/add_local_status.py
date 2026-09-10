from pathlib import Path
import re

P=Path('index.html')
s=P.read_text(encoding='utf-8')

STYLE='''\n<style id="local-status-style">\n.toolbar{gap:9px}.local-status{margin-left:auto;display:flex;align-items:center;gap:9px;min-width:0;color:#475569;font-size:11px;white-space:nowrap}.local-status .local-date,.local-status .local-time{font-weight:700;color:#334155}.local-status .local-weather{display:inline-flex;align-items:center;gap:4px}.local-status .weather-temp{font-weight:800;color:#111827}.local-status .weather-condition{color:#64748b}.local-status .weather-location{color:#94a3b8;max-width:150px;overflow:hidden;text-overflow:ellipsis}.local-status .local-sep{color:#cbd5e1}@media(prefers-color-scheme:dark){.local-status,.local-status .local-date,.local-status .local-time,.local-status .weather-temp{color:#e5e7eb}.local-status .weather-condition{color:#a1a1aa}}@media(max-width:700px){.local-status{gap:5px;font-size:10px}.local-status .weather-location,.local-status .weather-condition,.local-status .local-sep{display:none}}\n</style>\n'''
HTML='''<div id="local-status" class="local-status" aria-label="Local date, time and weather"><span class="local-date" id="local-date">—</span><span class="local-sep">·</span><span class="local-time" id="local-time">—</span><span class="local-sep">·</span><span class="local-weather"><span id="weather-icon">☀️</span><span class="weather-temp" id="weather-temp">—°</span><span class="weather-condition" id="weather-condition">Loading weather…</span><span class="weather-location" id="weather-location"></span></span></div>'''
JS=r'''<script id="local-status-v1">
(function(){
'use strict';
const weatherCodes={0:['☀️','Clear'],1:['🌤️','Mostly clear'],2:['⛅','Partly cloudy'],3:['☁️','Cloudy'],45:['🌫️','Foggy'],48:['🌫️','Foggy'],51:['🌦️','Light drizzle'],53:['🌦️','Drizzle'],55:['🌧️','Heavy drizzle'],61:['🌦️','Light rain'],63:['🌧️','Rain'],65:['🌧️','Heavy rain'],71:['🌨️','Light snow'],73:['❄️','Snow'],75:['❄️','Heavy snow'],80:['🌦️','Showers'],81:['🌧️','Showers'],82:['⛈️','Heavy showers'],85:['🌨️','Snow showers'],86:['❄️','Heavy snow showers'],95:['⛈️','Thunderstorm'],96:['⛈️','Thunderstorm'],99:['⛈️','Severe thunderstorm']};
let clockTimer=null,weatherTimer=null;
function updateClock(){const d=new Date(),date=document.getElementById('local-date'),time=document.getElementById('local-time');if(!date||!time)return;date.textContent=d.toLocaleDateString([], {weekday:'short',month:'short',day:'numeric'});time.textContent=d.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});clearTimeout(clockTimer);clockTimer=setTimeout(updateClock,Math.max(1000,60000-(d.getSeconds()*1000+d.getMilliseconds())));}
async function coords(){if(window.UnderreportedLocation?.get)return window.UnderreportedLocation.get();throw new Error('Location service unavailable');}
async function loadWeather(){const icon=document.getElementById('weather-icon'),temp=document.getElementById('weather-temp'),condition=document.getElementById('weather-condition'),location=document.getElementById('weather-location');try{const c=await coords();const r=await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${encodeURIComponent(c.lat)}&longitude=${encodeURIComponent(c.lon)}&current=temperature_2m,weather_code&temperature_unit=fahrenheit&timezone=auto`,{cache:'no-store'});if(!r.ok)throw new Error('weather unavailable');const d=await r.json(),code=Number(d.current?.weather_code),w=weatherCodes[code]||['🌡️','Current conditions'];icon.textContent=w[0];temp.textContent=Math.round(Number(d.current?.temperature_2m))+'°';condition.textContent=w[1];location.textContent=c.label||[c.city,c.state].filter(Boolean).join(', ');}catch(e){condition.textContent='Weather unavailable';}finally{clearTimeout(weatherTimer);weatherTimer=setTimeout(loadWeather,10*60*1000);}}
function start(){updateClock();loadWeather();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
</script>'''

s=re.sub(r'\n?<style id="local-status-style">.*?</style>\n?','\n',s,flags=re.S)
s=re.sub(r'<div id="local-status".*?</div>','',s,count=1,flags=re.S)
s=re.sub(r'\n?<script id="local-status-v1">.*?</script>\n?','\n',s,flags=re.S)
if '</head>' not in s:raise SystemExit('Missing </head>')
s=s.replace('</head>',STYLE+'</head>',1)
status=re.search(r'<span id="status"[^>]*>.*?</span>',s,flags=re.S)
if not status:raise SystemExit('Status element not found')
s=s[:status.end()]+HTML+s[status.end():]
if '</body>' not in s:raise SystemExit('Missing </body>')
s=s.replace('</body>',JS+'\n</body>',1)
P.write_text(s,encoding='utf-8')
print('Added local status using the shared location service, minute-aligned clock updates, and ten-minute weather refreshes.')
