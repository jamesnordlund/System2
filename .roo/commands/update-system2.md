---
description: Update System2 modes and commands to the latest upstream version
mode: orchestrator
---

Run the System2 update script to check for and apply updates from the upstream repository.

Execute the following command:

```bash
bash scripts/update-system2.sh $ARGUMENTS
```

If the script is not found at that path, check if it exists at the project root or in the
user's home directory. If still not found, fetch it first:

```bash
curl -sL --max-time 30 https://raw.githubusercontent.com/jamesnordlund/System2/main/scripts/update-system2.sh -o scripts/update-system2.sh
chmod +x scripts/update-system2.sh
bash scripts/update-system2.sh $ARGUMENTS
```

Report the full output to the user. If the script reports that the update command itself was
updated, let the user know they can re-invoke /update-system2 to use the new version.
