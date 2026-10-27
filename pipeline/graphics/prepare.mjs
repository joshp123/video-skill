// Written by AI on 2026-10-16 by GPT-6 Codex.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): every kind a component draws is built from its cues, each item starting
// on the forced-alignment frame of its cue's word and ending on that of its until word; each kind's cue verbs matched exactly and
// any other verb an error; prompt, start screen and words from the edit data and words.md; the subtitle phrasers, the picture
// staging, the stale cut list exception and the fixed font copy removed.
// Edited 2026-10-21 by Claude Fable 5.1: cue words are matched the way the cut builder matches them (lower case, letters, digits, apostrophes).
// Edited 2026-10-22 by Claude Opus 5.5 (native graphics): the terminal kinds only; photo grids, photo panels and the closing page
// (and a title on any graphic) are built in Resolve by pipeline/resolve/build_graphics.py; the photo staging and slot words went with them.
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {compileTerminalContent,findTerminalTarget} from './terminal-content.mjs';
import {fitClaudeWelcomeRows} from './claude-screen.mjs';

const readJson=async file=>JSON.parse(await readFile(file,'utf8'));
// The parts of the edit data a cut depends on: the same list as cut_inputs() in pipeline/cut/build_cutlist.py (change both
// together). A camera's grade or a mixer field is not among them, so changing one does not stale the cut list.
const pick=(object,keys)=>Object.fromEntries(keys.filter(key=>key in object).map(key=>[key,object[key]]));
export function cutInputs(edit){
 const media=edit.media;
 const inputs=pick(edit,['format','spelling','layouts','graphics','lead_in_s']);
 inputs.lines=edit.lines.map(line=>pick(line,['id','words','keep','retime','cut_points','max_pause_s','pause_after_s','shots']));
 inputs.media={transcript:media.transcript,
  lav:pick(media.lav,['file','offset_s','silence_dbfs','pause_dbfs','room_tone_s']),
  cameras:Object.fromEntries(Object.entries(media.cameras).map(([name,camera])=>[name,pick(camera,['file','offset_s','camera'])])),
  face_touch:media.face_touch||{}};
 return inputs;
}
const canonical=value=>Array.isArray(value)?value.map(canonical):(value&&typeof value==='object')?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
export function cutMatchesEdit(cut,edit){return JSON.stringify(canonical(cut.cut_inputs||null))===JSON.stringify(canonical(cutInputs(edit)));}
function alignedDisplayWords(cut,fps){
 return cut.words.filter(word=>word.word.trim()).flatMap(word=>{
  const timedToken=token=>{
   const startFrame=token.aligned_start_frame;
   const endFrame=token.aligned_end_frame??(token.aligned_end_s===undefined?undefined:Math.ceil(token.aligned_end_s*fps));
   if(startFrame===undefined||endFrame===undefined)throw new Error(`Forced-aligned timing absent: ${token.word??token.text}`);
   return {...word,...token,word:token.word??token.text,t:token.aligned_start_s??startFrame/fps,end:token.aligned_end_s??endFrame/fps,start_frame:startFrame,end_frame:endFrame};
  };
  if(word.aligned_tokens)return word.aligned_tokens.map(timedToken);
  if(word.word.trim().split(/\s+/).length>1)throw new Error(`Individual forced-aligned display tokens absent: ${word.word}`);
  return [timedToken(word)];
 });
}
// The forced-alignment frame of an anchor: its first word's start, or with edge 'end' its last word's end, moved by offset_s.
function alignedAnchorFrame(cut,anchor,fps){
 const tokens=[];
 for(const word of cut.words.filter(word=>word.line===anchor.line)){
  const source=(word.source_word??word.word).split(/\s+/);
  source.forEach((text,index)=>tokens.push({text,start:word.aligned_tokens?.[index]?.aligned_start_frame??word.aligned_start_frame,
   end:word.aligned_tokens?.[index]?.aligned_end_frame??word.aligned_end_frame}));
 }
 // The same match as the cut builder (build_cutlist.py normalize): lower case, letters, digits and apostrophes only.
 const plain=text=>text.toLowerCase().replace(/\u2019/g,"'").replace(/[^a-z0-9']/g,'');
 const target=(anchor.word??anchor.at).split(/\s+/).map(plain);let matches=0;
 for(let index=0;index<=tokens.length-target.length;index++){
  if(!target.every((text,offset)=>plain(tokens[index+offset].text)===text))continue;
  if(matches++!==(anchor.n??0))continue;
  const frame=anchor.edge==='end'?tokens[index+target.length-1].end:tokens[index].start;
  if(frame===undefined)throw new Error(`Aligned cue time absent: ${anchor.line}: ${target.join(' ')}`);
  return frame+Math.round((anchor.offset_s??0)*fps);
 }
 throw new Error(`Aligned cue word absent: ${anchor.line}: ${target.join(' ')}`);
}
// The cue verbs each kind draws; a cue with any other verb stops the build.
const cueVerbs={'terminal':new Set(['type','show','highlight','scroll']),'agent box':new Set(),'keyline':new Set(['show','highlight'])};
// Drawn in Resolve by pipeline/resolve/build_graphics.py, not here.
const nativeKinds=new Set(['photo-grid','photo-panel','closing']);
export async function prepare(editFolder,project){
 const rawEdit=await readFile(path.join(editFolder,'edit/edit.json'));
 const edit=JSON.parse(rawEdit);
 const cut=await readJson(path.join(editFolder,'build/cutlist.json'));
 if(!cutMatchesEdit(cut,edit))throw new Error('The cut list was built from other cut inputs than edit.json holds now. Rebuild the cut list and align it first.');
 for(const graphic of cut.graphics){
  if(!graphic.in_resolved||!graphic.out_resolved)throw new Error(`Unresolved graphic anchor: ${graphic.id}`);
 }
 const {default:look}=await import(pathToFileURL(path.resolve(project,'../../looks',edit.look,'index.mjs')).href);
 const fps=edit.format.fps;
 const graphics=[];
 for(const source of cut.graphics.filter(graphic=>!nativeKinds.has(graphic.kind))){
  const kindName=source.kind==='terminal'&&!source.content.capture?'agent box':source.kind;
  const strayCue=cueVerbs[kindName]&&source.cues.find(cue=>!cueVerbs[kindName].has(cue.do));
  if(strayCue)throw new Error(`Graphic ${source.id} (${kindName}) has a cue verb no ${kindName} draws: ${strayCue.do}`);
  const graphic={id:source.id,kind:source.kind,layout:source.layout,startFrame:source.in_resolved.frame,endFrame:source.out_resolved.frame,content:{...source.content},cues:[]};
  // A timed item starts on the forced-alignment frame of its cue's word and ends on that of its until word; first_frame draws
  // show cues from the graphic's first frame; highlights and motion keep their aligned timing.
  const itemStart=cue=>source.first_frame&&cue.do==='show'?graphic.startFrame:alignedAnchorFrame(cut,cue.at,fps);
  const itemEnd=cue=>cue.until?alignedAnchorFrame(cut,cue.until,fps):undefined;
  if(kindName==='terminal'){
   const capture=await readFile(path.join(editFolder,source.content.capture),'utf8');
   graphic.content={...source.content,...compileTerminalContent(capture,source.content.columns)};
   graphic.cues=source.cues.map(cue=>({frame:itemStart(cue),...(cue.until?{endFrame:itemEnd(cue)}:{}),action:cue.do,target:cue.target,
    ...((cue.do==='show'||cue.do==='highlight'||cue.do==='scroll')&&cue.target!==undefined?{range:findTerminalTarget(graphic.content.rows,cue.target,cue.after)}:{})}));
  }else if(kindName==='agent box'){
   // The agent box types his kept words of the in line from the in word on, each on its aligned frame.
   const requestStart=alignedAnchorFrame(cut,{line:source.in.line,word:source.in.at??source.in.word,n:source.in.n},fps);
   const words=alignedDisplayWords(cut,fps).filter(word=>word.line===source.in.line&&word.start_frame>=requestStart&&word.start_frame<graphic.endFrame);
   graphic.content={columns:source.content.columns,prompt:source.content.prompt,rows:[],words:words.map(word=>word.word),
    welcomeRows:fitClaudeWelcomeRows(await readFile(path.join(editFolder,source.content.start_screen),'utf8'),source.content.columns)};
   graphic.cues=words.map((word,index)=>({frame:word.start_frame,endFrame:word.end_frame,action:'type-word',index}));
  }else if(source.kind==='keyline'){
   // A show cue names a card by its first row; a highlight lights its target in the card on screen at that frame.
   const cards=source.content.cards.map(rows=>({rows}));
   for(const cue of source.cues.filter(cue=>cue.do==='show')){
    const card=cards.find(card=>card.rows[0]===cue.target);
    if(!card)throw new Error(`${source.id}: no card starts with the show cue's target: ${cue.target}`);
    card.fromFrame=itemStart(cue);
   }
   const highlights=[];
   for(const cue of source.cues.filter(cue=>cue.do==='highlight')){
    const frame=itemStart(cue);
    const cardIndex=cards.findLastIndex(card=>card.fromFrame<=frame);
    if(cardIndex<0)throw new Error(`${source.id}: no card is on screen for the highlight on ${cue.target}`);
    const ranges=findTerminalTarget(cards[cardIndex].rows,cue.target,cue.after).map(range=>({card:cardIndex,...range}));
    const sameFrame=highlights.find(highlight=>highlight.frame===frame);
    if(sameFrame)sameFrame.ranges.push(...ranges);else highlights.push({frame,ranges});
   }
   // Without a command, header is optional literal text in the command row; keyColumns also sizes that row.
   graphic.content={...source.content,commandColumns:source.content.commandColumns??source.content.keyColumns,cards,highlights};
  }else throw new Error(`No component draws graphics of kind ${source.kind}: ${source.id}`);
  graphics.push(graphic);
 }
 return {format:edit.format,layouts:cut.layouts,graphics,look};
}
