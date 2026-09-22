import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {connect} from './observe.mjs';
const o=await connect('armarium25-example');
const path='campaigns/campaign_1/sessions/S-1-901.md';
const result={checks:[]};
let original;
try {
  await o.open(path);
  original=await o.js(`app.vault.read(app.vault.getAbstractFileByPath(${JSON.stringify(path)}))`);
  await o.js(`(async()=>{const p=app.workspace.activeLeaf.view.containerEl.querySelector('.markdown-preview-view');p.scrollTop=0;await new Promise(r=>setTimeout(r,500));const e=p.querySelector('[data-property-key="prepared_npcs"] .multi-select-pill-remove-button');e.click();await new Promise(r=>setTimeout(r,1000));return true;})()`);
  const removed=await o.js(`app.metadataCache.getFileCache(app.vault.getAbstractFileByPath(${JSON.stringify(path)})).frontmatter.prepared_npcs`);
  assert.deepEqual(removed,['[[content/Review/Signal Keeper|Keeper]]']);
  result.checks.push({name:'Remove Visitor using native Properties pill x',pass:true,value:removed});
  const added=await o.js(`(async()=>{const e=app.workspace.activeLeaf.view.containerEl.querySelector('[data-property-key="prepared_npcs"] .multi-select-input');e.focus();e.textContent='[[content/Review/Visitors/Signal Keeper|Visitor]]';e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:e.textContent}));e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',bubbles:true}));e.blur();await new Promise(r=>setTimeout(r,1000));return app.metadataCache.getFileCache(app.vault.getAbstractFileByPath(${JSON.stringify(path)})).frontmatter.prepared_npcs;})()`);
  assert.deepEqual(added,['[[content/Review/Signal Keeper|Keeper]]','[[content/Review/Visitors/Signal Keeper|Visitor]]']);
  result.checks.push({name:'Add Visitor through native Properties input and Enter; appended after Keeper',pass:true,value:added});
  await o.screenshot('/private/tmp/armarium25-edits/selections.png');
  const text=await o.js(`app.vault.read(app.vault.getAbstractFileByPath(${JSON.stringify(path)}))`);
  assert.equal(text.split('# Notes\n')[1],original.split('# Notes\n')[1]);
  // Selection edits do not silently rewrite the snapshot.
  assert.equal(text.split('# Preparation\n')[1],original.split('# Preparation\n')[1]);
  result.checks.push({name:'UI selection edits preserve snapshot and all Notes',pass:true});
  await o.capture();
  const navigation=await o.js(`(async()=>{const a=[...app.workspace.activeLeaf.view.containerEl.querySelectorAll('table [data-href]')].find(a=>a.dataset.href==='content/Review/Quay');a.click();await new Promise(r=>setTimeout(r,800));return app.workspace.getActiveFile().path;})()`);
  assert.equal(navigation,'content/Review/Quay.md');
  result.checks.push({name:'Click wikilink embedded in canonical summary snapshot',pass:true,destination:navigation});
} catch(error){result.failure=String(error.stack);throw error;}
finally {
  if(original)await o.js(`app.vault.modify(app.vault.getAbstractFileByPath(${JSON.stringify(path)}),${JSON.stringify(original)})`);
  o.close();await fs.writeFile('/private/tmp/armarium25-edits/editing.json',JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
}
