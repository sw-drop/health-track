Agent Operating Boundaries & Architecture

1. The Environment (Remote Docker Execution)
You are running natively on a macOS host, but the application runtime is located on a remote Linux server/host.

File Edits: You must only read and edit files locally on this Mac. Do NOT use ssh, scp, or rsync directly to edit files on the remote server.

Sync & Deployment:
Identify which deployment method the project uses:
- **Method A: Via deploy script (`deploy.sh`)**: If the project has a `deploy.sh` script, it likely relies on local-to-host syncing via rsync/ssh. Execute `./deploy.sh` from the Mac to sync files and deploy. Do NOT try to run `docker-compose --context` directly, as relative mounts in `docker-compose.yml` will fail on the remote host.
- **Method B: Via Direct Docker Context**: If there is no deploy script, compile and deploy directly from your local Mac environment by target-building via the context: `docker-compose --context [context_name] up --build -d`.
  - **Docker Compose Volumes Warning:** For direct context deployments, you must use explicit remote host absolute paths (e.g., `- /mnt/ssd/docker/<project>/data:/app/data`) in the `docker-compose.yml` file, not relative paths.
  - **Remote Directory Initialization:** If a remote host directory used for a bind mount does not exist, run a temporary container on the target context to create the directory with correct permissions on the remote filesystem (e.g., `docker --context [context_name] run --rm -v /mnt/ssd/docker:/mnt alpine mkdir -p /mnt/<project>/data`).

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

3. Versioning & Variables
Headers: Ensure a version number appears as a comment near/at the top of the code, incremented appropriately from the baseline.

Timestamps: Include a "last updated" string at the end of the key field.

4. Compliance Verification
Before concluding any task or /goal, you must explicitly state whether you have complied with these rules, confirm you did not hallucinate any layout changes, and state whether you had all necessary context to complete the request.
