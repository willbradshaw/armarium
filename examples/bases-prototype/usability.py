"""Capture UI editing, navigation, and explicit snapshot refresh evidence."""
import argparse
import json
from pathlib import Path

from observe import Observer
from prototype import refresh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    o = Observer(args.vault)
    root = Path(o.js("JSON.stringify(app.vault.adapter.basePath)"))
    if not root.name.startswith("armarium-bases-"):
        parser.error("Use a disposable armarium-bases-* fixture")
    session = "campaign_1/sessions/S-1-001.md"
    source = "campaign_1/clues/C-1-0001.md"
    originals = {p: (root / p).read_text() for p in [session, source]}
    result = {}
    try:
        o.open(session)
        o.js("(async()=>{document.querySelector('.markdown-preview-view').scrollTop=0;await new Promise(r=>setTimeout(r,800));document.querySelector('[data-property-key=prepared_npcs]').scrollIntoView({block:'center'});await new Promise(r=>setTimeout(r,300));return JSON.stringify(true);})()")
        o.command("dev:screenshot", "path=" + str(args.output.parent.resolve() / "selections.png"))
        result["property_widget_removal"] = o.js("""(async()=>{
          const el=document.querySelector('[data-property-key="prepared_npcs"] .multi-select-pill-remove-button');
          if(!el)throw Error('Selection widget not visible');
          el.click();await new Promise(r=>setTimeout(r,1000));
          return JSON.stringify(app.metadataCache.getFileCache(app.workspace.getActiveFile()).frontmatter.prepared_npcs);
        })()""")
        result["after_widget_removal"] = o.capture("bases/prepared-npcs.base")
        o.open("world/npcs/Mira.md")
        o.capture("bases/entity-clues.base")
        result["base_link_navigation"] = o.js("""(async()=>{
          document.querySelector('.bases-tbody .internal-link').click();await new Promise(r=>setTimeout(r,700));
          return JSON.stringify(app.workspace.getActiveFile().path);
        })()""")
        o.open(session)
        result["long_text"] = o.capture("bases/prepared-clues.base")
        o.js("(async()=>{document.querySelector('.internal-embed[src=\"bases/prepared-clues.base\"]').scrollIntoView({block:'start'});await new Promise(r=>setTimeout(r,350));return JSON.stringify(true);})()")
        o.command("dev:screenshot", "path=" + str(args.output.parent.resolve() / "bases-prep.png"))
        result["fallback"] = o.js("""(async()=>{
          const preview=document.querySelector('.markdown-preview-view');let table;
          for(let i=0;i<30;i++){
            table=preview.querySelector('table');if(table)break;
            preview.scrollTop+=200;await new Promise(r=>setTimeout(r,100));
          }
          if(!table)throw Error('Fallback table not visible');
          table.scrollIntoView({block:'start'});await new Promise(r=>setTimeout(r,400));
          return JSON.stringify({text:table.innerText,links:Array.from(table.querySelectorAll('a.internal-link')).map(a=>a.dataset.href),width:table.clientWidth,scrollWidth:table.scrollWidth});
        })()""")
        o.command("dev:screenshot", "path=" + str(args.output.parent.resolve() / "markdown-prep.png"))
        result["fallback_link_navigation"] = o.js("""(async()=>{
          document.querySelector('table a.internal-link').click();await new Promise(r=>setTimeout(r,700));
          return JSON.stringify(app.workspace.getActiveFile().path);
        })()""")
        o.open(session)
        o.capture("bases/prepared-clues.base")
        o.set_property(source, "text", "EXPLICIT-SNAPSHOT-REFRESH [[world/locations/Quay|the quay]]")
        result["snapshot_unchanged_before_refresh"] = "EXPLICIT-SNAPSHOT-REFRESH" not in (root / session).read_text()
        refresh(root, session.removesuffix(".md"))
        result["snapshot_updated_on_disk"] = "EXPLICIT-SNAPSHOT-REFRESH" in (root / session).read_text()
        result["snapshot_render_after_refresh"] = o.js("""(async()=>{
          await new Promise(r=>setTimeout(r,1000));
          const preview=document.querySelector('.markdown-preview-view');
          for(let i=0;i<30;i++){
            const table=Array.from(preview.querySelectorAll('table')).find(t=>t.textContent.includes('EXPLICIT-SNAPSHOT-REFRESH'));
            if(table)return JSON.stringify({updated:true,links:Array.from(table.querySelectorAll('a.internal-link')).map(a=>a.dataset.href)});
            preview.scrollTop+=200;await new Promise(r=>setTimeout(r,100));
          }
          return JSON.stringify({updated:false});
        })()""")
    finally:
        for p, content in originals.items():
            o.js("(async()=>{await app.vault.modify(app.vault.getAbstractFileByPath(" + json.dumps(p) + ")," + json.dumps(content) + ");return JSON.stringify(true);})()")
        args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
