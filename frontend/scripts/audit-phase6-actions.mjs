import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
const root=path.resolve(import.meta.dirname,'../..');
const rows=[];
const interactive=/^(button|Button|a|input|Input|select|Select|textarea|Textarea|form|summary|Link|NextLink|Switch|Checkbox|Slider|RadioGroup|RadioGroupItem|SelectItem|SelectTrigger|NavigationMenuLink|AlertDialogAction|AlertDialogCancel|AlertDialogTrigger|AccordionTrigger|CollapsibleTrigger|MenubarItem|MenubarTrigger|ContextMenuItem|DropdownMenuItem|DropdownMenuTrigger|CommandItem|TabsTrigger|DialogClose|DialogTrigger|SheetTrigger|PopoverTrigger|Toggle|ToggleGroupItem|Controls|ControlButton)$/;
function scan(directory){
 for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
  const absolute=path.join(directory,entry.name);
  if(entry.isDirectory()){scan(absolute);continue;}
  if(!/\.tsx$/.test(entry.name)||/\.(test|spec)\.tsx$/.test(entry.name))continue;
  const text=fs.readFileSync(absolute,'utf8');const tree=ts.createSourceFile(absolute,text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  function visit(node){
   if(ts.isJsxOpeningElement(node)||ts.isJsxSelfClosingElement(node)){
    const kind=node.tagName.getText(tree);const props=node.attributes.properties;
    const attrs=Object.fromEntries(props.filter(ts.isJsxAttribute).map(p=>[p.name.getText(tree),p.initializer?.getText(tree)??'true']));
    const handlers=Object.fromEntries(Object.entries(attrs).filter(([name])=>/^on[A-Z]/.test(name)));
    if(interactive.test(kind)||Object.keys(handlers).length){
     const file=path.relative(root,absolute);const line=tree.getLineAndCharacterOfPosition(node.getStart(tree)).line+1;
     const label=(attrs['aria-label']??attrs.title??(ts.isJsxElement(node.parent)?node.parent.children.map(c=>c.getText(tree)).join(' '):kind)).replace(/\s+/g,' ').slice(0,180);
     rows.push({file,line,kind,label,handlers,disabled:attrs.disabled??null,spread:props.some(ts.isJsxSpreadAttribute)});
    }
   }
   ts.forEachChild(node,visit);
  }visit(tree);
 }
}
for(const directory of ['screens','features','components'])scan(path.join(root,'frontend/src',directory));
rows.sort((a,b)=>a.file.localeCompare(b.file)||a.line-b.line);
const output=path.join(root,'openspec/changes/phase6-runtime-readiness/action-inventory.json');
const encoded=JSON.stringify({format:'phase6-action-inventory-v1',note:'Every source control/handler; JSX loops and delegated primitives are recorded once with their expression. See action-audit-matrix.md for behavior, permissions and coverage.',controls:rows},null,2)+'\n';
if(process.argv.includes('--check')){if(!fs.existsSync(output)||fs.readFileSync(output,'utf8')!==encoded)throw Error('Action inventory is stale; run frontend/scripts/audit-actions.mjs.');}
else fs.writeFileSync(output,encoded);
console.log(`${rows.length} source controls inventoried across ${new Set(rows.map(row=>row.file)).size} files.`);
if(process.argv.includes('--summary'))for(const file of [...new Set(rows.map(row=>row.file))])console.log(file,rows.filter(row=>row.file===file).length);
