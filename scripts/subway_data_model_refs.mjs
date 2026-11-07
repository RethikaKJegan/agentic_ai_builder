/** Resolve ref paths from a declared model's root schema; never execute source. */
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
let raw='';for await(const chunk of process.stdin)raw+=chunk;
function scan(text){
 const sf=ts.createSourceFile('archive.js',text,ts.ScriptTarget.Latest,true,ts.ScriptKind.JS),vars=new Map(),models=[];
 const name=n=>n?.getText(sf).replace(/^['"]|['"]$/g,'');
 function collect(n){if(ts.isVariableDeclaration(n)&&n.initializer)vars.set(name(n.name),n.initializer);if(ts.isCallExpression(n)&&ts.isPropertyAccessExpression(n.expression)&&n.expression.name.text==='model'&&n.arguments.length>=2&&ts.isStringLiteral(n.arguments[0]))models.push({name:n.arguments[0].text,schema:name(n.arguments[1])});ts.forEachChild(n,collect);}collect(sf);
 function walk(node,path,seen,refs){
  if(!node||seen.has(node))return;seen=new Set(seen);seen.add(node);
  if(ts.isIdentifier(node)){walk(vars.get(node.text),path,seen,refs);return;}
  if(ts.isCallExpression(node)||ts.isNewExpression(node)){const expr=node.expression.getText(sf);if(/(?:^|\.)Schema$/.test(expr))walk(node.arguments?.[0],path,seen,refs);return;}
  if(ts.isArrayLiteralExpression(node)){for(const item of node.elements)walk(item,path+'[]',seen,refs);return;}
  if(!ts.isObjectLiteralExpression(node))return;
  const props=node.properties.filter(ts.isPropertyAssignment);const byName=new Map(props.map(p=>[name(p.name),p]));
  const ref=byName.get('ref');
  if(ref){if(ts.isStringLiteral(ref.initializer))refs.push({path,target:ref.initializer.text,quote:ref.getText(sf),start_line:sf.getLineAndCharacterOfPosition(ref.getStart(sf)).line+1,end_line:sf.getLineAndCharacterOfPosition(ref.end).line+1});return;}
  if(byName.has('type')){walk(byName.get('type').initializer,path,seen,refs);return;}
  for(const p of props)walk(p.initializer,path?path+'.'+name(p.name):name(p.name),seen,refs);
 }
 return models.map(m=>{const refs=[];walk(vars.get(m.schema),'',new Set(),refs);return {...m,references:refs};});
}
const input=JSON.parse(raw);process.stdout.write(JSON.stringify(Object.fromEntries(input.sources.map(s=>[s.key,scan(s.text)]))));
