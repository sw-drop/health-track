#!/bin/bash
# Deploys the project to Git, pushes to the remote DietPi server, and restarts containers.

COMMIT_MSG=${1:-"Elevate Nginx to global infra and serve HTML via API"}

echo "--- 1. Committing and pushing to GitHub ---"
git add .
git commit -m "$COMMIT_MSG"
git push

echo "--- 2. Syncing files to Eadu (DietPi) via rsync ---"
rsync -avz --exclude 'legacy_eufy' --exclude '.git' ./ Eadu:/mnt/ssd/docker/eufy/

if [ $? -eq 0 ]; then
    echo "--- 3. Restarting containers on Eadu ---"
    # Stop old legacy health stack if it was running and remove orphans
    ssh Eadu 'cd /mnt/ssd/docker/eufy && docker compose down --remove-orphans'
    
    # Start the new health dashboard stack
    ssh Eadu 'cd /mnt/ssd/docker/eufy && docker compose up -d --build'
    
    # Run the ingestion script in the background to populate the new database
    ssh Eadu 'docker start health_ingest'

    echo "Deployment successfully completed!"
else
    echo "Error pushing changes via rsync."
    exit 1
fi
