# Written by AI on 2026-10-22 by Claude Opus 5.5, fault pass after the codex-switch test.
# The verbatim transcriber's environment (verbatim_transcript.py beside it; the run line is in its header).
# micromamba added by AI on 2026-10-29 by Claude Opus 5.5: pipeline/b/align.py installs the Montreal Forced Aligner with it.
# Python 3.13 and uv; uv resolves the transcriber's packages from its cache, because the vendored
# CrisperWhisper decoder needs transformers 4.46.3 and nixpkgs ships transformers 5.
{ pkgs, ... }:
{
  packages = [ pkgs.python313 pkgs.uv pkgs.micromamba ];
  env.UV_PYTHON = "${pkgs.python313}/bin/python3.13";
  env.UV_PYTHON_DOWNLOADS = "never";
  env.HF_HOME = "/Volumes/Josh Extreme Pro USB4 4TB/OpenTrawl/system-cache-relief/huggingface";
  env.HF_HUB_OFFLINE = "1";
}
