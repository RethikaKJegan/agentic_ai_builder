import type { SemanticCanvas } from "./semantic-canvas";
type Point = { x: number; y: number };
type Particle = Point & { id: string; width: number; height: number; dx: number; dy: number };
/** Position the existing canvas with occupied label space and deterministic collision separation. */
export function semanticCanvasLayout(canvas: SemanticCanvas) {
  const particles: Particle[] = [], byId = new Map<string, Particle>();
  const columns = Math.max(1, Math.ceil(Math.sqrt(canvas.entities.length * 1.65)));
  const add = (id: string, x: number, y: number, width: number, height: number) => {
    const p = { id, x, y, width, height, dx: 0, dy: 0 }; particles.push(p); byId.set(id,p); return p;
  };
  canvas.entities.forEach((n,i) => add(n.entity_id, (i % columns) * 330, Math.floor(i / columns) * 230, 220, 104));
  const springs: [Particle,Particle][] = [];
  canvas.relationships.forEach((e,i) => {
    const a=byId.get(e.source_entity_id)!, b=byId.get(e.target_entity_id)!;
    const p=add(`label:${e.relationship_id}`, (a.x+b.x)/2 + ((i%3)-1)*40, (a.y+b.y)/2 + (i%2?45:-45), 174, 58);
    springs.push([a,p],[p,b]);
  });
  const areaWidth=Math.max(700,columns*310),areaHeight=Math.max(500,Math.ceil((canvas.entities.length+canvas.relationships.length)/columns)*125);
  const centerX=areaWidth/2,centerY=areaHeight/2;
  for(let iteration=0;iteration<360;iteration++) {
    for(const p of particles) { p.dx=(centerX-p.x)*0.02; p.dy=(centerY-p.y)*0.02; }
    for(let i=0;i<particles.length;i++) for(let j=i+1;j<particles.length;j++) {
      const a=particles[i]!,b=particles[j]!;let x=b.x-a.x,y=b.y-a.y;
      if(Math.abs(x)+Math.abs(y)<0.1) { x=(i%2?1:-1)*0.5; y=(j%2?1:-1)*0.5; }
      const distance=Math.max(1,Math.hypot(x,y)), repulsion=1150/distance;
      const rx=x/distance*repulsion,ry=y/distance*repulsion;a.dx-=rx;a.dy-=ry;b.dx+=rx;b.dy+=ry;
      const ox=(a.width+b.width)/2+22-Math.abs(x),oy=(a.height+b.height)/2+20-Math.abs(y);
      if(ox>0&&oy>0) {
        if(ox<oy) { const push=Math.sign(x)*ox*0.65; a.dx-=push;b.dx+=push; }
        else { const push=Math.sign(y)*oy*0.65; a.dy-=push;b.dy+=push; }
      }
    }
    for(const [a,b] of springs) {
      const x=b.x-a.x,y=b.y-a.y,distance=Math.max(1,Math.hypot(x,y)),force=(distance-220)*0.025;
      a.dx+=x/distance*force;a.dy+=y/distance*force;b.dx-=x/distance*force;b.dy-=y/distance*force;
    }
    const step=iteration<240?16:6;
    for(const p of particles) { p.x=Math.max(p.width/2,Math.min(areaWidth-p.width/2,p.x+Math.max(-step,Math.min(step,p.dx)))); p.y=Math.max(p.height/2,Math.min(areaHeight-p.height/2,p.y+Math.max(-step,Math.min(step,p.dy)))); }
  }
  for(let iteration=0;iteration<160;iteration++) {
    let moved=false;
    for(let i=0;i<particles.length;i++) for(let j=i+1;j<particles.length;j++) {
      const a=particles[i]!,b=particles[j]!,x=b.x-a.x,y=b.y-a.y;
      const ox=(a.width+b.width)/2+12-Math.abs(x),oy=(a.height+b.height)/2+12-Math.abs(y);
      if(ox>0&&oy>0) { moved=true; if(ox<oy) { const d=(x>=0?1:-1)*(ox/2+0.1);a.x-=d;b.x+=d; } else { const d=(y>=0?1:-1)*(oy/2+0.1);a.y-=d;b.y+=d; } }
    }
    if(!moved)break;
  }
  const left=Math.min(0,...particles.map(p=>p.x-p.width/2))-45,top=Math.min(0,...particles.map(p=>p.y-p.height/2))-45;
  for(const p of particles) {p.x-=left;p.y-=top;}
  const width=Math.max(500,...particles.map(p=>p.x+p.width/2+45)),height=Math.max(320,...particles.map(p=>p.y+p.height/2+45));
  const boundary=(node:Particle,toward:Point):Point=>{
    const x=toward.x-node.x,y=toward.y-node.y;
    const kind=canvas.entities.find(e=>e.entity_id===node.id)?.kind;
    const scale=kind === "entity" ? 1/Math.max(0.001,Math.hypot(x/105,y/47)) : 1/Math.max(Math.abs(x)/105,Math.abs(y)/36,0.001);
    return {x:node.x+x*scale,y:node.y+y*scale};
  };
  const routes=new Map(canvas.relationships.map(e=>{
    const label=byId.get(`label:${e.relationship_id}`)!,a=byId.get(e.source_entity_id)!,b=byId.get(e.target_entity_id)!;
    return [e.relationship_id,{x:label.x,y:label.y,points:[boundary(a,label),{x:label.x,y:label.y},boundary(b,label)]}] as const;
  }));
  return { graph:()=>({width,height}), node:(id:string)=>byId.get(id)!, edge:({name}:{v:string;w:string;name:string})=>routes.get(name)! };
}
