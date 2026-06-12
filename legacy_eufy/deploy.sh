#!/bin/bash
# Deploys the project to Git, pushes to the remote DietPi server, and restarts containers.

COMMIT_MSG=${1:-"chore: automate deployment updates"}

echo "--- 1. Committing and pushing to GitHub ---"
git add .
git commit -m "$COMMIT_MSG"
git push

echo "--- 2. Syncing files to Eadu (DietPi) via rsync ---"
rsync -avz --exclude 'data' --exclude 'eufylife-api-hacs' --exclude '.git' ./ Eadu:/docker/eufy/

if [ $? -eq 0 ]; then
    echo "--- 3. Restarting containers on Eadu ---"
    ssh Eadu 'cd /docker/eufy && docker compose down && docker compose up -d --build'
    echo "Deployment successfully completed!"
else
    echo "Error pushing changes via rsync."
    exit 1
fi
