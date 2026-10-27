// Written by AI on 2026-10-17 by GPT-6 Codex.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): the shell and photo panel from the layout's regions, the pill padding
// from the look, the prompt glyphs from the content.
// Edited 2026-10-22 by Claude Opus 5.5 (native graphics): the photos beside the card are a photo-panel graphic of their own,
// drawn in Resolve; the card no longer draws them.
import React,{useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {rowCells} from '../terminal-content.mjs';
import {useRenderedWordBoxes} from './glyphBounds';
import {terminalRegion} from './layout';

type KeyRange={card:number;row:number;column:number;length:number};
type KeyContent={command?:string;prompt?:string;typeCommand?:boolean;header?:string;commandColumns:number;keyColumns:number;cards:{fromFrame:number;rows:string[]}[];highlights:{frame:number;ranges:KeyRange[]}[]};
export function Keyline({content,startFrame,region,look}:{content:KeyContent;startFrame:number;region:[number,number,number,number];look:any}) {
 const frame=useCurrentFrame();
 const source=look.terminal,panel=source.panel,padding=source.highlight.padding;
 const safe=terminalRegion(region);
 const shell=[region[0]+panel.inset,region[1]+panel.inset,region[2]-2*panel.inset,region[3]-2*panel.inset];
 const left=Math.max(safe[0],shell[0]+panel.padding);
 const top=Math.max(safe[1],shell[1]+panel.padding);
 const width=Math.min(safe[0]+safe[2],shell[0]+shell[2]-panel.padding)-left;
 const textWidth=width-2*padding;
 const commandScale=textWidth/(content.commandColumns*source.cellWidth);
 const keyScale=textWidth/(content.keyColumns*source.cellWidth);
 const commandRowHeight=source.rowHeight*commandScale;
 const rowHeight=source.rowHeight*keyScale;
 const cellWidth=source.cellWidth*keyScale;
 const fontSize=source.fontSize*keyScale;
 const cardIndex=content.cards.map((card,index)=>({card,index})).filter(({card})=>card.fromFrame<=frame).at(-1)?.index??-1;
 const card=content.cards[cardIndex];
 const cardSpaceTop=2*commandRowHeight;
 const cardSpaceBottom=shell[1]+shell[3]-(top+padding);
 const cardTop=(cardSpaceTop+cardSpaceBottom-(card?.rows.length??0)*rowHeight)/2;
 const highlight=content.highlights.filter(highlight=>highlight.frame<=frame).at(-1);
 const ranges=highlight?.ranges.filter(range=>range.card===cardIndex)??[];
 const container=useRef<HTMLDivElement>(null);
 const boxes=useRenderedWordBoxes(container,`${cardIndex}:${highlight?.frame??-1}:${fontSize}`,source.fontFamily,source.fontWeight??400,'cells');
 const progress=content.typeCommand===false?1:Math.max(0,Math.min(1,(frame-startFrame+1)/source.typeFrames));
 const command=(content.command??'').slice(0,Math.floor((content.command??'').length*progress));
 return <>
  <div style={{position:'absolute',inset:0,background:look.background}}/>
  <div style={{position:'absolute',left:shell[0],top:shell[1],width:shell[2],height:shell[3],background:source.background,borderRadius:panel.borderRadius}}/>
  <div style={{position:'absolute',left:left+padding,top:top+padding,width:textWidth,fontFamily:source.fontFamily,fontWeight:source.fontWeight,color:source.text}}>
   <div style={{fontSize:source.fontSize*commandScale,lineHeight:`${commandRowHeight}px`,height:commandRowHeight,whiteSpace:'pre'}}>{content.command?<><span style={{color:source.prompt}}>{content.prompt}</span>{command}</>:content.header}</div>
   <div ref={container} style={{position:'absolute',top:cardTop,width:textWidth,fontSize,lineHeight:`${rowHeight}px`}}>
    {boxes.map(box=><div key={box.index} style={{position:'absolute',left:box.left-padding,top:box.top-padding,width:box.width+2*padding,height:box.height+2*padding,background:source.highlight.color,borderRadius:source.highlight.borderRadius==='half'?(box.height+2*padding)/2:source.highlight.borderRadius}}/>)}
    {card?.rows.map((row,rowIndex)=><div key={rowIndex} style={{position:'absolute',top:rowIndex*rowHeight,height:rowHeight,whiteSpace:'pre'}}>{rowCells(row).map((cell:{text:string;column:number;width:number})=>{
     const rangeIndex=ranges.findIndex(range=>range.row===rowIndex&&cell.column<range.column+range.length&&cell.column+cell.width>range.column);
     return <span key={cell.column} data-pill-word-index={rangeIndex>=0?rangeIndex:undefined} style={{position:'relative',display:'inline-block',width:cellWidth*cell.width,height:rowHeight,color:rangeIndex>=0?source.highlightText:source.text}}>{cell.text}</span>;
    })}</div>)}
   </div>
  </div>
 </>;
}
