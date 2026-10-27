#!/usr/bin/env python3
"""Written by AI on 2026-10-21 by GPT-6.1 Sol. Capture a supplied command through a PTY."""
import argparse
import errno
import fcntl
import os
import pty
import struct
import subprocess
import termios
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Capture a command at a real terminal width")
    parser.add_argument("--columns", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if arguments.columns < 1:
        parser.error("--columns must be positive")
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, arguments.columns, 0, 0))
    environment = dict(os.environ, COLUMNS=str(arguments.columns), LINES="40", TERM="xterm-256color")
    command_arguments = arguments.arguments
    if command_arguments[:1] == ["--"]:
        command_arguments = command_arguments[1:]
    process = subprocess.Popen(command_arguments, stdin=slave, stdout=slave, stderr=slave, env=environment)
    os.close(slave)
    captured = bytearray()
    try:
        while True:
            try:
                chunk = os.read(master, 65536)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            captured.extend(chunk)
    finally:
        os.close(master)
    status = process.wait()
    if status:
        raise SystemExit(f"Command exited with status {status}; capture not written")
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(captured)
    print(f"Captured {len(captured)} bytes at {arguments.columns} columns to {output}")


if __name__ == "__main__":
    main()
