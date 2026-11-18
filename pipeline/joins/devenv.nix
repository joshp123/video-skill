# Written by AI on 2026.11.17 by model Claude Opus 5.5: the join placer and checker (README.md).
# Python packages come from requirements.txt into .devenv/state/venv (uv); models download once to ~/.cache/join-check.
{ pkgs, config, ... }:
{
  packages = [ pkgs.python312 pkgs.uv pkgs.ffmpeg ];
  env.UV_PYTHON = "${pkgs.python312}/bin/python3.12";
  env.UV_PYTHON_DOWNLOADS = "never";
  enterShell = ''
    venv="${config.env.DEVENV_STATE}/venv"
    if [ ! -x "$venv/bin/python" ] || ! cmp -s requirements.txt "$venv/requirements.txt"; then
      uv venv -q --allow-existing "$venv" && uv pip install -q --python "$venv/bin/python" -r requirements.txt \
        && cp requirements.txt "$venv/requirements.txt"
    fi
  '';
}
