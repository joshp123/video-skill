// Written by AI on 2026-10-16 by GPT-6 Codex. Exact repeat detector lifted from the old project.
// Edited 2026-10-21 by Claude Opus 5.5 (pipeline cleanup): output buffers sized from the file's frame count, not a fixed 8 MB.
import {execFileSync} from 'node:child_process';
export function scanFlashes(videoPath, cueFrames = []) {
  const frameCount = parseInt(execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', videoPath], {encoding: 'utf8'}), 10);
  const maxBuffer = (frameCount + 1) * 1024;
  const rows = execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', videoPath, '-map', '0:v:0', '-pix_fmt', 'rgba', '-f', 'framemd5', '-'], {encoding: 'utf8', maxBuffer}).split('\n').filter((line) => line && !line.startsWith('#'));
  const hashes = rows.map((line) => line.split(',').at(-1).trim());
  const isolatedFrames = [];
  for (let frame = 1; frame < hashes.length - 1; frame++) {
    if (hashes[frame - 1] === hashes[frame + 1] && hashes[frame] !== hashes[frame - 1]) isolatedFrames.push(frame);
  }
  const samples=execFileSync('ffmpeg',['-v','error','-i',videoPath,'-map','0:v:0','-vf','scale=32:32,format=gray','-f','rawvideo','-'],{maxBuffer});
  const means=[];
  for(let offset=0;offset<samples.length;offset+=1024){let sum=0;for(const value of samples.subarray(offset,offset+1024))sum+=value;means.push(sum/1024);}
  const brightnessSpikes=[];
  for(let frame=1;frame<means.length-1;frame++)if(Math.abs(means[frame-1]-means[frame+1])<6&&Math.abs(means[frame]-means[frame-1])>18&&Math.abs(means[frame]-means[frame+1])>18)brightnessSpikes.push(frame);
  const frameDifference=(a,b)=>{let sum=0;for(let pixel=0;pixel<1024;pixel++)sum+=Math.abs(samples[a*1024+pixel]-samples[b*1024+pixel]);return sum/1024;};
  const pictureOutliers=[];
  for(let frame=1;frame<means.length-1;frame++){
    const before=frameDifference(frame-1,frame),after=frameDifference(frame,frame+1),neighbors=frameDifference(frame-1,frame+1);
    if(before>12&&after>12&&neighbors<Math.min(before,after)*.4)pictureOutliers.push(frame);
  }
  const significantIsolatedFrames=isolatedFrames.filter(frame=>frameDifference(frame-1,frame)>1);
  return {decodedFrames: hashes.length, isolatedFrames:significantIsolatedFrames, brightnessSpikes,pictureOutliers, unexpectedFrames: [...new Set([...significantIsolatedFrames,...brightnessSpikes,...pictureOutliers])].filter((frame) => !cueFrames.includes(frame))};
}
if (process.argv[1]?.endsWith('scan-flashes.mjs')) for (const file of process.argv.slice(2)) console.log(file, scanFlashes(file));
