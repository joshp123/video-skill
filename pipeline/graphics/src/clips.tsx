// Written by AI on 2026-10-17 by GPT-6 Codex.
import React from 'react';
import {Composition,registerRoot} from 'remotion';
import {GraphicClip} from './GraphicClip';
function ClipsRoot(){return <Composition id="graphic-clip" component={GraphicClip as any} durationInFrames={1} fps={25} width={1080} height={1920} defaultProps={{data:null,graphicId:''}} calculateMetadata={({props}:any)=>{const graphic=props.data.graphics.find((graphic:any)=>graphic.id===props.graphicId);return {durationInFrames:graphic.endFrame-graphic.startFrame,...props.data.format};}}/>;}
registerRoot(ClipsRoot);
