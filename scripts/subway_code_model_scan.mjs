/** Parse model reference declarations without treating comments as executable code. */
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
let input='';for await(const part of process.stdin)input+=part;
const payload=JSON.parse(input);
function scan(text){
const source=ts.createSourceFile('model.js',text,ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
const references=[];
function walk(node){
 if(ts.isPropertyAssignment(node)&&node.name.getText(source)==='ref'&&ts.isStringLiteral(node.initializer)){
  const object=node.parent,field=object.parent;
  if(ts.isPropertyAssignment(field)){
   const path=[];let current=field;
   while(current&&current!==source){if(ts.isPropertyAssignment(current))path.unshift(current.name.getText(source).replace(/^['"]|['"]$/g,''));current=current.parent;}
   const start=field.getStart(source),end=field.end;
   references.push({field:field.name.getText(source).replace(/^['"]|['"]$/g,''),path:path.join('.'),target:node.initializer.text,start_line:source.getLineAndCharacterOfPosition(start).line+1,end_line:source.getLineAndCharacterOfPosition(end).line+1,quote:text.slice(start,end)});
  }
 }
 ts.forEachChild(node,walk);
}
walk(source);return {references};
}
process.stdout.write(JSON.stringify(payload.sources?Object.fromEntries(payload.sources.map(s=>[s.key,scan(s.text)])):scan(payload.text)));
