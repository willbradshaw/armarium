/** Background-only probe: actual Bases parser and cell renderer, hidden DOM.
 * Requires the disposable armarium25-starter to be open on port 9225 with a Base
 * controller already loaded. Never opens a note, requests focus, or navigates.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {connect} from './observe.mjs';

const formula = String.raw`html(escapeHTML(if(note.text, note.text.toString(), "")).replace(/\[\[([^|\]\n]+)\|([^\]\n]+)\]\]/g, '<a class="internal-link" data-href="$1" href="$1">$2</a>').replace(/\[\[([^\]\n]+)\]\]/g, '<a class="internal-link" data-href="$1" href="$1">$1</a>').replace(/\n/g, '<br>'))`;
const samples = [
  {name:'bare links',text:'Meet [[reference/types/Clue]] and [[reference/types/Content]].',labels:['reference/types/Clue','reference/types/Content']},
  {name:'aliases and duplicate basenames',text:'[[reference/types/Clue|type]] versus [[reference/templates/Clue|template]].',labels:['type','template']},
  {name:'heading and extension',text:'[[reference/types/Content.md#Fields|fields]]',labels:['fields']},
  {name:'escaping and multiline',text:'Literal <script>alert(1)</script> & "quotes".\n[[reference/types/Clue|A & B < C "quoted"]]',labels:['A & B < C "quoted"']},
  {name:'null',text:null,labels:[]},
];
const o = await connect('armarium25-starter');
const source = 'reference/views/HTML formula probe.md';
let created = false;
const evidence = {formula,method:'Obsidian in-memory Base query and real table-cell renderer; hidden DOM; native navigation intercepted; no window focus or tab changes',samples:[]};
try {
  await o.js(`(async()=>{if(app.vault.getAbstractFileByPath(${JSON.stringify(source)}))throw Error('Probe file already exists');await app.vault.create(${JSON.stringify(source)},${JSON.stringify('---\ntext: initial\n---\n')});return true;})()`);
  created = true;
  for (const sample of samples) {
    const result = await o.js(`(async()=>{
      const source=${JSON.stringify(source)}, input=${JSON.stringify(sample.text)};
      const file=app.vault.getAbstractFileByPath(source);
      await app.fileManager.processFrontMatter(file,fm=>fm.text=input);
      for(let i=0;i<50&&app.metadataCache.getFileCache(file)?.frontmatter?.text!==input;i++)await new Promise(r=>setTimeout(r,100));
      if(app.metadataCache.getFileCache(file)?.frontmatter?.text!==input)throw Error('Metadata update timed out');
      const c=app.workspace.activeLeaf.view.previewMode._children.find(x=>x.controller&&x.controller.view.type==='table').controller;
      const q=c.query.constructor.parse({formulas:{probe:${JSON.stringify(formula)},native:'link("reference/types/Clue", "native control")',raw:'html("[[reference/types/Clue|raw Markdown]]")'},views:[{type:'table',name:'probe',order:['formula.probe']}]});
      const ctx=new c.ctx.constructor(app,null,q.formulas,file);
      const entry=new c.ctx.local.constructor(ctx,file);
      const host=document.createElement('div');host.style.display='none';c.view.containerEl.appendChild(host);
      const original=app.workspace.openLinkText;let calls=[];
      app.workspace.openLinkText=function(...args){calls.push(args);return Promise.resolve()};
      // Suppress browser default actions too, including sanitized target=_blank.
      const stop=e=>e.preventDefault();window.addEventListener('click',stop);
      try {
        const records={};
        for(const name of ['probe','native','raw']){
          const cell=host.createDiv('bases-td');c.view.createRenderer('formula.'+name,cell).render(entry);
          calls=[];
          for(const a of cell.querySelectorAll('[data-href]'))a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,button:0}));
          records[name]={html:cell.innerHTML,text:cell.textContent,links:[...cell.querySelectorAll('[data-href]')].map(a=>({label:a.textContent,target:a.dataset.href,resolved:app.metadataCache.getFirstLinkpathDest(a.dataset.href.split('#')[0],source)?.path})),navigationCalls:[...calls],scriptCount:cell.querySelectorAll('script,[onclick],[onerror]').length};
        }
        return {version:document.title.split('Obsidian ').pop(),community:[...app.plugins.enabledPlugins],sourceValue:app.metadataCache.getFileCache(file).frontmatter.text,...records};
      }finally{window.removeEventListener('click',stop);app.workspace.openLinkText=original;host.remove();}
    })()`);
    assert.equal(result.sourceValue,sample.text);
    assert.deepEqual(result.probe.links.map(a=>a.label),sample.labels);
    assert.equal(result.probe.scriptCount,0);
    assert.equal(result.probe.navigationCalls.length,0,'Reevaluate the limitation if a newer app adds HTML link navigation');
    assert.equal(result.native.navigationCalls.length,1,'Positive native-link control must navigate');
    assert(result.raw.text.includes('[[reference/types/Clue|raw Markdown]]'));
    evidence.samples.push({name:sample.name,input:sample.text,...result});
  }
  evidence.outcome='HTML formula parses, renders prose/aliases and reflects successive canonical source edits on reevaluation. HTML links do not invoke internal navigation in Bases 1.13.7; native link() positive control does. Not a working replacement; no production views changed.';
} finally {
  if(created)await o.js(`(async()=>{await app.vault.delete(app.vault.getAbstractFileByPath(${JSON.stringify(source)}));return true;})()`);
  o.close();
}
const output=process.argv[2] || '/private/tmp/armarium25-html.json';
await fs.writeFile(output,JSON.stringify(evidence,null,2)+'\n');
console.log(evidence.outcome+'\nEvidence: '+output);
