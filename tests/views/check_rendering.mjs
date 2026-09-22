import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {connect} from './observe.mjs';
const output=process.argv[2] || '/private/tmp/armarium25-evidence';
await fs.mkdir(output,{recursive:true});
const evidence={date:new Date().toISOString(),checks:[],baseline:[],edits:[]};
async function save(){await fs.writeFile(`${output}/rendering.json`,JSON.stringify(evidence,null,2)+'\n');}
function passed(name,detail){evidence.checks.push({name,pass:true,detail});console.log('PASS '+name);}
function rows(data,name){return data.views.filter(v=>!name||v.name===name).flatMap(v=>v.rows);}
function ids(data,name){return rows(data,name).map(r=>r.links[0]?.split('/').pop().replace('.md',''));}
async function expectIds(o,expected,label){
  let data=await o.capture();
  assert.deepEqual(ids(data),expected,label);
  return data;
}
const observers=[];
try {
  const inventory=JSON.parse(await fs.readFile('docs/views/inventory.json','utf8'));
  for (const vault of ['starter','example']) {
    const o=await connect('armarium25-'+vault);observers.push(o);
    const runtime=await o.js(`({version:document.title.split('Obsidian ').pop(),community:[...app.plugins.enabledPlugins],bases:app.internalPlugins.plugins.bases.enabled})`);
    assert.deepEqual(runtime.community,[]);assert.equal(runtime.bases,true);
    evidence[vault]=runtime;passed(vault+' runtime: Bases on, no community plugins',runtime);
    const paths=[...new Set(inventory.filter(i=>i.file.startsWith('vaults/'+vault+'/')).map(i=>i.file.slice(('vaults/'+vault+'/').length)))];
    if(!paths.includes('reference/templates/Session.md'))paths.push('reference/templates/Session.md');
    for(const path of (process.env.SKIP_BASELINE ? [] : paths)){
      await o.open(path);const data=await o.capture();evidence.baseline.push({vault,...data});
      assert.equal(data.errors.filter(Boolean).length,0,path);
      assert(data.views.every(view=>view.type==='table'),path);
      if(path.includes('/sessions/')||path==='reference/templates/Session.md')assert(data.tables.length>=3,path);
      else assert(data.views.length>0,path);
      if(vault==='starter')assert.deepEqual(ids(data),[],path);
      if(vault==='example'){
        if(path.startsWith('content/')||path.startsWith('campaigns/campaign_1/content/')){
          const name=path.split('/').pop();
          const expected=name==='Captain Mara Vey.md'?['C-1-0003']:
            ['Shoal Chart.md','The Red Teeth.md'].includes(name)?['C-1-0003','C-1-0004']:
            name==='Free Pilots Assembly.md'?['C-1-0004']:[];
          assert.deepEqual(ids(data),expected,path);
        }
        if(path.startsWith('campaigns/campaign_1/clues/')){
          const expected=path.endsWith('0003.md')?['S-1-002','S-1-003']:
            path.endsWith('0004.md')?['S-1-003']:['S-1-001'];
          assert.deepEqual(ids(data),expected,path);
        }
        if(path.endsWith('/indexes/Clues.md')){
          assert.deepEqual(ids(data,'Active').filter(x=>!x.includes('-9')),['C-1-0003','C-1-0004']);
          assert.deepEqual(ids(data,'Closed').filter(x=>!x.includes('-9')),['C-1-0001','C-1-0002']);
        }
      }
    }
    if(!process.env.SKIP_BASELINE)passed(vault+' all inventoried containing notes render',paths.length);
    await save();
  }
  const o=observers[1];
  for(const campaign of [1,2]){
    await o.open(`campaigns/campaign_${campaign}/reference/indexes/Clues.md`);
    const data=await o.capture();evidence.edits.push({test:'initial campaign index',...data});
    assert.deepEqual(ids(data,'Active').filter(x=>x.includes('-9')),[`C-${campaign}-9001`,`C-${campaign}-9002`]);
    assert.deepEqual(ids(data,'Closed').filter(x=>x.includes('-9')),[3,4,5,6].map(i=>`C-${campaign}-900${i}`));
    assert(rows(data).every(r=>r.links[0].includes(`/campaign_${campaign}/`)));
    assert(rows(data).filter(r=>r.text.includes('-900')).every(r=>r.text.includes('CLUE_TEXT_END')));
    passed('campaign '+campaign+' scope, all statuses, order, long text');
    await o.open(`campaigns/campaign_${campaign}/clues/C-${campaign}-9001.md`);
    const sessions=await o.capture();evidence.edits.push({test:'session order',...sessions});
    assert.deepEqual(ids(sessions),[902,903,901].map(i=>`S-${campaign}-${i}`));
    passed('campaign '+campaign+' Sessions date/number order, no transcripts or nested Sessions');
  }
  const keeper='content/Review/Signal Keeper.md',clue='campaigns/campaign_1/clues/C-1-9001.md';
  const originalClue=await o.js(`app.vault.read(app.vault.getAbstractFileByPath(${JSON.stringify(clue)}))`);
  const originalKeeper=await o.js(`app.vault.read(app.vault.getAbstractFileByPath(${JSON.stringify(keeper)}))`);
  try {
    await o.open(keeper);assert.deepEqual(ids(await o.capture()),['C-1-9001']);
    await o.set(keeper,'view_campaign','campaign_2');assert.deepEqual(ids(await o.capture()),['C-2-9001']);
    await o.set(keeper,'view_campaign','campaign_1');
    passed('shared Content explicit scope switches live');
    for(const status of ['Pending','Hinted','Revealed','Abandoned','Dormant','Superseded']){
      await o.set(clue,'status',`[[${status}]]`);
      const data=await expectIds(o,['Pending','Hinted'].includes(status)?['C-1-9001']:[],'status '+status);evidence.edits.push({test:'status '+status,...data});
    }
    passed('all six status edits update the table');
    await o.set(clue,'status','[[Pending]]');
    await o.set(clue,'text','LIVE_CLUE_EDIT [[content/Review/Quay|Quay]]');
    assert(rows(await o.capture())[0].text.includes('LIVE_CLUE_EDIT'));
    await o.set(clue,'subjects',['[[content/Review/Visitors/Signal Keeper|Visitor]]']);
    await expectIds(o,[],'subject removal');
    await o.open('content/Review/Visitors/Signal Keeper.md');assert.deepEqual(ids(await o.capture()),['C-1-9001','C-1-9002']);
    passed('canonical aliased subjects distinguish duplicate basenames and update live');
    await o.open('content/Review/Empty.md');assert.deepEqual(ids(await o.capture()),[]);
    passed('Content empty state');
  } finally {
    await o.js(`(async()=>{await app.vault.modify(app.vault.getAbstractFileByPath(${JSON.stringify(clue)}),${JSON.stringify(originalClue)});await app.vault.modify(app.vault.getAbstractFileByPath(${JSON.stringify(keeper)}),${JSON.stringify(originalKeeper)});await new Promise(r=>setTimeout(r,700));return true;})()`);
  }
  await o.open(keeper);await o.capture();
  await o.js(`(()=>{const p=app.workspace.activeLeaf.view.containerEl.querySelector('.markdown-preview-view');const e=p.querySelector('.bases-tbody .bases-tr');e.scrollIntoView({block:'center'});return true;})()`);
  const dimensions=await o.js(`(()=>{const e=[...document.querySelectorAll('.bases-tbody .bases-tr')].find(e=>e.innerText.includes('CLUE_TEXT_END'));return {height:e.clientHeight,scrollHeight:e.scrollHeight,text:e.innerText,links:[...e.querySelectorAll('[data-href]')].map(a=>a.dataset.href)};})()`);
  evidence.longText=dimensions; // Record table clipping honestly; full text remains on the source.
  passed('long clue text is present in the table',dimensions.height);
  // Dispatch a real click on the source ID.
  const destination=await o.js(`(async()=>{const a=[...app.workspace.activeLeaf.view.containerEl.querySelectorAll('.bases-tbody .bases-tr [data-href]')].find(a=>a.dataset.href==='${clue}');a.dispatchEvent(new MouseEvent('click',{bubbles:true}));await new Promise(r=>setTimeout(r,600));return app.workspace.getActiveFile().path;})()`);
  assert.equal(destination,clue);passed('Base source link click navigates to canonical file');
  const session='campaigns/campaign_1/sessions/S-1-901.md';
  await o.open(session);const prep=await o.capture();evidence.preparation=prep;
  assert(prep.tables.some(t=>t.text.includes('LONG_TEXT_END')));
  assert(prep.tables.flatMap(t=>t.links).includes('content/Review/Quay'));
  assert(!prep.tables.flatMap(t=>t.links).includes('content/Review/Events Only'));
  const npc=prep.tables.find(t=>t.text.includes('LONG_TEXT_END'));
  assert(npc.text.indexOf('Visitor')<npc.text.indexOf('Keeper'));
  passed('preparation ordered, full long text, embedded wikilinks, no Events-only selections');
  await o.js(`(()=>{const p=app.workspace.activeLeaf.view.containerEl.querySelector('.markdown-preview-view');p.querySelector('table').scrollIntoView({block:'start'});return true;})()`);
  const originalSession=await o.js(`app.vault.read(app.vault.getAbstractFileByPath(${JSON.stringify(session)}))`);
  try {
    await o.set(keeper,'summary','LIVE_SUMMARY_EDIT [[content/Review/Quay|the quay]]');
    const stale=await o.capture();assert(!stale.tables.some(t=>t.text.includes('LIVE_SUMMARY_EDIT')));
    await o.set(session,'prepared_npcs',['[[content/Review/Signal Keeper|Keeper]]']);
    const root='/private/tmp/armarium25-review/armarium25-example';
    const python=process.env.ARMARIUM_PYTHON || 'python3';
    execFileSync(python,['tools/refresh_preparation.py',root,session]);
    await new Promise(r=>setTimeout(r,1200));
    const fresh=await o.capture();evidence.refreshed=fresh;
    assert(fresh.tables.some(t=>t.text.includes('LIVE_SUMMARY_EDIT')));
    assert(!fresh.tables.some(t=>t.text.includes('A different keeper')));
    const current=await o.js(`app.vault.read(app.vault.getAbstractFileByPath(${JSON.stringify(session)}))`);
    assert.equal(current.split('# Notes\n')[1],originalSession.split('# Notes\n')[1]);
    assert(execFileSync(python,['tools/refresh_preparation.py',root,session],{encoding:'utf8'}).includes('Current'));
    passed('explicit refresh updates summary/selections in open note; repeated run stable; Notes preserved');
  } finally {
    await o.js(`(async()=>{await app.vault.modify(app.vault.getAbstractFileByPath(${JSON.stringify(session)}),${JSON.stringify(originalSession)});await app.vault.modify(app.vault.getAbstractFileByPath(${JSON.stringify(keeper)}),${JSON.stringify(originalKeeper)});return true;})()`);
  }
  await save();console.log('Evidence: '+output);
} catch(error) {evidence.failure=String(error.stack);await save();throw error;}
finally {for(const o of observers)o.close();}
