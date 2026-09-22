/** Real Bases renderer, invisible DOM, no note navigation or app focus. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {connect} from './observe.mjs';
const o=await connect('armarium25-starter');
const sentence='The [[content/Free Pilots Assembly|Free Pilots Assembly]] holds a second copy of [[campaigns/campaign_1/content/Shoal Chart|Shoal Chart]], including its pencilled tide marks for a rendezvous beyond [[content/The Red Teeth|The Red Teeth]].';
try {
 const result=await o.js(`(async()=>{
 const original=app.workspace.activeLeaf.view.previewMode._children.find(x=>x.controller).controller;
 const host=document.body.createDiv({cls:'bases-view'});host.style.cssText='position:fixed;top:0;left:0;opacity:0;pointer-events:none;z-index:-1000';
 const table=host.createDiv({cls:'bases-table-container mod-multiline'});
 const file=app.workspace.getActiveFile();
 const q=original.query.constructor.parse({formulas:{text:${JSON.stringify(JSON.stringify(sentence))},summary:${JSON.stringify(JSON.stringify(sentence))}},views:[{type:'table',name:'probe',order:['formula.text','formula.summary']}]});
 const ctx=new original.ctx.constructor(app,null,q.formulas,file),entry=new original.ctx.local.constructor(ctx,file);entry.note.get('type');
 const records=[];
 function positions(el){const out=[],walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),box=el.getBoundingClientRect();let n;while(n=walker.nextNode()){for(let i=0;i<n.length;i++){if(!n.textContent[i].trim())continue;const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+1);const b=r.getBoundingClientRect();out.push({char:n.textContent[i],x:b.x-box.x,y:b.y-box.y});}}return out;}
 try{
 for(const enabled of [false,true]){
 app.customCss.setCssEnabledStatus('armarium-prose',enabled);await app.customCss.loadSnippets();
 for(const field of ['text','summary'])for(const width of [250,600,1000]){
 const cell=table.createDiv({cls:'bases-td',attr:{'data-property':'formula.'+field}});cell.style.width=width+'px';const actual=cell.createDiv({cls:'bases-table-cell bases-rendered-value'});original.view.createRenderer('formula.'+field,actual).render(entry);
 actual.style.fontSize='15px';
 const reference=actual.cloneNode(false);reference.textContent=actual.textContent;reference.style.display='block';reference.style.whiteSpace='pre-wrap';reference.style.overflowWrap='anywhere';cell.appendChild(reference);
 const a=positions(actual),b=positions(reference);const mismatches=a.filter((p,i)=>!b[i]||p.char!==b[i].char||Math.abs(p.x-b[i].x)>2||Math.abs(p.y-b[i].y)>2).length;
 records.push({enabled,field,width,display:getComputedStyle(actual).display,characters:a.length,referenceCharacters:b.length,mismatches,links:actual.querySelectorAll('.internal-link').length,text:actual.textContent});cell.remove();
 }
 }
 return records;
 }finally{app.customCss.setCssEnabledStatus('armarium-prose',true);await app.customCss.loadSnippets();host.remove();}
 })()`);
 assert(result.filter(r=>!r.enabled).some(r=>r.mismatches>0),'Negative control should reproduce broken flex flow');
 for(const r of result.filter(r=>r.enabled)){assert.equal(r.mismatches,0,JSON.stringify(r));assert.equal(r.characters,r.referenceCharacters);assert.equal(r.links,3);assert(r.text.startsWith('The Free Pilots Assembly holds a second copy of Shoal Chart,'));}
 await fs.writeFile(process.argv[2]||'/private/tmp/prose-layout.json',JSON.stringify({method:'Actual Bases renderer; character rectangles compared to plain paragraph reference. Snippet off is a negative control; no focus/navigation.',checks:result},null,2)+'\n');
 console.log('6 inline layout checks passed; 6 negative controls reproduced flex layout.');
}finally{o.close()}
