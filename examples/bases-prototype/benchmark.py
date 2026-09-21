"""Measure actual Reading-view readiness and scroll through 30 nested views."""
import argparse
import json
from pathlib import Path
from observe import Observer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    observer = Observer(args.vault)
    result = observer.js(r"""(async()=>{
      if(!app.vault.getAbstractFileByPath('world/npcs/Corpus/N-02999.md')) throw Error('Build with --corpus 3000');
      require('@electron/remote').getCurrentWindow().show();
      require('@electron/remote').getCurrentWindow().focus();
      const pause=ms=>new Promise(r=>setTimeout(r,ms));
      const open=async path=>{
        await app.workspace.activeLeaf.setViewState({type:'markdown',state:{file:path,mode:'preview'}});
      };
      const results={files:app.vault.getMarkdownFiles().length,trials:[],repeated:[],heapBefore:performance.memory?.usedJSHeapSize};
      for(let round=0;round<5;round++){
        for(const [path,expected] of [['world/npcs/Mira.md',1],['world/npcs/Corpus/N-00001.md',0]]){
          await open('Start.md'); await pause(50);
          const start=performance.now(); await open(path);
          let ready=false;
          for(let i=0;i<250;i++){
            const el=app.workspace.activeLeaf.view.containerEl.querySelector('.internal-embed[src="bases/entity-clues.base"]');
            if(el){el.scrollIntoView({block:'start'});if(el.innerText.includes(expected+' result') && (expected===0 || el.querySelector('.bases-tbody .bases-tr'))){ready=true;break;}}
            await pause(20);
          }
          results.trials.push({round,path,expected,ready,ms:performance.now()-start});
        }
      }
      const start=performance.now();await open('Repeated.md');await pause(100);
      const preview=app.workspace.activeLeaf.view.containerEl.querySelector('.markdown-preview-view');
      preview.scrollTop=0;
      for(let i=0;i<30;i++){
        const src='world/npcs/Corpus/N-'+String(i).padStart(5,'0')+'#Active Clues';
        const selector='.internal-embed[src='+JSON.stringify(src)+']';
        let el;
        for(let n=0;n<100;n++){
          el=preview.querySelector(selector);
          if(el && el.querySelector('.bases-view'))break;
          preview.scrollTop+=250;await pause(30);
        }
        if(!el)throw Error('Missing repeated embed '+src);
        el.scrollIntoView({block:'center'});await pause(100);
        results.repeated.push({src,expected:i%10===0?1:0,text:el.innerText,height:el.getBoundingClientRect().height});
      }
      results.repeatedScrollMs=performance.now()-start;
      results.heapAfter=performance.memory?.usedJSHeapSize;
      return JSON.stringify(results);
    })()""")
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
