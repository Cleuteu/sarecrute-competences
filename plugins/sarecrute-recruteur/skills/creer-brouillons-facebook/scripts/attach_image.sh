#!/bin/bash
# Joint une image au composeur Facebook déjà ouvert, par le presse-papiers macOS.
#
#   attach_image.sh <fragment_url_onglet> <chemin_image>
#
# Le composeur doit être ouvert ET le curseur déjà placé dans la zone de texte
# (le script ne fait que coller). Prérequis système : Claude.app autorisé dans
# Réglages Système > Confidentialité et sécurité > Accessibilité.

set -euo pipefail

FRAGMENT="${1:?usage: attach_image.sh <fragment_url_onglet> <chemin_image>}"
IMAGE="${2:?usage: attach_image.sh <fragment_url_onglet> <chemin_image>}"

[ -f "$IMAGE" ] || { echo "Image introuvable : $IMAGE" >&2; exit 1; }

# Le presse-papiers macOS veut du PNG : on convertit systématiquement (sips est natif).
TMP_PNG="$(mktemp -t fbpub).png"
trap 'rm -f "$TMP_PNG"' EXIT
sips -s format png "$IMAGE" --out "$TMP_PNG" >/dev/null

osascript -e "set the clipboard to (read (POSIX file \"$TMP_PNG\") as «class PNGf»)"

# Mettre l'onglet cible au premier plan : sans ça, le collage part ailleurs.
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

[ "$FOUND" = "true" ] || { echo "Aucun onglet Chrome ne correspond à : $FRAGMENT" >&2; exit 1; }

sleep 1
if ! osascript -e 'tell application "System Events" to keystroke "v" using command down' 2>/tmp/fbpub_keystroke.err; then
  if grep -q "1002" /tmp/fbpub_keystroke.err; then
    echo "Accessibilité refusée. Autorise Claude.app dans Réglages Système > Confidentialité et sécurité > Accessibilité, puis relance." >&2
  else
    cat /tmp/fbpub_keystroke.err >&2
  fi
  exit 2
fi

# Facebook met quelques secondes à téléverser et afficher la vignette.
sleep 4
echo "Collé dans l'onglet contenant : $FRAGMENT"
