// Written by AI on 2026-10-16 by GPT-6 Codex. Director's C: One family.
// Installed JetBrains Bold/ExtraBold; terminal 35.9px fits 44 cells in the safe 950px width.
export default {
  name: 'one-family', letter: 'C', label: 'One family', background: '#171717',
  fonts: [
    {family: 'Candidate JetBrains', src: 'fonts/jetbrains-bold.ttf', weight: 700},
    {family: 'Candidate JetBrains', src: 'fonts/jetbrains-extrabold.ttf', weight: 800},
  ],
  terminal: {
    fontFamily: 'Film Mono', fontSize: 35.9, fontWeight: 400, cellWidth: 21.54, rowHeight: 48.465,
    background: '#0B0D10', text: '#E7E9EC', prompt: '#6C7480',
    highlightText: '#ffffff', highlightBackground: '#3D8BFF',
    panel: {inset: 0, padding: 60, borderRadius: 0},
    highlight: {kind: 'selection', color: '#3D8BFF', drawFrames: 5, fadeFrames: 0, easing: [0,0,1,1]},
    zoomFrames: 8, zoomEasing: [0,0,.58,1],
    typeFrames: 8, printFrames: 2, scrollFrames: 8, scrollEasing: [0,0,.58,1],
  },
  subtitles: {
    fontFamily: 'Candidate JetBrains', fontSize: 62, fontWeight: 800, lineHeight: 60/62,
    color: '#ffffff', shadow: 'none', outlineWidth: 0, outlineColor: 'transparent',
    align: 'left', maxCharacters: 26, background: 'rgba(11,13,16,.82)', padding: [10,10], borderRadius: 0,
    maxLines: 2, avoidLastLineSingleWord: true, textMetrics: {"advances":{" ":37.200000000000003,"_":37.200000000000003,"-":37.200000000000003,"–":37.200000000000003,"—":37.200000000000003,",":37.200000000000003,";":37.200000000000003,":":37.200000000000003,"!":37.200000000000003,"?":37.200000000000003,".":37.200000000000003,"…":37.200000000000003,"'":37.200000000000003,"‘":37.200000000000003,"’":37.200000000000003,"\"":37.200000000000003,"“":37.200000000000003,"”":37.200000000000003,"(":37.200000000000003,")":37.200000000000003,"[":37.200000000000003,"]":37.200000000000003,"{":37.200000000000003,"}":37.200000000000003,"@":37.200000000000003,"*":37.200000000000003,"\/":37.200000000000003,"\\":37.200000000000003,"&":37.200000000000003,"#":37.200000000000003,"%":37.200000000000003,"`":37.200000000000003,"^":37.200000000000003,"+":37.200000000000003,"<":37.200000000000003,"=":37.200000000000003,">":37.200000000000003,"|":37.200000000000003,"~":37.200000000000003,"$":37.200000000000003,"0":37.200000000000003,"1":37.200000000000003,"2":37.200000000000003,"3":37.200000000000003,"4":37.200000000000003,"5":37.200000000000003,"6":37.200000000000003,"7":37.200000000000003,"8":37.200000000000003,"9":37.200000000000003,"a":37.200000000000003,"A":37.200000000000003,"b":37.200000000000003,"B":37.200000000000003,"c":37.200000000000003,"C":37.200000000000003,"d":37.200000000000003,"D":37.200000000000003,"e":37.200000000000003,"E":37.200000000000003,"f":37.200000000000003,"F":37.200000000000003,"g":37.200000000000003,"G":37.200000000000003,"h":37.200000000000003,"H":37.200000000000003,"i":37.200000000000003,"I":37.200000000000003,"j":37.200000000000003,"J":37.200000000000003,"k":37.200000000000003,"K":37.200000000000003,"l":37.200000000000003,"L":37.200000000000003,"m":37.200000000000003,"M":37.200000000000003,"n":37.200000000000003,"N":37.200000000000003,"o":37.200000000000003,"O":37.200000000000003,"p":37.200000000000003,"P":37.200000000000003,"q":37.200000000000003,"Q":37.200000000000003,"r":37.200000000000003,"R":37.200000000000003,"s":37.200000000000003,"S":37.200000000000003,"t":37.200000000000003,"T":37.200000000000003,"u":37.200000000000003,"U":37.200000000000003,"v":37.200000000000003,"V":37.200000000000003,"w":37.200000000000003,"W":37.200000000000003,"x":37.200000000000003,"X":37.200000000000003,"y":37.200000000000003,"Y":37.200000000000003,"z":37.200000000000003,"Z":37.200000000000003},"fontSize":62,"kerning":{}},
    popFrames: 0, popScale: 1,
  },
  photos: {
    labelFontFamily: 'Candidate JetBrains', labelFontSize: 34, labelFontWeight: 700,
    labelLineHeight: 1, labelColor: '#ffffff', labelShadow: 'none', labelBackground: 'transparent',
    labelPadding: [0,0], labelBorderRadius: 0, labelUppercase: true,
    labelMarker: {size: 14, color: '#3D8BFF'}, labelFadeFrames: 0, anchor: [60,230],
  },
  card: {
    fontFamily: 'Candidate JetBrains', fontWeight: 700, fontSize: 60,
    linkFontFamily: 'Candidate JetBrains', linkFontWeight: 700, linkFontSize: 44,
    color: '#ffffff', linkColor: '#3D8BFF', linkBackground: 'transparent', linkPadding: [0,0], linkBorderRadius: 0,
    dim: .55, align: 'left', blockCenterY: 960, shadow: 'none',
    background: 'transparent', borderWidth: 0, padding: 0, gap: 48,
  },
};
