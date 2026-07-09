#!/bin/bash
# Deploys the project to Git, pushes to the remote DietPi server, and restarts containers.

COMMIT_MSG=${1:-"Elevate Nginx to global infra and serve HTML via API"}

echo "--- 1. Committing and pushing to GitHub ---"
git add .
git commit -m "$COMMIT_MSG"
git push

echo "--- 2. Syncing files to Eadu (DietPi) via rsync ---"
rsync -avz --delete --exclude 'legacy_eufy' --exclude '.git' --exclude 'Apple_Health/' --exclude 'backups/' ./ Eadu:/mnt/ssd/docker/health/

if [ $? -eq 0 ]; then
    echo "--- 3. Restarting containers on Eadu ---"
    # Stop old legacy health stack if it was running and remove orphans
    ssh Eadu 'cd /mnt/ssd/docker/health && docker compose down --remove-orphans'
    
    # Start the new health dashboard stack
    ssh Eadu 'cd /mnt/ssd/docker/health && docker compose up -d --build'
    
    # Reload Nginx to ensure it picks up any new IP addresses for the eufy containers
    ssh Eadu 'docker exec global_nginx nginx -s reload'
    
    # Run the ingestion script in the background to populate the new database
    ssh Eadu 'docker start health_ingest'

    echo "Deployment successfully completed!"
else
    echo "Error pushing changes via rsync."
    exit 1
fi
