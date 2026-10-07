import { writeFile, mkdir } from 'node:fs/promises';
// Use the owner's actual public avatar. Keep its pixels unchanged.
const portraitUrl = 'https://avatars.githubusercontent.com/u/276199363?v=4';
const response = await fetch(portraitUrl, { signal: AbortSignal.timeout(30000) });
if (!response.ok) throw new Error('Portrait request failed: ' + response.status);
const mime = response.headers.get('content-type')?.split(';')[0];
if (!['image/png', 'image/jpeg', 'image/webp'].includes(mime)) throw new Error('Unexpected avatar format');
const bytes = Buffer.from(await response.arrayBuffer());
if (!bytes.length || bytes.length > 4_000_000) throw new Error('Unexpected avatar size');
const portrait = 'data:' + mime + ';base64,' + bytes.toString('base64');
const font = 'Inter,Segoe UI,Arial,sans-serif';
const mono = 'ui-monospace,Consolas,monospace';
const escape = text => text.replaceAll('&','&amp;').replaceAll('<','&lt;');
const text = (x,y,value,size,color='#d5d9e5',weight=400,family=font) => '<text x="'+x+'" y="'+y+'" font-family="'+family+'" font-size="'+size+'" font-weight="'+weight+'" fill="'+color+'">'+escape(value)+'</text>';
function render(mobile) {
  const w=mobile?600:1200, h=mobile?870:640;
  const cx=mobile?300:936, cy=mobile?279:287, radius=mobile?168:187;
  let s='<svg xmlns="http://www.w3.org/2000/svg" width="'+w+'" height="'+h+'" viewBox="0 0 '+w+' '+h+'" role="img" aria-labelledby="title desc"><title id="title">Call me Yaswanth — AI Engineer</title><desc id="desc">Yaswanth Kumar Akkireddy, using his actual GitHub avatar. Agentic AI, RAG, evaluation, reliability and security.</desc>';
  s+='<defs><radialGradient id="glow"><stop stop-color="#ff4825" stop-opacity=".7"/><stop offset="1" stop-color="#ff4825" stop-opacity="0"/></radialGradient><linearGradient id="rim"><stop stop-color="#ff4825"/><stop offset=".5" stop-color="#ff923c"/><stop offset="1" stop-color="#ffd53d"/></linearGradient><clipPath id="portrait"><circle cx="'+cx+'" cy="'+cy+'" r="'+(radius-7)+'"/></clipPath><clipPath id="typing"><rect x="42" y="'+(mobile?709:371)+'" width="'+(mobile?510:627)+'" height="42"><animate attributeName="width" values="0;627;627;0;0" keyTimes="0;.18;.78;.9;1" dur="12s" repeatCount="indefinite"/></rect></clipPath><pattern id="grid" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="#fff" stroke-opacity=".025"/></pattern></defs>';
  s+='<rect x="1" y="1" width="'+(w-2)+'" height="'+(h-2)+'" rx="20" fill="#05070e" stroke="#323646"/><rect x="1" y="1" width="'+(w-2)+'" height="'+(h-2)+'" rx="20" fill="url(#grid)"/>';
  s+=text(30,41,'yaswanthakkireddy / identity.sys',mobile?19:17,'#858ca2',400,mono);
  s+='<circle cx="'+(w-35)+'" cy="35" r="5" fill="#a3ff39"><animate attributeName="opacity" values="1;.5;1" dur="4s" repeatCount="indefinite"/></circle><path d="M24 61H'+(w-24)+'" stroke="#2b3040"/>';
  s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+(radius*1.45)+'" fill="url(#glow)"/><circle cx="'+cx+'" cy="'+cy+'" r="'+radius+'" fill="#ff4825" stroke="url(#rim)" stroke-width="4"/>';
  s+='<image href="'+portrait+'" x="'+(cx-radius+7)+'" y="'+(cy-radius+7)+'" width="'+(2*radius-14)+'" height="'+(2*radius-14)+'" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait)"/>';
  s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+(radius+13)+'" fill="none" stroke="#ff6937" stroke-opacity=".65" stroke-width="1.5" stroke-dasharray="90 220"><animateTransform attributeName="transform" type="rotate" from="0 '+cx+' '+cy+'" to="360 '+cx+' '+cy+'" dur="32s" repeatCount="indefinite"/></circle>';
  s+='<path d="M'+(cx-radius-15)+' '+(cy-radius+12)+'v-25h35M'+(cx+radius+15)+' '+(cy+radius-12)+'v25h-35" fill="none" stroke="#ff7b42" stroke-width="3"/>';
  if(mobile) {
    s+=text(30,521,'Call me',52,'#ff4b2e',400,'Georgia,serif');
    s+=text(27,594,'Yaswanth.',68,'#a3ff39',800);
    s+=text(30,641,'KUMAR AKKIREDDY',24,'#f5f5fa',600,mono);
    s+=text(30,688,'AI ENGINEER',21,'#8894b0',500,mono);
    s+='<g clip-path="url(#typing)">'+text(30,741,'> agents · RAG · evaluation',25,'#00c8ff',500,mono)+'</g>';
    s+='<rect x="30" y="769" width="167" height="37" rx="4" fill="#00a9ed"/><rect x="204" y="769" width="173" height="37" rx="4" fill="#ff4b2e"/><rect x="384" y="769" width="186" height="37" rx="4" fill="#ffd537"/>';
    s+=text(45,794,'LANGGRAPH',18,'#fff',600,mono)+text(220,794,'EVALUATION',18,'#fff',600,mono)+text(401,794,'RELIABILITY',18,'#080b14',600,mono);
    s+=text(30,846,'Bengaluru · India / Remote',22,'#b3bccf');
  } else {
    s+=text(42,137,'GENERATIVE + AGENTIC AI',18,'#00c8ff',600,mono);
    s+=text(42,226,'Call me',65,'#ff4b2e',400,'Georgia,serif');
    s+=text(36,322,'Yaswanth.',90,'#a3ff39',800);
    s+=text(43,360,'KUMAR AKKIREDDY',27,'#fff',600,mono);
    s+='<g clip-path="url(#typing)">'+text(42,404,'> build · evaluate · red team · ship',24,'#00c8ff',500,mono)+'</g>';
    s+=text(42,455,'AI Engineer. Evidence before execution.',27,'#c4cbda');
    const badges=[['LANGGRAPH','#00a9ed',170],['RAG + AGENTS','#ff4b2e',190],['EVALUATION','#00a9ed',178],['RELIABILITY','#ffd537',198],['AI SECURITY','#a3ff39',178]];
    let x=42;
    badges.forEach(([label,color,width])=>{s+='<rect x="'+x+'" y="515" width="'+width+'" height="43" rx="4" fill="'+color+'"/>'+text(x+15,543,label,18,['#ffd537','#a3ff39'].includes(color)?'#080b14':'#fff',700,mono);x+=width+9;});
    s+='<path d="M42 582H1158" stroke="#2b3040"/>'+text(42,616,'Applied AI Engineer · Felix Byte',18)+text(638,616,'Previously AI Red Team · Aram Algorithm',18);
  }
  s+='</svg>\n'; return s;
}
await mkdir('assets', {recursive:true});
await writeFile('assets/hero.svg', render(false));
await writeFile('assets/hero-mobile.svg', render(true));
await writeFile('assets/portrait-source.json', JSON.stringify({source:portraitUrl,format:mime,note:'Public GitHub avatar; original pixels preserved. Refresh only when the source avatar changes.'},null,2)+'\n');
console.log('Generated portrait headers from the actual public GitHub avatar ('+bytes.length+' bytes).');
