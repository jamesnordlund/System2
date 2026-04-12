#!/usr/bin/env python3
"""TTS notification hook — announces task completion audibly."""
from __future__ import annotations

import subprocess
import sys

# Message mapping for hook types
MESSAGES = {
    "stop": "Task complete",
    "subagent": "Subagent complete",
}


def get_tts_command(message: str) -> list[str] | None:
    platform = sys.platform

    if platform == "darwin":
        # macOS: use built-in 'say' command
        return ["say", message]

    elif platform == "win32":
        # Windows: use PowerShell with SpeechSynthesizer
        escaped = message.replace("'", "''")
        ps_script = (
            f"Add-Type -AssemblyName System.Speech; "
            f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped}')"
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
    try:
        tts_command = get_tts_command(message)
        if tts_command is None:
            return

        subprocess.run(
            tts_command,
            timeout=10,
            capture_output=True,
        )
    except Exception:
        # Silently ignore all failures
        pass


def main() -> int:
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
