/** Background-only integration test. Run against build_review.py's example fixture
 * copied into the already-open disposable armarium25-starter. Requires the selected
 * community plugin enabled. Mounts transparent, noninteractive Bases controllers;
 * never opens a note, focuses a window, or follows a link. Node 22 + PyYAML required.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {connect} from './observe.mjs';
const python=process.env.ARMARIUM_PYTHON || 'python3';
const definitions=JSON.parse(execFileSync(python,['-c',`import json,yaml,pathlib;print(json.dumps({p.stem:yaml.safe_load(p.read_text()) for p in pathlib.Path('vaults/starter/reference/views').glob('*.base')}))`]));
// Exercise wrapping at a bounded width instead of allowing automatic column expansion.
definitions['prepared-clues'].views[0].columnSize={'formula.text':250};
const o=await connect('armarium25-starter');
const evidence={method:'Real Bases controllers mounted transparent and noninteractive in disposable vault; source edits observed without query reruns; navigation intercepted; no focus or tab changes',checks:[]};
const originals=new Map();
const session='campaigns/campaign_1/sessions/S-1-901.md';
const clue='campaigns/campaign_1/clues/C-1-9001.md';
const keeper='content/Review/Signal Keeper.md';
async function waitFor(predicate){for(let i=0;i<80;i++){if(await o.js(predicate))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out: '+predicate);}
async function save(path){if(!originals.has(path))originals.set(path,await o.js(`app.vault.read(app.vault.getFileByPath(${JSON.stringify(path)}))`));}
async function edit(path,values){await save(path);await o.js(`app.fileManager.processFrontMatter(app.vault.getFileByPath(${JSON.stringify(path)}),fm=>Object.assign(fm,${JSON.stringify(values)}))`);}
async function mount(name,path,view){
 await o.js(`(async()=>{const t=window.armariumLiveTest;t.c?.unload();t.host?.remove();const host=document.body.createDiv();host.style.cssText='position:fixed;left:0;top:0;width:1100px;height:900px;opacity:0;pointer-events:none;z-index:-1000';t.host=host;const c=t.c=new t.Controller(app,t.plugin,host,app.vault.getFileByPath(${JSON.stringify(path)}));c.load();c.setQuery(t.Query.parse(${JSON.stringify(definitions[name])}));${view?`c.selectView(${JSON.stringify(view)});`:''}return true;})()`);
 await waitFor(`window.armariumLiveTest.c.view && window.armariumLiveTest.host.querySelector('.bases-thead')?.innerText.length > 0`);
}
async function record(name){const r=await o.js(`(()=>{const {c,host}=window.armariumLiveTest;return {headers:host.querySelector('.bases-thead').innerText.trim().split('\\n'),paths:c.view.data.groupedData.flatMap(g=>g.entries.map(e=>e.file.path)),rows:[...host.querySelectorAll('.bases-tbody .bases-tr')].map(x=>x.innerText),links:[...host.querySelectorAll('.bases-tbody .internal-link')].map(a=>({label:a.innerText,target:a.dataset.href || a.title})),errors:[...c.errors],error:c.error};})()`);assert.deepEqual(r.errors,[]);assert.equal(r.error,null);evidence.checks.push({name,...r});return r;}
async function paths(expected){await waitFor(`JSON.stringify(window.armariumLiveTest.c.view.data.groupedData.flatMap(g=>g.entries.map(e=>e.file.path))) === ${JSON.stringify(JSON.stringify(expected))}`);}
try{
 evidence.environment=await o.js(`(()=>{if(!app.plugins.plugins['frontmatter-markdown-links'])throw Error('Enable Frontmatter Markdown Links first');const original=app.workspace.activeLeaf.view.previewMode._children.find(x=>x.controller).controller;window.armariumLiveProbe?.c.unload();window.armariumLiveProbe?.host.remove();delete window.armariumLiveProbe;window.armariumLiveTest={Controller:original.constructor,Query:original.query.constructor,plugin:original.plugin};return {title:document.title,activeFile:app.workspace.getActiveFile().path,plugin:app.plugins.manifests['frontmatter-markdown-links'].version,enabled:[...app.plugins.enabledPlugins]};})()`);
 await mount('prepared-clues',session);
 await paths(['campaigns/campaign_1/clues/C-1-9002.md',clue]);
 let r=await record('Explicit preparation order; closed statuses also selectable');assert.deepEqual(r.headers,['ID','Text']);
 await edit(clue,{text:'Meet [[content/Review/Quay|the quay]] and [[content/Review/Visitors/Signal Keeper|the visitor]].\nLiteral <b> & quotes "here".',status:'[[Revealed]]'});
 await waitFor(`window.armariumLiveTest.host.innerText.includes('the visitor')`);
 r=await record('Canonical text updates live; aliases and multiline prose');assert(r.rows.some(x=>x.includes('Literal <b> & quotes "here".')));assert(!r.rows.some(x=>x.includes('[[content/Review')));
 const spacing=await o.js(`(()=>{const row=[...window.armariumLiveTest.host.querySelectorAll('.bases-tbody .bases-tr')].find(r=>r.innerText.includes('the visitor'));const cell=row.querySelector('[data-property="formula.text"]');const walker=document.createTreeWalker(cell,NodeFilter.SHOW_TEXT);const tops=[];let n;while(n=walker.nextNode()){for(let i=0;i<n.length;i++){if(!n.textContent[i].trim())continue;const range=document.createRange();range.setStart(n,i);range.setEnd(n,i+1);const rect=range.getBoundingClientRect();if(rect.height)tops.push(rect.top);}}const lines=[...new Set(tops.map(y=>Math.round(y)))].sort((a,b)=>a-b);return {html:cell.innerHTML,width:cell.getBoundingClientRect().width,whiteSpace:getComputedStyle(cell.firstElementChild).whiteSpace,rowHeight:row.getBoundingClientRect().height,fontSize:parseFloat(getComputedStyle(cell).fontSize),lineTops:lines,maxLineGap:Math.max(0,...lines.slice(1).map((y,i)=>y-lines[i])),editableFragments:cell.querySelectorAll('[contenteditable="true"]').length};})()`);
 assert(spacing.rowHeight <= spacing.fontSize*5,'Short prose should not occupy an eight-line row');
 assert(spacing.lineTops.length >= 2,'Spacing probe must exercise wrapped prose');
 assert(spacing.maxLineGap <= spacing.fontSize*2,'Prose fragments must flow with normal line spacing');
 assert.equal(spacing.editableFragments,0,'Prose display must avoid nested property-editor fragments');
 evidence.checks.push({name:'Compact rows and continuous prose layout',...spacing});
 const clicks=await o.js(`(async()=>{const calls=[],orig=app.workspace.openLinkText;app.workspace.openLinkText=(...args)=>{calls.push(args);return Promise.resolve()};try{for(const a of window.armariumLiveTest.host.querySelectorAll('.bases-td[data-property="formula.text"] .internal-link')){for(const type of ['mousedown','mouseup','click'])a.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true,button:0}));}await Promise.resolve();return calls;}finally{app.workspace.openLinkText=orig;}})()`);
 assert(clicks.some(x=>x[0]==='content/Review/Visitors/Signal Keeper'));evidence.checks.push({name:'Embedded prose links invoke internal navigation, intercepted',calls:clicks});
 await edit(session,{prepared_clues:['[[campaigns/campaign_1/clues/C-1-9001]]','[[campaigns/campaign_1/clues/C-1-9002|Second]]']});
 await paths([clue,'campaigns/campaign_1/clues/C-1-9002.md']);await record('Selection reorder updates live');
 await edit(session,{prepared_clues:[]});await paths([]);await waitFor(`window.armariumLiveTest.host.querySelectorAll('.bases-tbody .bases-tr').length === 0`);await record('Removing last selection removes rendered rows');
 await edit(session,{prepared_clues:['[[campaigns/campaign_2/clues/C-2-9001]]','[[content/Review/Quay]]','[[missing]]','[[campaigns/campaign_1/clues/C-1-9001]]','[[campaigns/campaign_1/clues/C-1-9001|duplicate]]']});await paths([clue]);await record('Wrong campaign/type/missing selections excluded; duplicates collapse');
 await mount('prepared-npcs',session);await paths(['content/Review/Visitors/Signal Keeper.md',keeper]);r=await record('NPC preparation excludes Events-only records and preserves selection order');assert.deepEqual(r.headers,['Name','Summary']);
 await edit(keeper,{summary:'Changed live summary referencing [[content/Review/Quay|the quay]].'});await waitFor(`window.armariumLiveTest.host.innerText.includes('Changed live summary')`);await record('Canonical Content summary updates live');
 await mount('prepared-locations',session);await paths(['content/Review/Quay.md']);r=await record('Location preparation');assert.deepEqual(r.headers,['Location','Description']);
 await edit(clue,{status:'[[Pending]]'});
 await mount('content-clues',keeper);await paths([clue]);r=await record('Active Clues uses canonical subjects; mixed text links render');assert.deepEqual(r.headers,['ID','Text']);assert(r.links.some(x=>x.target==='content/Review/Visitors/Signal Keeper'));
 await edit(keeper,{view_campaign:'campaign_2'});await paths(['campaigns/campaign_2/clues/C-2-9001.md']);await record('Content campaign switch updates live');
 await edit(keeper,{view_campaign:'campaign_1'});await paths([clue]);
 await edit(clue,{subjects:[]});await paths([]);await waitFor(`window.armariumLiveTest.host.querySelectorAll('.bases-tbody .bases-tr').length===0`);await record('Removing final subject clears Active Clues table');
 await mount('clue-index','campaigns/campaign_1/reference/indexes/Clues.md','Active');
 await paths(['campaigns/campaign_1/clues/C-1-0003.md','campaigns/campaign_1/clues/C-1-0004.md',clue,'campaigns/campaign_1/clues/C-1-9002.md']);r=await record('Active index campaign isolation and original columns');assert.deepEqual(r.headers,['ID','Status','Last Session','Text']);
 await o.js(`window.armariumLiveTest.c.selectView('Closed')`);await paths(['campaigns/campaign_1/clues/C-1-0001.md','campaigns/campaign_1/clues/C-1-0002.md',...['9003','9004','9005','9006'].map(n=>'campaigns/campaign_1/clues/C-1-'+n+'.md')]);await record('Closed index includes all four closed statuses');
 await mount('clue-sessions',clue);await paths(['campaigns/campaign_1/sessions/S-1-902.md','campaigns/campaign_1/sessions/S-1-903.md',session]);r=await record('Clue Sessions sorted by date and number; nested/cross-campaign decoys excluded');assert.deepEqual(r.headers,['Session','Date']);
 // Check unselected templates and the real example's preparation, not only synthetic rows.
 for(const kind of ['clues','locations','npcs']){
  await mount('prepared-'+kind,'reference/templates/Session.md');await paths([]);await record('Empty Session template: '+kind);
 }
 for(const number of ['001','002','003']){
  const path='campaigns/campaign_1/sessions/S-1-'+number+'.md';
  const selected=await o.js(`app.metadataCache.getFileCache(app.vault.getFileByPath(${JSON.stringify(path)})).frontmatter`);
  for(const kind of ['clues','locations','npcs']){
   const expected=await o.js(`(${JSON.stringify(selected['prepared_'+kind])}).map(v=>app.metadataCache.getFirstLinkpathDest(v.slice(2,-2).split('|')[0],${JSON.stringify(path)}).path)`);
   await mount('prepared-'+kind,path);await paths(expected);await record('Example '+number+' preparation: '+kind);
  }
 }
 const notes=originals.get(session).split('# Notes\n')[1];assert.equal(await o.js(`(await app.vault.read(app.vault.getFileByPath(${JSON.stringify(session)}))).split('# Notes\\n')[1]`),notes);
 assert.equal(await o.js('app.workspace.getActiveFile().path'),evidence.environment.activeFile);
 evidence.checks.push({name:'Notes/Events/Loot unchanged; active tab unchanged',pass:true});
}finally{
 for(const [path,text] of originals)await o.js(`app.vault.modify(app.vault.getFileByPath(${JSON.stringify(path)}),${JSON.stringify(text)})`);
 await o.js(`(()=>{const t=window.armariumLiveTest;t?.c?.unload();t?.host?.remove();delete window.armariumLiveTest;return true;})()`);
 o.close();
}
const output=process.argv[2] || '/private/tmp/armarium25-live-tables.json';await fs.writeFile(output,JSON.stringify(evidence,null,2)+'\n');console.log(`${evidence.checks.length} live checks passed; ${output}`);
