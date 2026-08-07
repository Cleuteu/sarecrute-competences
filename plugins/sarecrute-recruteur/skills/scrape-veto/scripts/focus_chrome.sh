#!/bin/bash
# Ramène au premier plan l'onglet Chrome du scrape (macOS).
#
#   focus_chrome.sh [fragment_url_onglet]      # défaut : facebook.com/groups
#
# Pourquoi : quand la fenêtre Chrome est masquée ou minimisée, Chrome suspend
# requestAnimationFrame et bride les timers. Le fil Facebook cesse de charger
# (2-3 posts + skeletons, scrollHeight figé) sans aucun message d'erreur.
# Rendre l'onglet visible relance le rendu immédiatement — pas besoin de
# recharger la page dans la plupart des cas.
#
# Il ne suffit pas d'activer l'application : c'est l'onglet CIBLE qui doit être
# l'onglet actif de la fenêtre au premier plan, sinon il reste occulté et gelé.

set -euo pipefail

FRAGMENT="${1:-facebook.com/groups}"

FOUND=$(osascript <<EOF
tell application "Google Chrome"
  set found to false
  repeat with w in windows
    set i to 0
    repeat with t in tabs of w
      set i to i + 1
      if URL of t contains "$FRAGMENT" then
        set active tab index of w to i
        set index of w to 1
        set found to true
        exit repeat
      end if
    end repeat
    if found then exit repeat
  end repeat
  activate
  return found
end tell
EOF
)

if [ "$FOUND" != "true" ]; then
  echo "Aucun onglet Chrome ne correspond à : $FRAGMENT" >&2
  exit 1
fi

# Laisser le compositeur repartir avant de rendre la main au scrape.
sleep 1
echo "Onglet au premier plan (fragment : $FRAGMENT)"
