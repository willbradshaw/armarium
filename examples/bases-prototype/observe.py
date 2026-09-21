"""Capture real Obsidian Reading-view DOM; requires enabled Obsidian CLI.

Only use disposable vaults built by prototype.py. This is an evaluation harness,
not a plugin, and uses private UI APIs that may change between Obsidian releases.
"""
import argparse
import json
from pathlib import Path
import subprocess

CLI = "/Applications/Obsidian.app/Contents/MacOS/obsidian-cli"


class Observer:
    def __init__(self, vault, cli=CLI):
        self.vault = vault
        self.cli = cli

    def command(self, *args):
        # This CLI version requires the vault selector before the command.
        result = subprocess.run([self.cli, "vault=" + self.vault, *args], text=True, capture_output=True, timeout=60)
        if result.returncode or result.stdout.startswith("Error:") or "not enabled" in result.stdout:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout.strip()

    def js(self, code):
        guarded = "(()=>{if(app.vault.getName()!==" + json.dumps(self.vault) + ")throw Error('CLI targeted the wrong vault');return (" + code + ");})()"
        output = self.command("eval", "code=" + guarded)
        if not output.startswith("=> "):
            raise RuntimeError(output)
        return json.loads(output[3:])

    def open(self, path):
        return self.js("""(async()=>{
          const start=performance.now();
          const w=require('@electron/remote').getCurrentWindow(); w.show(); w.focus();
          await app.workspace.activeLeaf.setViewState({type:'markdown',state:{file:PATH,mode:'preview'}});
          await new Promise(r=>setTimeout(r,300));
          return JSON.stringify({path:app.workspace.getActiveFile().path,openWith300msWait:performance.now()-start});
        })()""".replace("PATH", json.dumps(path)))

    def capture(self, embed):
        return self.js(r"""(async()=>{
          const selector='.internal-embed[src='+JSON.stringify(EMBED)+']';
          let el=document.querySelector(selector);
          // Markdown preview virtualizes sections: move down until the requested embed mounts.
          const preview=app.workspace.activeLeaf.view.containerEl.querySelector('.markdown-preview-view');
          for(let i=0;!el && i<40;i++){
            preview.scrollTop+=500; await new Promise(r=>setTimeout(r,50)); el=document.querySelector(selector);
          }
          if(!el) throw new Error('Embed not mounted: '+EMBED);
          el.scrollIntoView({block:'start'});
          await new Promise(r=>setTimeout(r,350));
          const rows=new Map(),cells=new Map();
          const table=el.querySelector('.bases-table-container');
          const top=table ? preview.scrollTop+table.getBoundingClientRect().top-preview.getBoundingClientRect().top : preview.scrollTop;
          const height=table ? Math.max(table.scrollHeight,table.getBoundingClientRect().height) : 0;
          for(let offset=0;offset<=height;offset+=Math.max(100,preview.clientHeight/2)){
            if(table)table.scrollTop=offset;
            preview.scrollTop=top+offset;
            await new Promise(r=>setTimeout(r,250));
            for(const row of el.querySelectorAll('.bases-tbody .bases-tr')){
              const data=Array.from(row.querySelectorAll('.bases-td')).map(c=>({property:c.dataset.property,text:c.innerText,links:Array.from(c.querySelectorAll('[data-href]')).map(a=>a.dataset.href)}));
              rows.set(JSON.stringify(data[0]),data);
            }
            for(const c of el.querySelectorAll('[data-property="note.text"] .metadata-input-longtext,[data-property="note.summary"] .metadata-input-longtext'))
              cells.set(c.textContent,{clientHeight:c.clientHeight,scrollHeight:c.scrollHeight,whiteSpace:getComputedStyle(c).whiteSpace,overflow:getComputedStyle(c).overflow});
          }
          return JSON.stringify({embed:EMBED,text:el.innerText+'\n'+Array.from(rows.values()).map(r=>r.map(c=>c.text).join('\n')).join('\n'),
            rows:Array.from(rows.values()),cells:Array.from(cells.values()),table:table?{height:table.clientHeight,scrollHeight:table.scrollHeight}:null,
            errors:Array.from(el.querySelectorAll('.bases-error')).map(e=>e.textContent)});
        })()""".replace("EMBED", json.dumps(embed)))

    def set_property(self, path, name, value):
        return self.js("""(async()=>{
          await app.fileManager.processFrontMatter(app.vault.getAbstractFileByPath(PATH),fm=>fm[NAME]=VALUE);
          await new Promise(r=>setTimeout(r,700));
          return JSON.stringify({edited:PATH,property:NAME,value:VALUE});
        })()""".replace("PATH", json.dumps(path)).replace("NAME", json.dumps(name)).replace("VALUE", json.dumps(value)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", help="Unique Obsidian vault name")
    parser.add_argument("output", type=Path)
    parser.add_argument("--cli", default=CLI)
    args = parser.parse_args()
    observer = Observer(args.vault, args.cli)
    # Fail closed before any navigation if the chosen vault is not this fixture.
    if not observer.js("JSON.stringify(app.vault.getAbstractFileByPath('bases/prepared-clues.base') !== null)"):
        parser.error("Not a Bases prototype vault")
    evidence = {"version": observer.command("version"), "plugins": observer.command("plugins:enabled", "versions"), "cases": []}
    for path, embeds in [
        ("campaign_1/index/Clues.md", ["bases/clue-index.base#Active", "bases/clue-index.base#Closed"]),
        ("campaign_2/index/Clues.md", ["bases/clue-index.base#Active", "bases/clue-index.base#Closed"]),
        ("world/npcs/Mira.md", ["bases/entity-clues.base"]),
        ("world/npcs/Visitors/Mira.md", ["bases/entity-clues.base"]),
        ("world/locations/Empty.md", ["bases/entity-clues.base"]),
        ("campaign_1/clues/C-1-0001.md", ["bases/clue-sessions.base"]),
        ("campaign_2/clues/C-2-0001.md", ["bases/clue-sessions.base"]),
        ("campaign_1/sessions/S-1-001.md", ["bases/prepared-clues.base", "bases/prepared-locations.base", "bases/prepared-npcs.base"]),
        ("campaign_1/sessions/S-1-003.md", ["bases/prepared-clues.base", "bases/prepared-locations.base", "bases/prepared-npcs.base"]),
    ]:
        opened = observer.open(path)
        evidence["cases"].append({**opened, "views": [observer.capture(e) for e in embeds]})
        args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
