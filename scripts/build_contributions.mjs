import { chromium } from 'playwright';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const year = 2026;
const source = 'https://github.com/yaswanthakkireddy?tab=overview&from=2026-01-01&to=2026-12-31';
const colors = ['#102334','#1b4670','#287eb3','#42c9cb','#9ff5d5'];
function normalize(rows) {
  const seen = new Set();
  return rows.filter(row => {
    if (!/^2026-\d{2}-\d{2}$/.test(row.date) || !Number.isInteger(row.level) || row.level < 0 || row.level > 4) throw new Error('Invalid contribution source');
    if (seen.has(row.date)) throw new Error('Duplicate date');
    seen.add(row.date);
    return row.level > 0;
  }).sort((a,b) => a.date.localeCompare(b.date)).map(({date,level}) => ({date,level}));
}
function render(days,mobile) {
  const w=mobile?600:1200,h=mobile?670:390;
  const monthCounts = Array.from({length:12},(_,i)=>days.filter(d=>Number(d.date.slice(5,7))===i+1).length);
  const counts = new Map(days.map(d=>[d.date,d.level]));
  const text=(x,y,s,size=20,c='#a8bfd1',weight=400)=>'<text x="'+x+'" y="'+y+'" font-family="Segoe UI,Arial,sans-serif" font-size="'+size+'" font-weight="'+weight+'" fill="'+c+'">'+s+'</text>';
  let svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+w+'" height="'+h+'" viewBox="0 0 '+w+' '+h+'" role="img"><title>GitHub contribution signal for '+year+'</title><desc>Public GitHub daily intensity and active days per month. No invented contribution counts.</desc><defs><linearGradient id="bar" x2="0" y2="1"><stop stop-color="#9ff5d5"/><stop offset="1" stop-color="#287eb3"/></linearGradient></defs><rect x="1" y="1" width="'+(w-2)+'" height="'+(h-2)+'" rx="22" fill="#07141f" stroke="#459dcc" stroke-opacity=".4"/>';
  svg+=text(30,48,'CONTRIBUTION SIGNAL / '+year,mobile?23:19,'#9ff5d5',700)+text(30,91,days.length+' active public contribution days',mobile?29:33,'#eafaff',700);
  const names=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  const bx=mobile?30:660,by=mobile?300:95,bw=mobile?540:510,step=bw/12;
  const max=Math.max(1,...monthCounts);
  svg+=text(bx,by-18,'ACTIVE DAYS PER MONTH',mobile?19:16,'#9ff5d5',600);
  monthCounts.forEach((n,i)=>{
    const x=bx+i*step,bh=n/max*110;
    svg+='<rect x="'+x+'" y="'+(by+125-bh)+'" width="'+(step-12)+'" height="'+Math.max(2,bh)+'" rx="4" fill="url(#bar)" opacity="'+(n?1:.22)+'"/>';
    svg+=text(x,by+153,names[i],mobile?14:12);
    if(n)svg+=text(x,by+113-bh,String(n),mobile?18:16,'#eafaff',600);
  });
  const gx=mobile?30:30,gy=mobile?141:144,cell=mobile?8.4:10,gap=mobile?1.3:1.7;
  const first=new Date(Date.UTC(year,0,1)),offset=(first.getUTCDay()+6)%7;
  const monthList=[];
  for(let day=0;day<365;day++){
    const date=new Date(Date.UTC(year,0,day+1)),key=date.toISOString().slice(0,10),col=Math.floor((day+offset)/7),row=(day+offset)%7;
    const x=gx+col*(cell+gap),y=gy+row*(cell+gap),level=counts.get(key)||0;
    svg+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+cell+'" height="'+cell+'" rx="2" fill="'+colors[level]+'"/>';
  }
  svg+=text(gx,gy+96,'GitHub daily intensity · empty slots remain unfilled',mobile?18:16);
  if(mobile){
    svg+=text(30,475,'Real activity. A clear signal.',29,'#eafaff',600);
    svg+=text(30,513,'Colors reflect GitHub intensity levels.',22);
    svg+=text(30,551,'Bars count active days, not commits.',22);
  }
  const ly=mobile?590:300;
  svg+=text(30,ly,'LESS',mobile?17:14);
  colors.forEach((c,i)=>svg+='<rect x="'+(90+i*27)+'" y="'+(ly-16)+'" width="20" height="20" rx="4" fill="'+c+'"/>');
  svg+=text(240,ly,'MORE',mobile?17:14);
  svg+=text(30,h-25,'Source: public GitHub '+year+' calendar · may include automation',mobile?18:16);
  svg+='<circle r="4" fill="#9ff5d5"><animateMotion dur="9s" repeatCount="indefinite" path="M30 '+(h-55)+'H'+(w-30)+'"/></circle></svg>\n';
  return svg;
}
assert.deepEqual(normalize([{date:'2026-10-01',level:2},{date:'2026-10-02',level:0}]),[{date:'2026-10-01',level:2}]);
assert.equal(render(normalize([{date:'2026-10-01',level:2}]),false),render(normalize([{date:'2026-10-01',level:2},{date:'2026-10-02',level:0}]),false));
assert.throws(()=>normalize([{date:'2026-10-01',level:5}]));
assert.throws(()=>normalize([{date:'2026-10-01',level:1},{date:'2026-10-01',level:2}]));
console.log('Contribution validation and unchanged-activity checks passed.');
const browser=await chromium.launch();
let days;
try {
 const page=await browser.newPage();
 const response=await page.goto(source,{waitUntil:'domcontentloaded',timeout:60000});
 if (!response?.ok()) throw new Error('GitHub calendar unavailable');
 await page.locator('[data-date][data-level]').first().waitFor({timeout:30000});
 const rows=await page.locator('[data-date][data-level]').evaluateAll(cells=>cells.map(cell=>({date:cell.getAttribute('data-date'),level:Number(cell.getAttribute('data-level'))})).filter(row=>row.date.startsWith('2026-')));
 if(rows.length < 200) throw new Error('Incomplete calendar');
 days=normalize(rows);
 if(!days.length) throw new Error('No active dates returned; preserve the previous panel.');
 console.log('Parsed '+rows.length+' calendar cells and '+days.length+' active days.');
} finally { await browser.close(); }
await mkdir('assets',{recursive:true});
async function writeChanged(path,value){
 let old;
 try{old=await readFile(path,'utf8');}catch(error){if(error.code!=='ENOENT')throw error;}
 if(old===value)return;
 await writeFile(path,value);
 console.log('Updated '+path);
}
await writeChanged('assets/contribution-signal.svg',render(days,false));
await writeChanged('assets/contribution-signal-mobile.svg',render(days,true));
await writeChanged('assets/contribution-source.json',JSON.stringify({year,source,scope:'Public GitHub intensity levels; active days only. No fetch timestamp.',days},null,2)+'\n');
