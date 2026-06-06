#!/bin/bash
# Deploys the project to the remote DietPi server and restarts the containers.

echo "Pushing changes to Eadu (DietPi)..."
rsync -avz --exclude 'data' --exclude 'eufylife-api-hacs' --exclude '.git' ./ Eadu:/docker/eufy/

if [ $? -eq 0 ]; then
    echo "Changes pushed successfully. Restarting containers on Eadu..."
    ssh Eadu 'cd /docker/eufy && docker compose down && docker compose up -d --build'
    echo "Deployment complete!"
else
    echo "Error pushing changes via rsync."
    exit 1
fi
