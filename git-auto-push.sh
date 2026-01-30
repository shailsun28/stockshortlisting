#!/bin/bash
cd ~/stockshortlisting || exit

# Stage changes
git add -A

# Commit only if there are changes
if ! git diff --cached --quiet; then
    git commit -m "Auto-update on $(date '+%Y-%m-%d %H:%M:%S')"
    git pull --rebase origin main
    git push origin main
fi

