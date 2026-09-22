/** Disposable-vault CDP harness; Node 22+, Obsidian --remote-debugging-port=9225.
 * Uses private UI APIs only for evaluation, never installed in a vault.
 */
import fs from 'node:fs/promises';
const port = process.env.OBSIDIAN_DEBUG_PORT || '9225';
export async function connect(vault) {
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = pages.find(p => p.type === 'page' && p.title.includes(vault));
  if (!page) throw Error(`No open review vault: ${vault}`);
  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let id = 0;
  const pending = new Map();
  socket.onmessage = event => {
    const data = JSON.parse(event.data);
    if (pending.has(data.id)) {pending.get(data.id)(data);pending.delete(data.id);}
  };
  async function send(method, params) {
    const current = ++id;
    const answer = new Promise(resolve => pending.set(current, resolve));
    socket.send(JSON.stringify({id: current, method, params}));
    const data = await answer;
    if (data.error) throw Error(JSON.stringify(data.error));
    return data.result;
  }
  async function js(code) {
    const expression = `(async()=>{if(app.vault.getName()!==${JSON.stringify(vault)} || !app.vault.adapter.basePath.startsWith('/private/tmp/armarium25-review/'))throw Error('Not a disposable review vault');return await (${code});})()`;
    const data = await send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (data.exceptionDetails) throw Error(JSON.stringify(data.exceptionDetails));
    return data.result.value;
  }
  async function open(path) {
    // Foreground rendering must be explicitly requested; default runs never steal focus.
    const focus = process.env.OBSIDIAN_ALLOW_FOCUS === '1'
      ? "const w=require('@electron/remote').getCurrentWindow();w.show();w.focus();" : '';
    return js(`(async()=>{${focus}await app.workspace.getLeaf().openFile(app.vault.getAbstractFileByPath(${JSON.stringify(path)}),{state:{mode:'preview'}});await new Promise(r=>setTimeout(r,650));return document.title;})()`);
  }
  async function capture() {
    return js(`(async()=>{
      const preview=app.workspace.activeLeaf.view.containerEl.querySelector('.markdown-preview-view');
      const views=new Map(),tables=new Map();
      const links=new Set();
      let text='';
      for(let offset=0;offset<=preview.scrollHeight;offset+=Math.max(200,preview.clientHeight/2)) {
        preview.scrollTop=offset;await new Promise(r=>setTimeout(r,80));
        text=preview.innerText;
        for(const el of preview.querySelectorAll('.bases-view')) {
          const src=el.closest('.internal-embed')?.getAttribute('src') || '';
          const rows=[...el.querySelectorAll('.bases-list-item,.bases-tbody .bases-tr')].map(r=>({text:r.innerText,values:[...r.querySelectorAll('input')].map(i=>i.value),links:[...r.querySelectorAll('[data-href]')].map(a=>a.dataset.href)}));
          const key=src+'#'+el.dataset.viewName;
          const previous=views.get(key) || {src,name:el.dataset.viewName,type:el.dataset.viewType,rows:[],errors:[]};
          for(const row of rows)if(!previous.rows.some(r=>r.text===row.text))previous.rows.push(row);
          previous.errors.push(...[...el.querySelectorAll('.bases-error')].map(e=>e.textContent));
          views.set(key,previous);
        }
        for(const el of preview.querySelectorAll('table'))tables.set(el.innerText,{text:el.innerText,links:[...el.querySelectorAll('[data-href]')].map(a=>a.dataset.href)});
        for(const a of preview.querySelectorAll('[data-href]'))links.add(a.dataset.href);
      }
      return {path:app.workspace.getActiveFile().path,title:document.title,text,views:[...views.values()],tables:[...tables.values()],links:[...links],errors:[...preview.querySelectorAll('.bases-error')].map(e=>e.textContent)};
    })()`);
  }
  async function set(path, property, value) {
    return js(`(async()=>{await app.fileManager.processFrontMatter(app.vault.getAbstractFileByPath(${JSON.stringify(path)}),fm=>fm[${JSON.stringify(property)}]=${JSON.stringify(value)});await new Promise(r=>setTimeout(r,1800));return true;})()`);
  }
  async function screenshot(path) {
    const data=await send('Page.captureScreenshot',{format:'png'});
    await fs.writeFile(path,Buffer.from(data.data,'base64'));
  }
  return {js,open,capture,set,screenshot,close:()=>socket.close()};
}

if (process.argv[1] && import.meta.url === new URL(process.argv[1], 'file:').href) {
  const observer = await connect(process.argv[2]);
  try {
    await observer.open(process.argv[3]);
    console.log(JSON.stringify(await observer.capture(),null,2));
  } finally {observer.close();}
}
