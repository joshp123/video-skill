// Written by AI on 2026-10-16 by GPT-6.1 Sol.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): one sizing rule for every column count with the pill padding from
// the look, the prompt colour over the prompt's own cells, a scroll that ends on its cue's endFrame; one video's special cases removed.
import React, {useRef} from 'react';
import {AskTerminal} from './AskTerminal';
import {Easing,useCurrentFrame} from 'remotion';
import {compileTerminalContent, rowCells} from '../terminal-content.mjs';
import {useRenderedWordBoxes} from './glyphBounds';

type Range = {row: number; column: number; length: number};
type Cue = {frame: number; endFrame?: number; action: string; index?: number; target?: string; range?: Range[]};
type TerminalProps = {
  content: {columns: number; prompt: string; command?: string; rows: string[]; words?: string[]; welcomeRows?: string[]};
  cues: Cue[];
  region: [number, number, number, number];
  panelRegion?: [number, number, number, number];
  look: any;
};

export const Terminal: React.FC<TerminalProps> = (props) => props.content.words!==undefined&&props.look.ask ? <AskTerminal {...props}/> : <CommandTerminal {...props}/>;

const CommandTerminal: React.FC<TerminalProps> = ({content, cues, region, panelRegion, look}) => {
  const frame = useCurrentFrame();
  const sourceValues = look.terminal;
  const [safeLeft, safeTop, safeWidth, safeHeight] = region;
  const panel = sourceValues.panel;
  const outer = panelRegion ?? region;
  const shell = panel ? [outer[0]+panel.inset,outer[1]+panel.inset,outer[2]-2*panel.inset,outer[3]-2*panel.inset] : region;
  const left = panel ? Math.max(safeLeft,shell[0]+panel.padding) : safeLeft;
  const top = panel ? Math.max(safeTop,shell[1]+panel.padding) : safeTop;
  const width = panel ? Math.min(safeLeft+safeWidth,shell[0]+shell[2]-panel.padding)-left : safeWidth;
  const height = panel ? Math.min(safeTop+safeHeight,shell[1]+shell[3]-panel.padding)-top : safeHeight;
  const padding = sourceValues.highlight.padding;
  const textWidth = width-2*padding;
  const characterScale = textWidth/(content.columns*sourceValues.cellWidth);
  const values = {...sourceValues,fontSize:sourceValues.fontSize*characterScale,cellWidth:sourceValues.cellWidth*characterScale,rowHeight:sourceValues.rowHeight*characterScale};
  const scrollEase = Easing.bezier(...values.scrollEasing as [number,number,number,number]);
  const visibleRows = Math.floor((height-2*padding) / values.rowHeight+1e-9);
  const typeCue = cues.find((cue) => cue.action === 'type');
  const typingStart = typeCue?.frame ?? 0;
  const typeProgress = typeCue ? Math.max(0, Math.min(1, (frame - typingStart + 1) / values.typeFrames)) : 1;
  const command = content.command ?? '';
  const promptRows: string[] = compileTerminalContent(content.prompt+command.slice(0,Math.floor(command.length*typeProgress)),content.columns).rows;
  const completedPromptRows: string[] = compileTerminalContent(content.prompt + command, content.columns).rows;
  const outputStart = typingStart + values.typeFrames;
  const outputProgress = typeCue ? Math.max(0, Math.min(1, (frame - outputStart + 1) / values.printFrames)) : 1;
  const displayedRows = [...promptRows,...content.rows.slice(0,Math.ceil(content.rows.length*outputProgress))];
  const cueRowsOffset = completedPromptRows.length;
  const maximumScrollRow = Math.max(0,content.rows.length+cueRowsOffset-visibleRows);
  const scrollEvents: {frame: number; duration: number; from: number; to: number}[] = [];
  let finalScrollRow = 0;
  for (const cue of cues) {
    if (!cue.range?.length || !['show', 'highlight', 'scroll'].includes(cue.action)) continue;
    const firstRow = Math.min(...cue.range.map((range) => range.row)) + cueRowsOffset;
    const lastRow = Math.max(...cue.range.map((range) => range.row)) + cueRowsOffset;
    let nextScrollRow = finalScrollRow;
    if (cue.action === 'scroll') nextScrollRow = lastRow - visibleRows + 1;
    else if (cue.action === 'show') nextScrollRow = firstRow;
    else if (firstRow < finalScrollRow) nextScrollRow = firstRow;
    else if (lastRow >= finalScrollRow + visibleRows) nextScrollRow = lastRow-visibleRows+1;
    nextScrollRow = Math.max(0, Math.min(nextScrollRow,maximumScrollRow));
    scrollEvents.push({frame:cue.frame,duration:cue.action==='scroll'&&cue.endFrame!==undefined?cue.endFrame-cue.frame:values.scrollFrames,from:finalScrollRow,to:nextScrollRow});
    finalScrollRow = nextScrollRow;
  }
  const currentScroll = scrollEvents.filter(event=>event.frame<=frame).at(-1);
  const scrollProgress = currentScroll ? scrollEase(Math.max(0,Math.min(1,(frame-currentScroll.frame)/Math.max(1,currentScroll.duration)))) : 0;
  let scrollRow = currentScroll ? Math.round(currentScroll.from+(currentScroll.to-currentScroll.from)*scrollProgress) : 0;
  const lastHighlight = cues.filter(cue=>cue.action==='highlight'&&cue.frame<=frame).at(-1);
  const ranges = lastHighlight?.range ?? [];
  // A newly named target is fully visible on its first highlighted frame.
  if(ranges.length&&(!currentScroll||currentScroll.frame<=lastHighlight!.frame)){
    const firstRow=Math.min(...ranges.map(range=>range.row))+cueRowsOffset;
    const lastRow=Math.max(...ranges.map(range=>range.row))+cueRowsOffset;
    if(lastRow-firstRow+1>visibleRows)throw new Error(`Terminal target cannot fit as whole rows: ${lastHighlight?.target}`);
    scrollRow=Math.max(0,Math.min(maximumScrollRow,Math.max(lastRow-visibleRows+1,Math.min(scrollRow,firstRow))));
  }
  const treatment = values.highlight;
  const textContainer = useRef<HTMLDivElement>(null);
  const renderedBoxes=useRenderedWordBoxes(textContainer,`${lastHighlight?.frame??-1}:${scrollRow}:${displayedRows.length}:${values.fontSize}`,values.fontFamily,values.fontWeight??400,'cells');
  const geometryPrefix=`terminal-${lastHighlight?.frame??-1}`;
  const overlays = treatment ? ranges : [];
  const promptCells = rowCells(content.prompt).reduce((cells:number,cell:{width:number})=>cells+cell.width,0);
  const visibleFirst=scrollRow;
  const visibleLast=scrollRow+visibleRows-1;
  return <>
    {panel && <div style={{position:'absolute',left:shell[0],top:shell[1],width:shell[2],height:shell[3],background:values.background,borderRadius:panel.borderRadius}}/>}
    <div style={{position:'absolute',left,top,width,height,overflow:'hidden',background:panel?undefined:values.background,fontFamily:values.fontFamily,fontSize:values.fontSize,fontWeight:values.fontWeight,lineHeight:`${values.rowHeight}px`,color:values.text}}>
      <div ref={textContainer} data-geometry-panel data-terminal-viewport data-scroll-row={scrollRow} data-row-height={values.rowHeight} style={{position:'absolute',left:padding,top:padding,width:textWidth,height:visibleRows*values.rowHeight}}>
        {treatment?.kind==='pill'&&renderedBoxes.map(box=><div key={`pill-${box.index}`} data-geometry-pill={`${geometryPrefix}-${box.index}`} data-geometry-kind="glyphs" data-padding-x={padding} data-padding-y={padding} style={{position:'absolute',left:box.left-padding,top:box.top-padding,width:box.width+2*padding,height:box.height+2*padding,background:treatment.color,borderRadius:treatment.borderRadius==='half'?(box.height+2*padding)/2:treatment.borderRadius}}/>)}
        {displayedRows.map((row,rowIndex)=>rowIndex<visibleFirst||rowIndex>visibleLast?null:<div key={rowIndex} data-terminal-row={rowIndex} data-geometry-row={rowIndex} style={{position:'absolute',top:(rowIndex-scrollRow)*values.rowHeight,height:values.rowHeight,whiteSpace:'pre'}}>
          {overlays.filter(range=>range.row===rowIndex-cueRowsOffset).map((range,index)=>{
            if(treatment.kind==='underline')return <div key={`underline-${index}`} style={{position:'absolute',left:range.column*values.cellWidth,bottom:treatment.underlineBottom,width:range.length*values.cellWidth,height:treatment.underlineHeight,background:treatment.color}}/>;
            if(treatment.kind==='pill')return null;
            return <div key={`background-${index}`} style={{position:'absolute',left:range.column*values.cellWidth,top:0,width:range.length*values.cellWidth,height:values.rowHeight,background:treatment.color}}/>;
          })}
          {rowCells(row).map((cell:{text:string;column:number;width:number})=>{
            const rangeIndex=ranges.findIndex(range=>range.row===rowIndex-cueRowsOffset&&cell.column<range.column+range.length&&cell.column+cell.width>range.column);
            const highlighted=rangeIndex>=0;
            const promptCell=rowIndex===0&&cell.column<promptCells;
            let color=highlighted?values.highlightText:promptCell?values.prompt:values.text;
            if(treatment?.kind==='underline')color=highlighted?treatment.color:color;
            else if(treatment?.kind==='selection')color=promptCell?values.prompt:values.text;
            return <span key={cell.column} data-pill-word-index={highlighted?rangeIndex:undefined} data-geometry-cell={cell.column} data-geometry-target={highlighted?`${geometryPrefix}-${rangeIndex}`:undefined} style={{position:treatment?'relative':undefined,display:'inline-block',width:values.cellWidth*cell.width,height:values.rowHeight,background:!treatment&&highlighted?values.highlightBackground:undefined,color}}>{cell.text}</span>;
          })}
          {treatment?.kind==='selection'&&overlays.filter(range=>range.row===rowIndex-cueRowsOffset).map((range,index)=><div key={`selected-text-${index}`} style={{position:'absolute',left:range.column*values.cellWidth,top:0,width:range.length*values.cellWidth,height:values.rowHeight,overflow:'hidden',whiteSpace:'pre',color:values.highlightText}}>{rowCells(row).filter((cell:{column:number})=>cell.column>=range.column&&cell.column<range.column+range.length).map((cell:{text:string;column:number;width:number})=><span key={cell.column} style={{display:'inline-block',width:cell.width*values.cellWidth,height:values.rowHeight}}>{cell.text}</span>)}</div>)}
        </div>)}
      </div>
    </div>
  </>;
};
