#!/usr/bin/env bash
# One command: the state of every repo in the registry.
#
#   ops/status_all.sh               uses hq.yaml in this headquarters
#   ops/status_all.sh --root DIR    uses DIR/hq.yaml instead
#
# Read-only. For each registered repo it shows the branch, whether there are
# uncommitted changes, the date of the latest commit, and whether pushing main
# deploys to production. A dirty repo is normal when someone is working in it;
# it is a signal, not an error. A registered repo that is missing or is not a
# git repository is an error, and the script exits with status 1.

set -euo pipefail

# Inside a git hook these point at the hook's repository; ignore them so each
# git command reads only the folder it is given.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_PREFIX
export GIT_OPTIONAL_LOCKS=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_ARGS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --root)
      if [ "$#" -lt 2 ]; then
        echo "Usage: ops/status_all.sh [--root HEADQUARTERS_FOLDER]" >&2
        exit 2
      fi
      ROOT_ARGS=(--root "$2")
      shift 2
      ;;
    -h|--help)
      sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: ops/status_all.sh [--root HEADQUARTERS_FOLDER]" >&2
      exit 2
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (it reads hq.yaml)." >&2
  exit 2
fi

if ! REPO_LINES="$(python3 "$SCRIPT_DIR/hqlib.py" repos ${ROOT_ARGS[@]+"${ROOT_ARGS[@]}"})"; then
  exit 2
fi

if [ -z "$REPO_LINES" ]; then
  echo "No repos are registered in hq.yaml yet. Ask your agent to 'Set up my headquarters'."
  exit 0
fi

problems=0
fmt="%-22s %-16s %-9s %-11s %-15s %s\n"
printf "$fmt" "REPO" "BRANCH" "STATE" "LAST COMMIT" "RELEASE" "FOLDER"
printf "$fmt" "----" "------" "-----" "-----------" "-------" "------"

while IFS="$(printf '\t')" read -r name path release; do
  [ -z "$name" ] && continue
  case "$release" in
    main-deploys) release_label="main=prod" ;;
    no-auto-deploy) release_label="manual" ;;
    *) release_label="not recorded" ;;
  esac
  if [ ! -d "$path" ]; then
    printf "$fmt" "$name" "-" "MISSING" "-" "$release_label" "$path"
    problems=$((problems + 1))
    continue
  fi
  top="$(git -C "$path" rev-parse --show-toplevel 2>/dev/null || true)"
  real="$(cd "$path" && pwd -P)"
  if [ -z "$top" ] || [ "$(cd "$top" && pwd -P)" != "$real" ]; then
    printf "$fmt" "$name" "-" "NOT-GIT" "-" "$release_label" "$path"
    problems=$((problems + 1))
    continue
  fi
  branch="$(git -C "$path" symbolic-ref --short -q HEAD 2>/dev/null || true)"
  [ -z "$branch" ] && branch="(detached)"
  changes="$(git -C "$path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$changes" = "0" ]; then
    state="clean"
  else
    state="dirty:$changes"
  fi
  last="$(git -C "$path" log -1 --format=%cd --date=short 2>/dev/null || true)"
  [ -z "$last" ] && last="none"
  printf "$fmt" "$name" "$branch" "$state" "$last" "$release_label" "$path"
done <<EOF
$REPO_LINES
EOF

if [ "$problems" -gt 0 ]; then
  echo ""
  echo "$problems registered repo(s) are missing or are not git repositories."
  echo "Fix the path in hq.yaml, clone the repo, or remove the entry."
  exit 1
fi
