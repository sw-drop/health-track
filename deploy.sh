#!/bin/bash
# Deploys the project to Git, pushes to the remote DietPi server, and restarts containers.

COMMIT_MSG=${1:-"Update to Apple Health Grafana stack"}

echo "--- 1. Committing and pushing to GitHub ---"
git add .
git commit -m "$COMMIT_MSG"
git push

echo "--- 2. Syncing files to Eadu (DietPi) via rsync ---"
# Syncing the new configuration and Apple_Health data (excluding the legacy backup)
rsync -avz --exclude 'legacy_eufy' --exclude '.git' ./ Eadu:/mnt/ssd/docker/eufy/

if [ $? -eq 0 ]; then
    echo "--- 3. Restarting containers on Eadu ---"
    ssh Eadu 'cd /mnt/ssd/docker/eufy && docker compose down --remove-orphans && docker compose up -d --build'
    echo "Deployment successfully completed!"
else
    echo "Error pushing changes via rsync."
    exit 1
fi
