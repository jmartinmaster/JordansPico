
#!/usr/bin/env bash
set -euo pipefail

# Configuration (filled for your repo)
REPO_URL="https://github.com/jmartinmaster/AIMartinSuiteGLCVersion.git"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="AIMartinSuiteGLCVersion-backup-${TIMESTAMP}.git"
REWRITE_DIR="AIMartinSuiteGLCVersion-rewrite-${TIMESTAMP}.git"
REMOVE_PATHS=( "rates.json" "dist/" )

# Helpers
err() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "INFO: $*"; }

echo
echo "This script will permanently remove the following from ALL commits, branches and tags in:"
echo "  $REPO_URL"
for p in "${REMOVE_PATHS[@]}"; do echo "   - $p"; done
echo
echo "What this DOES:"
echo " - Makes a mirror backup of the repo (safe copy) in: $BACKUP_DIR"
echo " - Makes a second mirror copy to rewrite in: $REWRITE_DIR"
echo " - Runs git-filter-repo to remove the specified file/folder from all refs"
echo " - Cleans and repacks the rewritten repo"
echo " - (OPTIONAL) Force-pushes rewritten refs back to origin (you will be prompted)"
echo
echo "WARNING:"
echo " - This rewrites history. Commit SHAs change. Everyone must reclone or reset to the new history."
echo " - If rates.json contained secrets, rotate/revoke them immediately (removal from git does not guarantee no leakage)."
echo " - You said branch protections are not enabled and there are no forks. Still, double-check any external integrations."
echo

read -p "Type 'yes' to continue, anything else to abort: " confirm
if [[ "${confirm}" != "yes" ]]; then
  echo "Aborted by user."
  exit 0
fi

# Check required commands
command -v git >/dev/null 2>&1 || err "git is required but not found in PATH."
if command -v git-filter-repo >/dev/null 2>&1; then
  GFR_CMD="git-filter-repo"
else
  # Try git filter-repo as a Python module wrapper (older installs)
  if python -c "import importlib,sys
try:
  import importlib.util, subprocess
  importlib.util.find_spec('git_filter_repo')
  sys.exit(0)
except Exception:
  sys.exit(1)" 2>/dev/null; then
    GFR_CMD="git-filter-repo"
  else
    echo
    echo "git-filter-repo is not installed or not found."
    echo "Install options:"
    echo " - Homebrew (macOS): brew install git-filter-repo"
    echo " - pip: pip install git-filter-repo"
    echo " - See: https://github.com/newren/git-filter-repo"
    read -p "Install now with 'pip install git-filter-repo'? Type 'yes' to attempt installation, anything else to abort: " inst
    if [[ "${inst}" == "yes" ]]; then
      if command -v pip >/dev/null 2>&1; then
        pip install --user git-filter-repo || err "pip install failed. Install git-filter-repo manually and re-run."
        GFR_CMD="git-filter-repo"
      else
        err "pip is not available. Install git-filter-repo manually and re-run."
      fi
    else
      err "git-filter-repo is required. Aborting."
    fi
  fi
fi

echo
info "Creating backup mirror..."
if git clone --mirror "$REPO_URL" "$BACKUP_DIR"; then
  info "Backup mirror created at $BACKUP_DIR"
else
  err "Backup mirror clone failed. Aborting."
fi

echo
info "Creating rewrite mirror..."
if git clone --mirror "$REPO_URL" "$REWRITE_DIR"; then
  info "Rewrite mirror created at $REWRITE_DIR"
else
  err "Rewrite mirror clone failed. Aborting."
fi

cd "$REWRITE_DIR"

echo
info "Running git-filter-repo to remove specified paths..."
# Build args
GFR_ARGS=(--invert-paths)
for p in "${REMOVE_PATHS[@]}"; do
  GFR_ARGS+=(--path "$p")
done

# Run filter-repo
# shellcheck disable=SC2086
$GFR_CMD "${GFR_ARGS[@]}" || err "git-filter-repo failed."

info "git-filter-repo completed."

echo
info "Performing aggressive cleanup (reflog expire and git gc)..."
git reflog expire --expire=now --all || true
git gc --prune=now --aggressive || true

# Verification step (local)
echo
info "Scanning rewritten repo for any remaining references to the removed paths..."
set +e
FOUND=$(git rev-list --all --objects | grep -E 'rates.json|(^|/)dist/' || true)
set -e
if [[ -n "$FOUND" ]]; then
  echo
  echo "WARNING: Some object paths still reference the patterns (showing matches):"
  echo "$FOUND"
  echo
  echo "You should inspect the repository before pushing the rewritten refs. Aborting push."
  echo "If you want to proceed despite this, re-run the script and confirm push manually after inspection."
  exit 1
else
  info "No visible references to rates.json or dist/ found in object list."
fi

echo
echo "Ready to push rewritten history back to origin (this will force-update all branches and tags)."
read -p "Type 'force-push' to perform git push --force --all and git push --force --tags, anything else to abort: " pushconfirm
if [[ "${pushconfirm}" != "force-push" ]]; then
  echo "Push aborted. Rewritten repo is in: $(pwd)"
  echo "You can inspect it, and push later with:"
  echo "  git push --force --all"
  echo "  git push --force --tags"
  exit 0
fi

echo
info "Force-pushing all branches and tags to origin..."
git push --force --all origin || err "git push --force --all failed."
git push --force --tags origin || err "git push --force --tags failed."

info "Force-push complete."

echo
echo "Post-push verification (do a fresh clone separately to be certain)."
echo "Recommended: on a separate location, run these commands to validate:"
echo "  git clone $REPO_URL test-repo"
echo "  cd test-repo"
echo "  git log --all --name-only --pretty=format: | grep -E '(^dist/|rates.json)' && echo 'FOUND' || echo 'NOT FOUND'"

echo
echo "IMPORTANT NEXT STEPS:"
echo " - If rates.json contained any secrets, rotate/revoke them immediately."
echo " - Inform any collaborators to reclone the repository."
echo " - Any open PRs or forks based on the old history will be incompatible and likely must be recreated."
echo
echo "Backup mirror kept at: ../$BACKUP_DIR"
echo "Rewrite mirror used at: $(pwd)"
echo
echo "Done."
