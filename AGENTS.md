Agent Operating Boundaries & Architecture

1. The Environment (Remote Docker Execution)
You are running natively on a macOS host, but the application runtime is located on a remote Linux server/host.

File Edits: You must only read and edit files locally on this Mac. Do NOT use ssh, scp, or rsync to edit files on the remote server.

Sync & Deployment:
- Check if the project uses Docker Compose Watch or requires rebuilding the image to apply local code changes. Do not assume local modifications auto-sync unless explicitly configured.
- **No Remote SSH/Rsync Deployments:** Do not attempt to run `ssh`, `rsync`, or local deployment scripts (like `deploy.sh`) to sync files or start containers on the remote host. You must compile and deploy directly from your local Mac environment by target-building via the context: `docker-compose --context [context_name] up --build -d`.
- **Docker Compose Volumes Warning:** Because `docker-compose` on Mac expands relative paths (like `./data`) into Mac absolute paths before sending them to the remote daemon, using relative host paths for bind mounts will cause the remote daemon to create empty folders on the host. To ensure containers mount the remote host's data, **you must use the remote host's explicit absolute paths** (e.g., `- /mnt/ssd/docker/<project>/data:/app/data`) in the `docker-compose.yml` file.
- **Remote Directory Initialization:** If a remote host directory used for a bind mount does not exist, do not use SSH to create it. Instead, you can run a temporary container on the target context to create the directory with correct permissions on the remote filesystem (e.g., `docker --context [context_name] run --rm -v /mnt/ssd/docker:/mnt alpine mkdir -p /mnt/<project>/data`).

Docker & Git Commands: 
- `docker`, `docker-compose`, and `git` are available directly in your PATH.
- Do NOT use stateful commands like `docker context use`. This creates shell session dependency and causes authorization prompts.
- Always run stateless commands by appending the `--context` flag directly.
  - Example: `docker --context [context_name] ps`
  - Example: `docker-compose --context [context_name] up --build -d`
  - Example: `docker-compose --context [context_name] exec [service] [command]`

2. Strict Coding Baselines (Non-Negotiable)
Surgical Increments: Use strict character-matching. Provide only changes to the exact lines that must be changed. Do not rewrite whole files or make unrequested "optimisations."

UI Lock: Existing HTML/CSS structures are completely locked. Do not make any change that might affect the layout or content other than the specifically requested logic.

Code Presentation: When outputting code, describe the exact lines changed, but return the file in full.

3. Versioning & Variables
Headers: Ensure a version number appears as a comment near/at the top of the code, incremented appropriately from the baseline.

Timestamps: Include a "last updated" string at the end of the key field.

Authentication: If updating app.py, ensure the application pin remains strictly set to "far too many clouds".

4. Compliance Verification
Before concluding any task or /goal, you must explicitly state whether you have complied with these rules, confirm you did not hallucinate any layout changes, and state whether you had all necessary context to complete the request.
