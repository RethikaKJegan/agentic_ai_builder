import {expect,it} from "vitest";
import {semanticCanvas} from "./semantic-canvas";
import {semanticCanvasLayout} from "./semantic-canvas-layout";
import type {SemanticView} from "@/api/semantic-kg";
import fixture from "../../e2e/fixtures/semantic-kg.json";
it("lays out connected entities and relationship labels without overlapping bodies",()=>{
 const canvas=semanticCanvas(structuredClone(fixture) as SemanticView),layout=semanticCanvasLayout(canvas);
 const boxes=canvas.entities.map(e=>{const p=layout.node(e.entity_id);return {x:p.x,y:p.y,w:220,h:104};});
 for(const edge of canvas.relationships){const route=layout.edge({v:edge.source_entity_id,w:edge.target_entity_id,name:edge.relationship_id});expect(route.points.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y))).toBe(true);boxes.push({x:route.x,y:route.y,w:174,h:58});}
 for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i]!,b=boxes[j]!;expect(Math.abs(a.x-b.x)>=(a.w+b.w)/2||Math.abs(a.y-b.y)>=(a.h+b.h)/2).toBe(true);}
 expect(layout.graph().width).toBeGreaterThan(0);expect(layout.graph().height).toBeGreaterThan(0);
});
it("handles an empty filtered canvas",()=>{const layout=semanticCanvasLayout({entities:[],relationships:[],resolvedIdentifiers:0});expect(layout.graph()).toEqual({width:500,height:320});});
