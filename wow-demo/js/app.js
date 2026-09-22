/* ============ PROFLAG · WOW DECK — app.js ============ */
(function(){
'use strict';
const $  = (s,el)=> (el||document).querySelector(s);
const $$ = (s,el)=> Array.from((el||document).querySelectorAll(s));
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------- Масштабирование фиксированных макетов 1200×675 ---------- */
function fitScaler(){
  const ba=$('#baSlider'); if(!ba) return;
  const fits=$$('.fit',ba);
  const update=()=>{
    const s=Math.min(ba.clientWidth/1200, ba.clientHeight/675);
    fits.forEach(f=>{ f.style.transform=`translate(-50%,-50%) scale(${s})`; });
  };
  update();
  addEventListener('resize',update,{passive:true});
  if(window.ResizeObserver){ new ResizeObserver(update).observe(ba); }
}
fitScaler();

/* ---------- Волновой флаг на canvas ---------- */
function makeFlag(canvas){
  const ctx = canvas.getContext('2d');
  let W=0,H=0,dpr=1,running=false,rafId=null;
  const bands=[['#f4f6fb',0,1/3],['#2e5fa3',1/3,2/3],['#d5313e',2/3,1]];

  function resize(){
    dpr=Math.min(window.devicePixelRatio||1,2);
    W=canvas.clientWidth||canvas.parentElement.clientWidth;
    H=canvas.clientHeight||canvas.parentElement.clientHeight;
    canvas.width=W*dpr; canvas.height=H*dpr;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    draw(performance.now());
  }
  function shade(hex,k){
    const n=parseInt(hex.slice(1),16),r=n>>16&255,g=n>>8&255,b=n&255;
    const f=v=>Math.max(0,Math.min(255,Math.round(v+(k>0?(255-v)*k:v*k))));
    return `rgb(${f(r)},${f(g)},${f(b)})`;
  }
  function wave(x,t){
    return Math.sin(x*0.011 + t*1.15)*11 + Math.sin(x*0.026 - t*0.65)*5 + Math.sin(t*0.4)*3;
  }
  function draw(t){
    const time=t/1000;
    ctx.clearRect(0,0,W,H);
    const step=3;
    for(let x=0;x<=W;x+=step){
      const y=wave(x,time), y2=wave(x+step,time);
      const dy=(y2-y)/step;
      const k=Math.max(-.22,Math.min(.22,dy*.85));
      for(let bi=0;bi<3;bi++){
        const [col,b0,b1]=bands[bi];
        ctx.fillStyle=shade(col,k);
        ctx.fillRect(x, b0*H+y, step, (b1-b0)*H+1.6);
      }
    }
    const g=ctx.createLinearGradient(0,0,0,H);
    g.addColorStop(0,'rgba(6,11,22,.58)');
    g.addColorStop(.45,'rgba(6,11,22,.34)');
    g.addColorStop(1,'rgba(6,11,22,.66)');
    ctx.fillStyle=g; ctx.fillRect(0,0,W,H);
    const g2=ctx.createRadialGradient(W/2,H*.5,H*.2,W/2,H*.5,W*.75);
    g2.addColorStop(0,'rgba(6,11,22,.30)'); g2.addColorStop(1,'rgba(6,11,22,0)');
    ctx.fillStyle=g2; ctx.fillRect(0,0,W,H);
  }
  function loop(t){ if(!running) return; draw(t); rafId=requestAnimationFrame(loop); }

  window.addEventListener('resize',resize);
  resize();
  if(reduced){ draw(1200); return; }

  const io=new IntersectionObserver(es=>{
    es.forEach(e=>{
      if(e.isIntersecting && !running){ running=true; rafId=requestAnimationFrame(loop); }
      else if(!e.isIntersecting && running){ running=false; cancelAnimationFrame(rafId); }
    });
  },{threshold:.05});
  io.observe(canvas);
}
const fc=$('#flagCanvas'); if(fc) makeFlag(fc);
const fc2=$('#flagCanvas2'); if(fc2) makeFlag(fc2);

/* ---------- Счётчики ---------- */
function animateCount(el){
  const target=parseFloat(el.dataset.count);
  const prefix=el.dataset.prefix||'', suffix=el.dataset.suffix||'';
  const fmt=v=>prefix+Math.round(v).toLocaleString('ru-RU')+suffix;
  if(reduced){ el.textContent=fmt(target); return; }
  const dur=1300, t0=performance.now();
  (function tick(t){
    const p=Math.min(1,(t-t0)/dur);
    const e=1-Math.pow(1-p,3);
    el.textContent=fmt(target*e);
    if(p<1) requestAnimationFrame(tick);
  })(t0);
}

/* ---------- Слайды: reveal + триггеры ---------- */
const slides=$$('.slide');

const slideIO=new IntersectionObserver(es=>{
  es.forEach(e=>{
    if(!e.isIntersecting) return;
    const s=e.target;
    if(!s.classList.contains('on')){
      s.classList.add('on');
      $$('[data-count]',s).forEach(animateCount);
      if($('#baSlider',s)) introSweep();
      if($('#chart',s)) drawChart();
    }
  });
},{threshold:.35});
slides.forEach(s=>slideIO.observe(s));

/* ---------- Dots nav ---------- */
const dotsBox=$('#dots');
slides.forEach((s,i)=>{
  const b=document.createElement('button');
  b.title=s.dataset.dot||('Слайд '+(i+1));
  b.setAttribute('aria-label',b.title);
  b.addEventListener('click',()=>{curIdx=i;s.scrollIntoView({behavior:reduced?'auto':'smooth'});});
  dotsBox.appendChild(b);
});
const dotBtns=$$('button',dotsBox);
const dotIO=new IntersectionObserver(es=>{
  es.forEach(e=>{
    if(e.isIntersecting){
      dotBtns.forEach(b=>b.classList.remove('act'));
      dotBtns[slides.indexOf(e.target)].classList.add('act');
    }
  });
},{threshold:.55});
slides.forEach(s=>dotIO.observe(s));

/* ---------- Клавиатура ---------- */
let curIdx=0;
function goSlide(d){
  curIdx=Math.max(0,Math.min(slides.length-1,curIdx+d));
  slides[curIdx].scrollIntoView({behavior:reduced?'auto':'smooth'});
}
document.addEventListener('keydown',e=>{
  if(['ArrowDown','PageDown',' '].includes(e.key)){ e.preventDefault(); goSlide(1); }
  if(['ArrowUp','PageUp'].includes(e.key)){ e.preventDefault(); goSlide(-1); }
  if(e.key==='Home'){ e.preventDefault(); slides[0].scrollIntoView({behavior:'smooth'}); }
  if(e.key==='End'){ e.preventDefault(); slides[slides.length-1].scrollIntoView({behavior:'smooth'}); }
});

/* ---------- Прогресс-бар ---------- */
const pBar=$('#progressBar');
addEventListener('scroll',()=>{
  const h=document.documentElement;
  const p=h.scrollTop/(h.scrollHeight-h.clientHeight);
  pBar.style.width=(p*100).toFixed(2)+'%';
},{passive:true});

/* ---------- Слайдер До/После ---------- */
const ba=$('#baSlider');
function setPos(p){ p=Math.max(5,Math.min(95,p)); ba.style.setProperty('--pos',p+'%'); }
let dragging=false;
function posFromEvent(e){
  const r=ba.getBoundingClientRect();
  const x=(e.touches?e.touches[0].clientX:e.clientX)-r.left;
  return x/r.width*100;
}
ba.addEventListener('pointerdown',e=>{ dragging=true; ba.setPointerCapture(e.pointerId); setPos(posFromEvent(e)); });
ba.addEventListener('pointermove',e=>{ if(dragging) setPos(posFromEvent(e)); });
addEventListener('pointerup',()=>dragging=false);
let swept=false;
function introSweep(){
  if(swept||reduced) return; swept=true;
  const seq=[[50,0],[30,450],[64,950],[45,1450],[50,1900]];
  seq.forEach(([p,t])=>setTimeout(()=>setPos(p),t));
}

/* ---------- График прогноза ---------- */
function drawChart(){
  const line=$('#linePath'), area=$('#areaPath'), dotsG=$('#chartDots');
  if(!line||line.dataset.done) return; line.dataset.done=1;
  const data=[100,103,118,142,170,205,245,290,330,368,400];
  const x0=30,x1=590,yBase=240,scale=(240-40)/(420-90);
  const pts=data.map((v,i)=>[x0+(x1-x0)*i/(data.length-1), yBase-(v-90)*scale]);
  let d=`M${pts[0][0]},${pts[0][1]}`;
  for(let i=1;i<pts.length;i++){
    const [px,py]=pts[i-1],[cx,cy]=pts[i];
    const mx=(px+cx)/2;
    d+=` C${mx},${py} ${mx},${cy} ${cx},${cy}`;
  }
  line.setAttribute('d',d);
  area.setAttribute('d',d+` L${x1},${yBase} L${x0},${yBase} Z`);
  if(reduced){
    area.setAttribute('opacity','1');
    addDots();
    return;
  }
  const len=line.getTotalLength();
  line.style.strokeDasharray=len;
  line.style.strokeDashoffset=len;
  line.getBoundingClientRect();
  line.style.transition='stroke-dashoffset 2.2s cubic-bezier(.3,.6,.3,1) .2s';
  line.style.strokeDashoffset='0';
  setTimeout(()=>{ area.style.transition='opacity 1s'; area.setAttribute('opacity','1'); addDots(); },1400);
  function addDots(){
    pts.forEach(([x,y],i)=>{
      const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
      c.setAttribute('cx',x); c.setAttribute('cy',y);
      c.setAttribute('r',i===pts.length-1?6:3.5);
      c.setAttribute('fill',i===pts.length-1?'#e0384a':'#3d7bfa');
      c.style.opacity=0; c.style.transition='opacity .4s';
      dotsG.appendChild(c);
      setTimeout(()=>c.style.opacity=1, 60*i);
    });
  }
}
})();
