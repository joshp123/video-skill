"""Write the record of what Josh said about a video, from Claude Code and Codex sessions.

Written by AI on 2026-10-21 by GPT-6.1 Sol; originally by Claude Opus 5.5.
--messages-matching and the per-session mention count added by AI on 2026-10-22 by
Claude Opus 5.5, fault pass after the codex-switch test.

Every message Josh typed is kept verbatim, with the agent text he was most likely
replying to and any files the agent had shown him since his previous message.

- Claude Code stores messages Josh typed while an agent was working as
  queued_command attachments, not as user turns; naive extraction
  silently drops them. Instructions the harness injects into a user turn
  ("Codebase and user instructions are shown below...") are not his and are dropped.
- Codex: only turns Josh typed himself count: in the desktop app ("composer"), from his
  phone ("remote_ios"), or by editing a message ("edit_user_message"). Briefs sent by
  other agents ("exec" turns) and Codex's own safety reviews do not.

    python3 -B record.py --list PATTERN               # candidate sessions from the last 60 days
    python3 -B record.py OUTPUT.md SESSION.jsonl ...  # write the record from chosen sessions
    python3 -B record.py OUTPUT.md SESSION.jsonl ... --messages-matching PATTERN

PATTERN is a case-insensitive regular expression, such as a video's slug or the names of
its tool ('codex[ -]?switch|codex-lb'). --list counts its matches in each session and in
his messages there. --messages-matching is for a video with no thread of its own, such as
the second video from a recording session: it keeps only his messages where PATTERN
matches his words or the agent text he was answering.
"""
JOSH_TURN_TRIGGERS = {"composer", "remote_ios", "edit_user_message"}
import json
import re
import sys
import time
from pathlib import Path

CLAUDE_SESSIONS = Path.home() / ".claude" / "projects"
CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
LIST_WINDOW_DAYS = 60
NOT_JOSH_PREFIXES = (
    "Task:", "<cross-session-message", "<agent-message", "Another Claude session sent a message", "[Subagent hand-back]", "[Agent-to-agent", "[Task from",
    "<task-notification>",
    "<command-name>",
    "<local-command-stdout>",
    "[Request interrupted",
    "Codebase and user instructions are shown below",
)


def text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        kind = block.get("type")
        if kind in ("text", "input_text", "output_text"):
            parts.append(block.get("text", ""))
        elif kind in ("image", "input_image"):
            parts.append("[image attached]")
    return "\n".join(parts)


def cleaned(text):
    if not isinstance(text, str):
        return None
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<in-app-browser-context\b.*?</in-app-browser-context>", "", text, flags=re.S).strip()
    if not text or text.startswith(NOT_JOSH_PREFIXES):
        return None
    return text


def claude_events(path):
    """Yield (timestamp, kind, text) with kind in josh, agent, shown."""
    for line in open(path):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("isSidechain"):
            continue
        timestamp = entry.get("timestamp", "")
        typed = None
        if entry.get("type") == "user" and not entry.get("isMeta") and not entry.get("isCompactSummary"):
            typed = text_of(entry["message"]["content"])
        elif (entry.get("attachment") or {}).get("type") == "queued_command":
            prompt = entry["attachment"].get("prompt")
            typed = prompt if isinstance(prompt, str) else text_of(prompt)
        typed = cleaned(typed)
        if typed:
            yield timestamp, "josh", typed
            continue
        if entry.get("type") != "assistant":
            continue
        for block in entry["message"].get("content", []):
            if block.get("type") == "text" and block["text"].strip():
                yield timestamp, "agent", block["text"].strip()
            elif block.get("type") == "tool_use" and block.get("name") == "SendUserFile":
                shown = block["input"]
                caption = f" ({shown['caption']})" if shown.get("caption") else ""
                yield timestamp, "shown", ", ".join(shown.get("files", [])) + caption


def codex_events(path):
    """Yield (timestamp, kind, text): Josh's composer turns and the agent's replies."""
    trigger_by_turn = {}
    for line in open(path):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = entry.get("timestamp", "")
        payload = entry.get("payload") or {}
        if entry.get("type") == "event_msg" and payload.get("type") == "task_started":
            attribution = payload.get("turn_attribution") or {}
            trigger_by_turn[attribution.get("turn_id")] = attribution.get("turn_trigger")
        elif entry.get("type") == "event_msg" and payload.get("type") == "item_completed":
            item = payload.get("item") or {}
            if item.get("type") == "UserMessage" and trigger_by_turn.get(payload.get("turn_id")) in JOSH_TURN_TRIGGERS:
                typed = cleaned(text_of(item.get("content")))
                if typed:
                    yield timestamp, "josh", typed
        elif entry.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "assistant":
            text = text_of(payload.get("content")).strip()
            if text:
                yield timestamp, "agent", text


