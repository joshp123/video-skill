// Written by AI on 2026-10-16 by GPT-6.1 Sol.
import {useLayoutEffect, useState, type RefObject} from 'react';
import {continueRender, delayRender} from 'remotion';

const fontLoading = new Map<string, Promise<void>>();
export function registerFontLoading(fontFamily: string, fontWeight: string, loading: Promise<void>) {
  fontLoading.set(`${fontFamily}:${fontWeight}`, loading);
}

export type RenderedWordBox = {index: number; left: number; top: number; width: number; height: number};

const renderedInkBounds = new Map<string, {left:number;top:number;width:number;height:number}>();
function inkBoundsForRenderedElement(element: HTMLElement) {
  const style = getComputedStyle(element);
  const font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
  const outline = parseFloat(style.webkitTextStrokeWidth) || 0;
  const text = element.textContent ?? '';
  const key = `${font}:${outline}:${text}`;
  const cached = renderedInkBounds.get(key);
  if (cached) return cached;
  const fontSize = parseFloat(style.fontSize);
  const scale = 4;
  const inset = Math.ceil(fontSize * 2);
  const canvas = document.createElement('canvas');
  const measuringContext = canvas.getContext('2d')!;
  measuringContext.font = font;
  canvas.width = Math.ceil((measuringContext.measureText(text).width + 2 * inset) * scale);
  canvas.height = Math.ceil(4 * fontSize * scale);
  const context = canvas.getContext('2d')!;
  context.scale(scale, scale);
  context.font = font;
  context.fillStyle = '#ffffff';
  if (outline) {context.strokeStyle='#ffffff';context.lineWidth=outline;context.strokeText(text,inset,inset);}
  context.fillText(text, inset, inset);
  const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
  let firstX = canvas.width, firstY = canvas.height, lastX = -1, lastY = -1;
  for (let y = 0; y < canvas.height; y++) for (let x = 0; x < canvas.width; x++) {
    if (!pixels[(y * canvas.width + x) * 4 + 3]) continue;
    firstX = Math.min(firstX, x); lastX = Math.max(lastX, x);
    firstY = Math.min(firstY, y); lastY = Math.max(lastY, y);
  }
  const box = {left: firstX / scale - inset, top: firstY / scale - inset, width: (lastX - firstX + 1) / scale, height: (lastY - firstY + 1) / scale};
  renderedInkBounds.set(key, box);
  return box;
}

// Use the rendered span's position, baseline and loaded computed font. Browser
// rasterization supplies the ink edges; logical font boxes include empty space.
export function useRenderedWordBoxes(container: RefObject<HTMLElement | null>, key: string, fontFamily: string, fontWeight: number, horizontalBounds: 'ink' | 'cells' = 'ink') {
  const [measurement, setMeasurement] = useState<{key: string; boxes: RenderedWordBox[]} | null>(null);
  useLayoutEffect(() => {
    if (!container.current) return;
    const renderHandle = delayRender('Measure rendered word boxes');
    let cancelled = false;
    const fontSize = getComputedStyle(container.current).fontSize;
    const loading = fontLoading.get(`${fontFamily}:${fontWeight}`) ?? document.fonts.load(`${fontWeight} ${fontSize} "${fontFamily}"`);
    loading.then(() => {
      if (cancelled || !container.current) return;
      const containerRectangle = container.current.getBoundingClientRect();
      const origin = {left: containerRectangle.left + container.current.clientLeft, top: containerRectangle.top + container.current.clientTop};
      const textBoxes = Array.from(container.current.querySelectorAll<HTMLElement>('[data-pill-word-index]')).filter(element => element.textContent?.trim()).map(element => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const box = horizontalBounds === 'cells' ? element.getBoundingClientRect() : range.getBoundingClientRect();
        const marker = document.createElement('span');
        Object.assign(marker.style, {display:'inline-block',width:'0',height:'0',verticalAlign:'baseline'});
        element.append(marker);
        const baseline = marker.getBoundingClientRect().top - origin.top;
        marker.remove();
        const ink = inkBoundsForRenderedElement(element);
        return {index: Number(element.dataset.pillWordIndex), left: box.left - origin.left + (horizontalBounds === 'cells' ? 0 : ink.left), top: baseline + ink.top, width: horizontalBounds === 'cells' ? box.width : ink.width, height: ink.height};
      });
      const boxesByIndex = new Map<number, RenderedWordBox>();
      for (const box of textBoxes) {
        const previous = boxesByIndex.get(box.index);
        if (!previous) {boxesByIndex.set(box.index, box); continue;}
        const left = Math.min(previous.left, box.left), top = Math.min(previous.top, box.top);
        const right = Math.max(previous.left + previous.width, box.left + box.width);
        const bottom = Math.max(previous.top + previous.height, box.top + box.height);
        boxesByIndex.set(box.index, {index:box.index,left,top,width:right-left,height:bottom-top});
      }
      const boxes = Array.from(boxesByIndex.values());
      setMeasurement({key, boxes});
      continueRender(renderHandle);
    });
    return () => {cancelled = true; continueRender(renderHandle);};
  }, [container, key, fontFamily, fontWeight, horizontalBounds]);
  return measurement?.key === key ? measurement.boxes : [];
}

export function useGlyphBounds(fontFamily: string, fontSize: number, fontWeight: number, lineHeight: number) {
  const [measurement, setMeasurement] = useState<{baseline: number; context: CanvasRenderingContext2D} | null>(null);
  useLayoutEffect(() => {
    const renderHandle = delayRender('Measure the loaded font baseline');
    const font = `${fontWeight} ${fontSize}px "${fontFamily}"`;
    (fontLoading.get(`${fontFamily}:${fontWeight}`) ?? document.fonts.load(font)).then(() => {
      const line = document.createElement('div');
      Object.assign(line.style, {position: 'absolute', left: '-10000px', top: '0', visibility: 'hidden', whiteSpace: 'pre', fontFamily, fontSize: `${fontSize}px`, fontWeight: String(fontWeight), lineHeight: `${lineHeight}px`});
      line.append(document.createTextNode('Hg'));
      const baselineMarker = document.createElement('span');
      Object.assign(baselineMarker.style, {display: 'inline-block', width: '0', height: '0', verticalAlign: 'baseline'});
      line.append(baselineMarker);
      document.body.append(line);
      const baseline = baselineMarker.getBoundingClientRect().top - line.getBoundingClientRect().top;
      line.remove();
      const context = document.createElement('canvas').getContext('2d')!;
      context.font = font;
      setMeasurement({baseline, context});
      continueRender(renderHandle);
    });
  }, [fontFamily, fontSize, fontWeight, lineHeight]);
  return (text: string) => {
    if (!measurement) return {top: 0, height: lineHeight};
    const glyphs = measurement.context.measureText(text);
    return {top: measurement.baseline - glyphs.actualBoundingBoxAscent, height: glyphs.actualBoundingBoxAscent + glyphs.actualBoundingBoxDescent};
  };
}
