/** Generuje tři ilustrační animace pro knowledge_graphs_analysis.md.\n * Použití: node scripts/generate_kg_animations.js (Node.js, bez závislostí).\n */\nconst fs = require('fs');\nconst path = require('path');\nconst files = (function generateGifs(){
 const W=720,H=352;
 const pal=[
 [11,18,32],[23,36,58],[57,76,105],[241,246,255],
 [161,183,209],[93,156,255],[48,211,184],[255,196,103],
 [255,120,144],[35,54,81],[107,228,170],[20,52,64],
 [43,70,105],[104,125,157],[15,27,43],[196,178,255]
 ];
 const glyph={
 "A":["01110","10001","10001","11111","10001","10001","10001"],
 "B":["11110","10001","10001","11110","10001","10001","11110"],
 "C":["01111","10000","10000","10000","10000","10000","01111"],
 "D":["11110","10001","10001","10001","10001","10001","11110"],
 "E":["11111","10000","10000","11110","10000","10000","11111"],
 "F":["11111","10000","10000","11110","10000","10000","10000"],
 "G":["01111","10000","10000","10111","10001","10001","01111"],
 "H":["10001","10001","10001","11111","10001","10001","10001"],
 "I":["11111","00100","00100","00100","00100","00100","11111"],
 "J":["00111","00010","00010","00010","10010","10010","01100"],
 "K":["10001","10010","10100","11000","10100","10010","10001"],
 "L":["10000","10000","10000","10000","10000","10000","11111"],
 "M":["10001","11011","10101","10101","10001","10001","10001"],
 "N":["10001","11001","10101","10011","10001","10001","10001"],
 "O":["01110","10001","10001","10001","10001","10001","01110"],
 "P":["11110","10001","10001","11110","10000","10000","10000"],
 "Q":["01110","10001","10001","10001","10101","10010","01101"],
 "R":["11110","10001","10001","11110","10100","10010","10001"],
 "S":["01111","10000","10000","01110","00001","00001","11110"],
 "T":["11111","00100","00100","00100","00100","00100","00100"],
 "U":["10001","10001","10001","10001","10001","10001","01110"],
 "V":["10001","10001","10001","10001","10001","01010","00100"],
 "W":["10001","10001","10001","10101","10101","10101","01010"],
 "X":["10001","10001","01010","00100","01010","10001","10001"],
 "Y":["10001","10001","01010","00100","00100","00100","00100"],
 "Z":["11111","00001","00010","00100","01000","10000","11111"],
 "0":["01110","10011","10101","10101","11001","10001","01110"],
 "1":["00100","01100","00100","00100","00100","00100","01110"],
 "2":["01110","10001","00001","00010","00100","01000","11111"],
 "3":["11110","00001","00001","01110","00001","00001","11110"],
 "4":["00010","00110","01010","10010","11111","00010","00010"],
 "5":["11111","10000","10000","11110","00001","00001","11110"],
 "6":["01110","10000","10000","11110","10001","10001","01110"],
 "7":["11111","00001","00010","00100","01000","01000","01000"],
 "8":["01110","10001","10001","01110","10001","10001","01110"],
 "9":["01110","10001","10001","01111","00001","00001","01110"],
 " ":["00000","00000","00000","00000","00000","00000","00000"],
 ".":["00000","00000","00000","00000","00000","01100","01100"],
 ":":["00000","01100","01100","00000","01100","01100","00000"],
 "-":["00000","00000","00000","11111","00000","00000","00000"],
 "?":["01110","10001","00001","00010","00100","00000","00100"],
 "/":["00001","00001","00010","00100","01000","10000","10000"],
 "=":["00000","11111","00000","11111","00000","00000","00000"],
 "+":["00000","00100","00100","11111","00100","00100","00000"],
 "#":["01010","11111","01010","11111","01010","00000","00000"]
 };
 const img=()=>new Uint8Array(W*H).fill(0);
 function rect(p,x,y,w,h,c){const x0=Math.max(0,Math.floor(x)), y0=Math.max(0,Math.floor(y)), x1=Math.min(W,Math.ceil(x+w)), y1=Math.min(H,Math.ceil(y+h));for(let j=y0;j<y1;j++)p.fill(c,j*W+x0,j*W+x1)}
 function round(p,x,y,w,h,r,c){rect(p,x+r,y,w-2*r,h,c);rect(p,x,y+r,r,h-2*r,c);rect(p,x+w-r,y+r,r,h-2*r,c);for(let dy=0;dy<r;dy++)for(let dx=0;dx<r;dx++){if((r-dx-0.5)**2+(r-dy-0.5)**2<=r*r){rect(p,x+dx,y+dy,1,1,c);rect(p,x+w-1-dx,y+dy,1,1,c);rect(p,x+dx,y+h-1-dy,1,1,c);rect(p,x+w-1-dx,y+h-1-dy,1,1,c)}}}
 function card(p,x,y,w,h,bg=1,border=2,r=10){round(p,x-1,y-1,w+2,h+2,r,border);round(p,x,y,w,h,r,bg)}
 function line(p,x0,y0,x1,y1,c=5,t=2){const dx=Math.abs(x1-x0),dy=Math.abs(y1-y0);let sx=x0<x1?1:-1,sy=y0<y1?1:-1,err=dx-dy;while(true){rect(p,x0-Math.floor(t/2),y0-Math.floor(t/2),t,t,c);if(x0===x1&&y0===y1)break;const e=2*err;if(e>-dy){err-=dy;x0+=sx}if(e<dx){err+=dx;y0+=sy}}}
 function arrow(p,x0,y0,x1,y1,c=5){line(p,x0,y0,x1,y1,c,2);const angle=Math.atan2(y1-y0,x1-x0);const a=9;line(p,x1,y1,Math.round(x1-a*Math.cos(angle-.6)),Math.round(y1-a*Math.sin(angle-.6)),c,2);line(p,x1,y1,Math.round(x1-a*Math.cos(angle+.6)),Math.round(y1-a*Math.sin(angle+.6)),c,2)}
 function text(p,x,y,s,c=3,sc=2){let xx=x;for(const ch of s.toUpperCase()){const rows=glyph[ch]||glyph["?"];for(let yy=0;yy<7;yy++)for(let i=0;i<5;i++){if(rows[yy][i]==="1")rect(p,xx+i*sc,y+yy*sc,sc,sc,c)}xx+=6*sc}}
 function circle(p,cx,cy,r,c){for(let yy=-r;yy<=r;yy++){const dx=Math.floor(Math.sqrt(r*r-yy*yy));rect(p,cx-dx,cy+yy,dx*2+1,1,c)}}
 function node(p,x,y,r,label,color){circle(p,x,y,r,color);circle(p,x,y,r-4,9);text(p,x-(label.length*6),y-7,label,3,2)}
 function top(p,title,step){text(p,24,20,title,3,2);rect(p,20,57,680,2,2);text(p,24,69,step,4,1)}
 function badge(p,x,y,label,c){card(p,x,y,label.length*12+20,28,9,c,7);text(p,x+10,y+7,label,3,2)}
 function footer(p,msg,c=4){text(p,24,331,msg,c,1)}
 function pipeline(k){
  const p=img();top(p,"OD DOKUMENTU KE GRAFU",["KROK 1 / ZDROJOVY TEXT","KROK 2 / NALEZENE ENTITY","KROK 3 / UDALOST A ROLE","KROK 4 / ZNALOSTNI GRAF","KROK 4 / PROPOJENY VYSLEDEK"][k]);card(p,20,91,326,226);card(p,362,91,338,226);
  text(p,39,109,"HISTORICKA LISTINA",7);rect(p,38,133,286,1,2);
  const lines=["JAN NOVAK","PRODAL 1542","PETRU MALEMU","MLYN V BRNE"];
  lines.forEach((s,i)=>{if(k>=1){rect(p,36,150+i*36,286,26,i===0||i===2?11:12)}text(p,47,156+i*36,s,k>=1?(i===1?7:6):3,2)});
  if(k===0){text(p,389,153,"EXTRAKCE FAKTU",4);text(p,389,186,"ZATIM NEPROBEHLA",4);badge(p,389,241,"VSTUP: OCR",5)}
  if(k===1){text(p,389,115,"ROZPOZNANE PRVKY",6);badge(p,390,152,"JAN NOVAK",5);badge(p,537,152,"PETR MALY",5);badge(p,390,202,"MLYN",7);badge(p,512,202,"BRNO",6)}
  if(k>=2){
   text(p,389,109,k===2?"JEDNA UDALOST":"GRAF UDALOSTI",6);
   circle(p,528,192,44,5);circle(p,528,192,39,9);text(p,490,185,"PRODEJ",3);text(p,506,202,"1542",7);
   const dots=[[417,155,"JAN",6],[648,155,"PETR",7],[425,265,"MLYN",10],[638,265,"BRNO",15]];
   for(const [x,y,s,c] of dots){if(k>=3)arrow(p,528,192,x,y,c);node(p,x,y,26,s,c)}
   if(k>=4){rect(p,373,291,319,19,11);text(p,387,297,"ZDROJ: LISTINA / STRANA 2",10,1)}
  }
  footer(p,k<2?"NEJPRVE ROZPOZNAT ZMINKY, POTOM VZTAHY":"ROLE, CAS A MISTO PATRI K JEDNE UDALOSTI");
  return p;
 }
 function entity(k){
  const p=img();top(p,"SJEDNOCOVANI ENTIT",["DVE ZMINKY V RUZNYCH LISTINACH","PODOBNOST JMEN NESTACI","KONTROLA DALSICH DUKAZU","SLOUCENI AZ PO OVERENI","JEDNA IDENTITA / DVA ZDROJE"][k]);
  card(p,20,92,324,73);card(p,376,92,324,73);
  text(p,36,107,"LISTINA A",7);text(p,36,134,"JAN NOVAK, MLYNAR",3,2);
  text(p,390,107,"LISTINA B",7);text(p,390,134,"J. NOVAK Z BRNA",3,2);
  if(k<3){
   node(p,194,244,42,"JAN",5);node(p,526,244,42,"J.",7);
   if(k>=1){arrow(p,254,242,462,242,15);text(p,273,199,"STEJNA OSOBA?",15,2)}
   if(k>=2){badge(p,216,285,"POROVNAT KONTEXT",6)}
   else footer(p,"STEJNE JMENO SAMO O SOBE NENI DUKAZ");
  }else{
   arrow(p,180,164,322,237,6);arrow(p,543,164,400,237,7);
   circle(p,360,248,58,10);circle(p,360,248,52,9);text(p,312,240,"PERSON",3);text(p,334,258,"001",7);
   text(p,36,283,"ZMINKA A",6);text(p,558,283,"ZMINKA B",7);
   footer(p,"SLOUCENI JE NUTNE OPRAVIT, POKUD SE UKAZE CHYBA",k===4?10:4);
  }
  return p;
 }
 function provenance(k){
  const p=img();top(p,"DVA ZDROJE, DVE TVRZENI",["ROZDILNA DATA V LISTINACH","ULOZIME OBE TVRZENI","KE KAZDEMU TVRZENI PRIPOJIME ZDROJ","KONFLIKT BEZ ZTRATY INFORMACI","DOTAZ VRACI TVRZENI A DUKAZY"][k]);
  card(p,20,92,324,90);card(p,376,92,324,90);
  text(p,36,109,"LISTINA A",7);text(p,36,142,"PRODEJ ROK 1542",3);
  text(p,390,109,"LISTINA B",7);text(p,390,142,"PRODEJ ROK 1547",3);
  if(k===0){text(p,213,244,"KTERY ROK PLATI?",8);footer(p,"ZE ZDROJU TO ZATIM NELZE ROZHODNOUT")}
  else{
   if(k>=2){arrow(p,156,183,156,221,6);arrow(p,536,183,536,221,7)}
   card(p,31,229,301,69,9,k>=2?6:2);card(p,389,229,301,69,9,k>=2?7:2);
   text(p,47,240,"TVRZENI #A",6);text(p,47,269,"ROK: 1542",3);
   text(p,405,240,"TVRZENI #B",7);text(p,405,269,"ROK: 1547",3);
   if(k>=3){line(p,333,259,387,259,8,3);text(p,334,206,"!",8,3);text(p,270,309,"ROZPOR ZDROJU",8,2)}
   footer(p,k>=4?"KAZDE TVRZENI MA SVUJ DOKLAD A STAV OVERENI":"NEVYBIRAT AUTOMATICKY JEDNU VERZI");
  }
  return p;
 }
 const push16=(a,x)=>{a.push(x&255,(x>>8)&255)};
 function compress(p){
  const out=[];let bit=0,nbits=0,cs=5,next=18;const map=new Map();
  function emit(c){bit|=c<<nbits;nbits+=cs;while(nbits>=8){out.push(bit&255);bit>>>=8;nbits-=8}}
  emit(16);let w=p[0];
  for(let i=1;i<p.length;i++){
   const v=p[i],key=w*16+v;
   if(map.has(key)){w=map.get(key);continue}
   emit(w);
   if(next<4096){map.set(key,next++);if(next>(1<<cs)&&cs<12)cs++}
   else{emit(16);map.clear();next=18;cs=5}
   w=v;
  }
  emit(w);emit(17);if(nbits>0)out.push(bit&255);
  return out;
 }
 function make(frames){
  const a=[71,73,70,56,57,97];push16(a,W);push16(a,H);a.push(0xf3,0,0);for(const color of pal)a.push(...color);
  a.push(0x21,0xff,0x0b,...[... "NETSCAPE2.0"].map(c=>c.charCodeAt(0)),3,1,0,0,0);
  for(let k=0;k<frames.length;k++){
   const delay=k===frames.length-1?125:95;
   a.push(0x21,0xf9,4,4,delay&255,delay>>8,0,0);
   a.push(0x2c);push16(a,0);push16(a,0);push16(a,W);push16(a,H);a.push(0);
   a.push(4);const bytes=compress(frames[k]);for(let i=0;i<bytes.length;i+=255)a.push(Math.min(255,bytes.length-i),...bytes.slice(i,i+255));a.push(0);
  }
  a.push(0x3b);
  const alpha="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let b64="";for(let i=0;i<a.length;i+=3){const b0=a[i],b1=i+1<a.length?a[i+1]:0,b2=i+2<a.length?a[i+2]:0;const n=b0*65536+b1*256+b2;b64+=alpha[n>>18]+alpha[(n>>12)&63]+(i+1<a.length?alpha[(n>>6)&63]:"=")+(i+2<a.length?alpha[n&63]:"=")}
  return {base64:b64,size:a.length,frames:frames.length};
 }
 return {
 "docs/images/kg_extraction_pipeline.gif":make([0,1,2,3,4].map(pipeline)),
 "docs/images/kg_entity_resolution.gif":make([0,1,2,3,4].map(entity)),
 "docs/images/kg_conflicting_sources.gif":make([0,1,2,3,4].map(provenance))
 };
})();\nfor (const [name, file] of Object.entries(files)) {\n  fs.mkdirSync(path.dirname(name), {recursive:true});\n  fs.writeFileSync(name, Buffer.from(file.base64, 'base64'));\n  console.log(name + ' (' + file.size + ' bytes)');\n}\n