def events_of(path):
    path = Path(path)
    return codex_events(path) if CODEX_SESSIONS in path.parents else claude_events(path)


def write_record(output_path, session_paths, messages_matching=None):
    events = sorted(((*event, str(path)) for path in session_paths for event in events_of(path)),
                    key=lambda event: event[0])
    last_agent_text = {}
    files_shown = {}
    sections = []
    already_kept = set()  # a forked session repeats its parent's messages
    for timestamp, kind, text, session in events:
        if kind == "agent":
            last_agent_text[session] = text
        elif kind == "shown":
            files_shown.setdefault(session, []).append(text)
        elif (timestamp, text) in already_kept or (
                messages_matching and not (messages_matching.search(text)
                                           or messages_matching.search(last_agent_text.get(session, "")))):
            files_shown[session] = []
        else:
            already_kept.add((timestamp, text))
            section = [f"## Josh, {timestamp[:16].replace('T', ' ')} UTC"]
            if files_shown.get(session):
                section.append("Files the agent had shown him since his last message: " + "; ".join(files_shown[session]))
            if last_agent_text.get(session):
                section.append("The agent's last words before this:\n\n> " + last_agent_text[session].replace("\n", "\n> "))
            section.append("Josh:\n\n" + text)
            sections.append("\n\n".join(section))
            files_shown[session] = []
    kept = (f", keeping only his messages where /{messages_matching.pattern}/ (any case) matches his words"
            " or the agent text he was answering") if messages_matching else ""
    header = (
        "# What Josh said\n\n"
        f"Generated by record.py from {len(session_paths)} session(s): "
        + ", ".join(str(path) for path in session_paths)
        + f"{kept}. {len(sections)} messages from Josh. Do not edit; regenerate.\n"
    )
    Path(output_path).write_text(header + "\n\n" + "\n\n---\n\n".join(sections) + "\n")
    print(f"{output_path}: {len(sections)} messages from Josh")


def list_sessions(pattern):
    cutoff = time.time() - LIST_WINDOW_DAYS * 86400
    candidates = list(CLAUDE_SESSIONS.glob("*/*.jsonl")) + list(CODEX_SESSIONS.glob("*/*/*/*.jsonl"))
    rows = []
    for session in candidates:
        if not session.exists() or session.stat().st_mtime < cutoff:
            continue
        raw = session.read_text(errors="ignore")
        mentions = len(pattern.findall(raw))
        if not mentions:
            continue
        josh_messages = list(dict.fromkeys(text for _, kind, text in events_of(session) if kind == "josh"))
        if not josh_messages:
            continue
        his_mentions = sum(1 for message in josh_messages if pattern.search(message))
        timestamps = re.findall(r'"timestamp":"([^"]+)"', raw)
        first, last = (min(timestamps), max(timestamps)) if timestamps else ("?", "?")
        rows.append((last, first, mentions, len(josh_messages), his_mentions, session, josh_messages[0]))
    for last, first, mentions, count, his_mentions, session, opening in sorted(rows, reverse=True):
        print(f"{first[:16]} to {last[:16]}  {count} messages from Josh ({his_mentions} name it), "
              f"{mentions} mentions in all  {session}")
        print(f"    starts: {opening[:200]!r}")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    messages_matching = None
    if "--messages-matching" in arguments:
        at = arguments.index("--messages-matching")
        if at + 1 >= len(arguments):
            sys.exit(__doc__)
        messages_matching = re.compile(arguments[at + 1], re.IGNORECASE)
        del arguments[at:at + 2]
    if len(arguments) == 2 and arguments[0] == "--list" and not messages_matching:
        list_sessions(re.compile(arguments[1], re.IGNORECASE))
    elif len(arguments) >= 2 and arguments[0] != "--list":
        write_record(arguments[0], arguments[1:], messages_matching)
    else:
        sys.exit(__doc__)
