// Native Canvas drawing utilities for these two films; not an animation object API.
export const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
export const ease=x=>1-Math.pow(1-clamp(x),3);
export const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
export const mix=(a,b,t)=>a+(b-a)*t;
export const fontReady=(async()=>{
 const f=new FontFace('Studio','url(/assets/NotoSansTC-VF.ttf)',{weight:'100 900'});
 await f.load();document.fonts.add(f);await document.fonts.load('700 48px Studio');
})();
export function surface(canvas,ctx){
 if(canvas.width!==ctx.width||canvas.height!==ctx.height){canvas.width=ctx.width;canvas.height=ctx.height}
 const g=canvas.getContext('2d');g.setTransform(ctx.width/1280,0,0,ctx.height/720,0,0);
 g.globalAlpha=1;g.textBaseline='alphabetic';g.lineCap='round';g.lineJoin='round';
 window.kinesmithDiagnostics=[];return g;
}
export function text(g,s,x,y,size=32,color='#172b25',weight=500,align='left'){
 g.font=`${weight} ${size}px Studio`;g.fillStyle=color;g.textAlign=align;
 const metrics=g.measureText(s),w=metrics.width,left=align==='center'?x-w/2:align==='right'?x-w:x;
 const m=g.getTransform(),scale=g.canvas.width/1280;
 const corners=[[left,y-metrics.actualBoundingBoxAscent],[left+w,y-metrics.actualBoundingBoxAscent],
                [left,y+metrics.actualBoundingBoxDescent],[left+w,y+metrics.actualBoundingBoxDescent]]
                .map(([xx,yy])=>[(m.a*xx+m.c*yy+m.e)/scale,(m.b*xx+m.d*yy+m.f)/scale]);
 const xs=corners.map(p=>p[0]),ys=corners.map(p=>p[1]);
 if(g.globalAlpha>.99&&(Math.min(...xs)<18||Math.max(...xs)>1262||Math.min(...ys)<12||Math.max(...ys)>704))
  window.kinesmithDiagnostics.push({type:'text_bounds',text:s,left:Math.min(...xs),right:Math.max(...xs),top:Math.min(...ys),bottom:Math.max(...ys)});
 g.fillText(s,x,y);g.textAlign='left';
}
export function rect(g,x,y,w,h,r,color){g.beginPath();g.roundRect(x,y,w,h,r);g.fillStyle=color;g.fill()}
export function line(g,x,y,xx,yy,color,width=2){g.beginPath();g.moveTo(x,y);g.lineTo(xx,yy);g.strokeStyle=color;g.lineWidth=width;g.stroke()}
export function dot(g,x,y,r,color){g.beginPath();g.arc(x,y,r,0,Math.PI*2);g.fillStyle=color;g.fill()}
export function reveal(g,t,delay,draw){const p=ease((t-delay)/.65);g.save();g.globalAlpha=p;g.translate(0,28*(1-p));draw(p);g.restore()}
export function chip(g,s,x,y,color,ink='#152a25',w=180){rect(g,x,y,w,42,21,color);text(g,s,x+w/2,y+28,18,ink,600,'center')}
export function footer(g,brand,index,t,paper,ink){
 text(g,brand,64,683,15,ink,600);text(g,`${String(index+1).padStart(2,'0')} / 08`,1216,683,15,ink,500,'right');
 g.fillStyle=paper;g.fillRect(64,700,1152,2);g.fillStyle=ink;g.fillRect(64,700,1152*clamp((index*6+t)/48),2);
}
export function arrow(g,x,y,xx,yy,color,width=3){line(g,x,y,xx,yy,color,width);const a=Math.atan2(yy-y,xx-x);line(g,xx,yy,xx-12*Math.cos(a-.5),yy-12*Math.sin(a-.5),color,width);line(g,xx,yy,xx-12*Math.cos(a+.5),yy-12*Math.sin(a+.5),color,width)}
export function check(g,x,y,color,scale=1){g.save();g.translate(x,y);g.scale(scale,scale);line(g,-10,0,-2,9,color,4);line(g,-2,9,15,-12,color,4);g.restore()}
