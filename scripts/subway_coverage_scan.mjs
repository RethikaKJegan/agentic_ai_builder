/** Static inventory only: never imports or evaluates supplied application code. */
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
let raw='';for await(const part of process.stdin)raw+=part;
function scan(text){
 const sf=ts.createSourceFile('archive.js',text,ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
 const models=[],references=[],fields=[],guards=[];
 const name=n=>n?.getText(sf).replace(/^['"]|['"]$/g,'');
 const lines=n=>({start_line:sf.getLineAndCharacterOfPosition(n.getStart(sf)).line+1,end_line:sf.getLineAndCharacterOfPosition(n.end).line+1});
 function schemaOf(n){while(n&&!ts.isVariableDeclaration(n))n=n.parent;return n?name(n.name):null;}
 function walk(n){
  if(ts.isCallExpression(n)&&ts.isPropertyAccessExpression(n.expression)&&n.expression.name.text==='model'&&n.arguments.length>=2&&ts.isStringLiteral(n.arguments[0]))models.push({name:n.arguments[0].text,schema:name(n.arguments[1]),...lines(n),quote:n.getText(sf)});
  if(ts.isPropertyAssignment(n)&&name(n.name)==='ref'){
   let f=n.parent.parent;while(f&&!ts.isPropertyAssignment(f)&&f!==sf)f=f.parent;
   if(f&&f!==sf){const path=[];let p=f;while(p&&p!==sf){if(ts.isPropertyAssignment(p))path.unshift(name(p.name));p=p.parent;}
    references.push({field:name(f.name),path:path.join('.'),schema:schemaOf(n),target:ts.isStringLiteral(n.initializer)?n.initializer.text:null,dynamic:!ts.isStringLiteral(n.initializer),...lines(n),quote:n.getText(sf)});}
  }
  if(ts.isPropertyAssignment(n)&&name(n.name)==='type'&&ts.isIdentifier(n.initializer)){
   let f=n.parent.parent;
   if(ts.isPropertyAssignment(f))fields.push({name:name(f.name),type:n.initializer.text,schema:schemaOf(n),...lines(n),quote:n.getText(sf)});
  }
  if(ts.isThrowStatement(n))guards.push({...lines(n),kind:'throw',quote:n.getText(sf)});
  ts.forEachChild(n,walk);
 }
 walk(sf);return {models,references,fields,guards};
}
const input=JSON.parse(raw);process.stdout.write(JSON.stringify(Object.fromEntries(input.sources.map(s=>[s.key,scan(s.text)]))));
