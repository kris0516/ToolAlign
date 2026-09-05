#!/usr/bin/env bash
# First publication of the reviewed ToolAlign planning package only.
# Never changes an existing repository or uses force push.
set -euo pipefail

MODE="${1:---dry-run}"
if [[ "$#" -gt 1 || ( "$MODE" != "--dry-run" && "$MODE" != "--publish" ) ]]; then
  printf 'Usage: bash scripts/publish_plan_repo.sh [--dry-run|--publish]\n' >&2
  exit 2
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
OWNER="kris0516"
NAME="ToolAlign"
TARGET="$OWNER/$NAME"
URL="https://github.com/$TARGET"
cd "$ROOT"
command -v python3 >/dev/null || { echo 'Python 3 is required.' >&2; exit 2; }

python3 - "$ROOT" <<'CHECK'
import hashlib
import sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
manifest = root / 'MANIFEST.sha256'
if not manifest.is_file():
    raise SystemExit('Missing MANIFEST.sha256; no publication performed.')
expected = set()
for line in manifest.read_text(encoding='utf-8').splitlines():
    digest, sep, relative = line.partition('  ')
    if not sep or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise SystemExit('Malformed manifest; no publication performed.')
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts or relative in expected:
        raise SystemExit('Unsafe/duplicate manifest path; no publication performed.')
    path = root / rel
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise SystemExit(f'Symlink rejected: {relative}')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit(f'Manifest mismatch: {relative}; review before publication.')
    expected.add(relative)
for path in root.rglob('*'):
    rel = path.relative_to(root)
    if rel.parts[0] in {'.git', '.toolalign-local'}:
        continue
    if path.is_symlink():
        raise SystemExit(f'Unexpected symlink: {rel}')
    if path.is_file() and str(rel) not in expected | {'MANIFEST.sha256', '.DS_Store'}:
        raise SystemExit(f'Unexpected file: {rel}; nothing will be published.')
print(f'Manifest verified: {len(expected)} files. Model/data artifacts are not part of this package.')
CHECK

if [[ "$MODE" == "--dry-run" ]]; then
  printf 'DRY RUN ONLY. No GitHub repository, commit, or push has been created.\n'
  printf 'Authorized target for explicit publication: %s (public).\n' "$TARGET"
  printf 'Next on the owner’s authenticated Mac: bash scripts/publish_plan_repo.sh --publish\n'
  exit 0
fi

for executable in git gh; do
  command -v "$executable" >/dev/null || {
    printf 'Missing %s. Install/authenticate it locally; never paste tokens into chat.\n' "$executable" >&2
    exit 2
  }
done
if [[ -e "$ROOT/.git" ]]; then
  echo 'A local Git repository already exists. Stop and inspect; this script is first-publication only.' >&2
  exit 2
fi
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo 'This folder is inside another Git repository. Move the clean planning package outside it.' >&2
  exit 2
fi
gh auth status >/dev/null
LOGIN="$(gh api user --jq '.login')"
if [[ "$LOGIN" != "$OWNER" ]]; then
  printf 'Authenticated account is not %s. No repository was created.\n' "$OWNER" >&2
  exit 2
fi
if ! git config --get user.name >/dev/null || ! git config --get user.email >/dev/null; then
  echo 'Configure your real Git author name/email locally before publication. No repository was created.' >&2
  exit 2
fi

trap 'rc=$?; echo "Publication stopped. Inspect local/remote state; never delete a repository or force-push to recover." >&2; exit "$rc"' ERR

git init -b main
git add -- .
git commit -m 'docs: bootstrap ToolAlign planning baseline'
# GitHub rejects an existing name; do not reuse it or change its visibility.
gh repo create "$TARGET" --public \
  --description 'Reliable tool-use post-training and evaluation on Apple Silicon. Planning baseline.'
git remote add origin "$URL.git"
# Per-command credential helper; no global Git config or token printing.
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' \
  push --set-upstream origin main
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(gh api "repos/$TARGET/git/ref/heads/main" --jq '.object.sha')"
IS_PRIVATE="$(gh api "repos/$TARGET" --jq '.private')"
DEFAULT_BRANCH="$(gh api "repos/$TARGET" --jq '.default_branch')"
README_SHA="$(gh api "repos/$TARGET/contents/README.md?ref=main" --jq '.sha')"
LOCAL_README_SHA="$(git hash-object README.md)"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" || "$IS_PRIVATE" != 'false' || "$DEFAULT_BRANCH" != 'main' || "$README_SHA" != "$LOCAL_README_SHA" ]]; then
  echo 'Remote verification failed; do not report publication as complete.' >&2
  exit 3
fi
mkdir -p .toolalign-local
python3 - "$URL" "$LOCAL_SHA" <<'RECEIPT'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
Path('.toolalign-local/publish-receipt.json').write_text(json.dumps({
    'repository_url': sys.argv[1],
    'commit': sys.argv[2],
    'visibility': 'public',
    'verified_at': datetime.now(timezone.utc).isoformat(),
    'scope': 'planning-package-only'
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
RECEIPT
printf 'VERIFIED PUBLIC REPOSITORY: %s\nCOMMIT: %s\n' "$URL" "$LOCAL_SHA"
printf 'Supervisor: update coordination/PROJECT_STATUS.md in a new commit, then claim P00.\n'
