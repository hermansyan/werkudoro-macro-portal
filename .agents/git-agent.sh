#!/usr/bin/env bash
# git-agent.sh — Tool untuk mengeksekusi git commit dengan identitas agent resmi synt-wrkdr-1

set -euo pipefail

ACTION="${1:-help}"

case "$ACTION" in
  commit)
    AGENT_ROLE="${2:-}"
    COMMIT_MSG="${3:-}"

    if [ -z "$AGENT_ROLE" ] || [ -z "$COMMIT_MSG" ]; then
      echo "Penggunaan: $0 commit <AGENT_ID> \"<Commit Message>\""
      echo "Contoh: $0 commit FRONTEND-synt-wrkdr-1 \"Refactor mobile navigation dock\""
      exit 1
    fi

    # Format email standar agent
    AGENT_NAME="$AGENT_ROLE"
    AGENT_EMAIL="$(echo "$AGENT_ROLE" | tr '[:upper:]' '[:lower:]')@hermes.local"

    echo "Executing commit as $AGENT_NAME <$AGENT_EMAIL>..."
    git -c user.name="$AGENT_NAME" -c user.email="$AGENT_EMAIL" commit -m "[$AGENT_ROLE] $COMMIT_MSG"
    ;;

  list)
    echo "Daftar Agent Terdaftar di synt-wrkdr-1:"
    echo "- CEO-synt-wrkdr-1      <ceo.synt-wrkdr-1@hermes.local>"
    echo "- CPO-synt-wrkdr-1      <cpo.synt-wrkdr-1@hermes.local>"
    echo "- MACRO-synt-wrkdr-1    <macro.synt-wrkdr-1@hermes.local>"
    echo "- CTO-synt-wrkdr-1      <cto.synt-wrkdr-1@hermes.local>"
    echo "- FRONTEND-synt-wrkdr-1 <frontend.synt-wrkdr-1@hermes.local>"
    echo "- BACKEND-synt-wrkdr-1  <backend.synt-wrkdr-1@hermes.local>"
    echo "- QA-synt-wrkdr-1       <qa.synt-wrkdr-1@hermes.local>"
    echo "- DEVOPS-synt-wrkdr-1   <devops.synt-wrkdr-1@hermes.local>"
    ;;

  *)
    echo "Werkudoro Multi-Agent Git Helper (synt-wrkdr-1)"
    echo "Perintah:"
    echo "  $0 list                                            # Lihat daftar agent"
    echo "  $0 commit <AGENT_ID> \"<Commit Message>\"             # Commit dengan author agent spesifik"
    ;;
esac
