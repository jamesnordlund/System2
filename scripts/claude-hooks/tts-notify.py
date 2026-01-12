#!/usr/bin/env python3
"""
tts-notify.py - TTS notification hook for Claude Code

This hook announces task completion audibly using platform-specific
text-to-speech commands. It triggers on Stop and SubagentStop events.

Inspiration: https://github.com/disler/claude-code-hooks-mastery

Usage:
    python3 tts-notify.py stop      # Announces "Task complete"
    python3 tts-notify.py subagent  # Announces "Subagent complete"

Exit codes:
    0 - Always (failures are silent)
"""
from __future__ import annotations

import subprocess
import sys

# Message mapping for hook types
MESSAGES = {
    "stop": "Task complete",
    "subagent": "Subagent complete",
}


def get_tts_command(message: str) -> list[str] | None:
    """Get the platform-specific TTS command.

    Args:
        message: The text to speak.

    Returns:
        List of command arguments, or None if no TTS available.
    """
    platform = sys.platform

    if platform == "darwin":
        # macOS: use built-in 'say' command
        return ["say", message]

    elif platform == "win32":
        # Windows: use PowerShell with SpeechSynthesizer
        ps_script = (
            f"Add-Type -AssemblyName System.Speech; "
            f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{message}')"
        )
        return ["powershell", "-Command", ps_script]

    elif platform.startswith("linux"):
        # Linux: check for espeak or spd-say
        import shutil

        if shutil.which("espeak"):
            return ["espeak", message]
        elif shutil.which("spd-say"):
            return ["spd-say", message]
        else:
            return None

    else:
        # Unsupported platform
        return None


def speak(message: str) -> None:
    """Speak a message using platform TTS.

    This function catches ALL exceptions silently - TTS failure
    should never cause the hook to report an error.

    Args:
        message: The text to speak.
    """
    try:
        tts_command = get_tts_command(message)
        if tts_command is None:
            return

        subprocess.run(
            tts_command,
            timeout=10,
            capture_output=True,
            shell=False,
        )
    except Exception:
        # Silently ignore all failures
        pass


def main() -> int:
    """Main entry point for the TTS notification hook.

    Returns:
        Always returns 0.
    """
    # Parse CLI argument
    if len(sys.argv) < 2:
        # No argument provided - exit silently
        return 0

    hook_type = sys.argv[1].lower()
    message = MESSAGES.get(hook_type)

    if message:
        speak(message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
