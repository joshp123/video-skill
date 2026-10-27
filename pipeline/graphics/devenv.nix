{ pkgs, ... }:

{
  # Remotion graphics for the video pipeline: Node and ffmpeg.
  packages = [ pkgs.nodejs_24 pkgs.ffmpeg ];
}
