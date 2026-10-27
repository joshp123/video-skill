# Written by AI on 2026-10-22 by GPT-6.1 Sol.
{ pkgs, ... }:
{
  # zstd: pipeline/subtitles/write_caption_track.py reads and writes Resolve's compressed caption records.
  packages = [ (pkgs.python312.withPackages (python: [ python.numpy ])) pkgs.ffmpeg pkgs.zstd ];
}
