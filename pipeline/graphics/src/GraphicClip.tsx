// Written by AI on 2026-10-17 by GPT-6 Codex.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): every face from the look's fonts; regions from the layout, never its name;
// the old card, its style override and the subtitle-band viewport removed.
// Edited 2026-10-22 by Claude Opus 5.5 (native graphics): the terminal kinds only; photo grids, photo panels, titles and the
// closing page are Fusion compositions in Resolve (pipeline/resolve/build_graphics.py).
import React from 'react';
import {AbsoluteFill,Sequence,staticFile} from 'remotion';
import {loadFont} from '@remotion/fonts';
import type {FilmData,Graphic,Region} from './types';
import {Terminal} from './Terminal';
import {Keyline} from './Keyline';
import {terminalRegion} from './layout';
import {registerFontLoading} from './glyphBounds';
const loadedFonts=new Set<string>();
export function GraphicClip({data,graphicId}:{data:FilmData;graphicId:string}) {
 for(const font of data.look.fonts??[]){
  const key=`${font.family}:${font.src}:${font.weight}`;
  if(!loadedFonts.has(key)){
   registerFontLoading(font.family,String(font.weight),loadFont({family:font.family,url:staticFile(font.src),weight:String(font.weight)}));
   loadedFonts.add(key);
  }
 }
 const graphic=data.graphics.find(graphic=>graphic.id===graphicId)!;
 return <Sequence from={-graphic.startFrame} layout="none"><GraphicOverlay data={data} graphic={graphic}/></Sequence>;
}
function GraphicOverlay({data,graphic}:{data:FilmData;graphic:Graphic}) {
 const layout=data.layouts[graphic.layout];
 const region:Region=layout.graphic??[0,0,data.format.width,data.format.height];
 const backgroundHeight=layout.picture?layout.picture[1]:data.format.height;
 return <AbsoluteFill>
  {graphic.kind==='terminal'&&<div style={{position:'absolute',left:0,top:0,width:data.format.width,height:backgroundHeight,background:data.look.background}}/>}
  {graphic.kind==='keyline'&&<Keyline content={graphic.content} startFrame={graphic.startFrame} region={region} look={data.look}/>}
  {graphic.kind==='terminal'&&<Terminal content={graphic.content} cues={graphic.cues} region={terminalRegion(region)} panelRegion={region} look={data.look}/>}
 </AbsoluteFill>;
}
