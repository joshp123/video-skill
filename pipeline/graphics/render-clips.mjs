// Written by AI on 2026-10-17 by GPT-6 Codex.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): render data from prepare(), kept beside the clips as render-data.json;
// edit folder and --out required; stills at a timeline frame into the edit folder's build/stills; one reused bundle folder.
import {writeFile,mkdir,access,unlink} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {openBrowser,getCompositions,renderMedia,renderStill} from '@remotion/renderer';
import {prepare} from './prepare.mjs';
const project=path.dirname(fileURLToPath(import.meta.url));
const option=name=>process.argv.find(argument=>argument.startsWith(`--${name}=`))?.slice(name.length+3);
const editArgument=process.argv.slice(2).find(argument=>!argument.startsWith('--'));
const stills=process.argv.includes('--stills'),stillFrame=option('frame'),only=option('only');
if(!editArgument||!option('out')||stills!==(stillFrame!==undefined))throw new Error('Usage: node render-clips.mjs EDIT_FOLDER --out=FOLDER_IN_EDIT_FOLDER [--only=GRAPHIC_ID] [--stills --frame=TIMELINE_FRAME]');
const editFolder=path.resolve(editArgument);
const output=path.join(editFolder,option('out'));
const stillsFolder=path.join(editFolder,'build/stills');
const data=await prepare(editFolder,project);
const graphics=data.graphics.filter(graphic=>(!only||graphic.id===only)&&(!stills||graphic.startFrame<=Number(stillFrame)&&Number(stillFrame)<graphic.endFrame));
if(!graphics.length)throw new Error(`No graphic to render${only?` with the id ${only}`:''}${stills?` on screen at frame ${stillFrame}`:''}`);
const outputFiles=stills?graphics.map(graphic=>path.join(stillsFolder,`${graphic.id}-${stillFrame}.png`)):[...graphics.map(graphic=>path.join(output,`${graphic.id}.mov`)),...(only?[]:[path.join(output,'manifest.json'),path.join(output,'render-data.json')])];
for(const file of outputFiles){
 try{await access(file);}catch(error){if(error.code==='ENOENT')continue;throw error;}
 throw new Error(`Output already exists: ${file}`);
}
await mkdir(stills?stillsFolder:output,{recursive:true});
if(!stills&&!only)await writeFile(path.join(output,'render-data.json'),JSON.stringify(data,null,2)+'\n',{flag:'wx'});
// One bundle folder, reused; the bundler links public into it afresh on every run.
const bundleFolder=path.resolve(project,'../../.cache/remotion-bundle');
await unlink(path.join(bundleFolder,'public')).catch(error=>{if(error.code!=='ENOENT')throw error;});
const serveUrl=await bundle({entryPoint:path.join(project,'src/clips.tsx'),outDir:bundleFolder,publicDir:path.join(project,'public'),symlinkPublicDir:true});
const browserExecutable=path.join(project,'chrome-render.sh'),chromeMode='chrome-for-testing';
const browser=await openBrowser('chrome',{browserExecutable,chromeMode});
try{
 for(const graphic of graphics){
  const shared={serveUrl,puppeteerInstance:browser,browserExecutable,chromeMode,logLevel:'error',inputProps:{data,graphicId:graphic.id}};
  const composition=(await getCompositions(shared)).find(composition=>composition.id==='graphic-clip');
  if(stills){
   await renderStill({...shared,composition,frame:Number(stillFrame)-graphic.startFrame,imageFormat:'png',output:path.join(stillsFolder,`${graphic.id}-${stillFrame}.png`)});
   console.log(`${graphic.id} still`);
   continue;
  }
  let previous=-1;
  await renderMedia({...shared,composition,outputLocation:path.join(output,`${graphic.id}.mov`),codec:'prores',proResProfile:'4444',pixelFormat:'yuva444p10le',imageFormat:'png',colorSpace:'bt709',muted:true,concurrency:1,onProgress:({progress})=>{const step=Math.floor(progress*4);if(step!==previous){previous=step;console.log(`${graphic.id} ${step*25}%`);}}});
 }
 if(!stills&&!only)await writeFile(path.join(output,'manifest.json'),JSON.stringify(graphics.map(graphic=>({id:graphic.id,file:`${graphic.id}.mov`,timeline_in_frame:graphic.startFrame,frames:graphic.endFrame-graphic.startFrame})),null,2)+'\n',{flag:'wx'});
}finally{await browser.close({silent:true});}
