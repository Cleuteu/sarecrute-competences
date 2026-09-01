#!/bin/bash
# Empêche l'écran du Mac de s'éteindre pendant la collecte (macOS).
#
#   keep_awake.sh start [minutes]   # réveille l'écran + le maintient allumé (défaut : 90 min)
#   keep_awake.sh stop              # rend la main à la gestion d'énergie normale
#
# Pourquoi : Chrome suspend requestAnimationFrame dès que la page n'est plus
# rendue — et l'écran ÉTEINT produit cet effet même quand la fenêtre Chrome est
# au premier plan et détient le focus. Le fil Facebook se fige alors sur 2-4
# posts, sans erreur, et focus_chrome.sh n'y change rien : ce n'est pas Chrome
# qui est masqué, c'est l'écran qui ne peint plus.
#
# La signature du cas est reconnaissable dans __alive() : visibility "hidden"
# ALORS QUE focused vaut true. À vérifier avec :
#     pmset -g log | grep "Display is turned"
#
# On le lance donc en PRÉVENTIF, avant la collecte : le délai d'extinction est
# souvent de quelques minutes, donc le gel est quasi certain dès que l'utilisateur
# quitte son clavier. Le curatif coûterait un diagnostic, un rechargement de page
# et une ré-injection des helpers à chaque fois.
#
# Windows : pas d'équivalent bundlé. Si le rendu gèle avec focused:true, demander
# à l'utilisateur de désactiver la mise en veille de l'écran le temps du scrape.

set -euo pipefail

PIDFILE="${TMPDIR:-/tmp}/scrape_veto_caffeinate.pid"
MODE="${1:-start}"

stop_existing() {
  if [ -f "$PIDFILE" ]; then
    local pid
    pid=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "caffeinate arrêté (pid $pid)"
    fi
    rm -f "$PIDFILE"
  fi
}

case "$MODE" in
  start)
    MINUTES="${2:-90}"
    stop_existing
    # -u : signale une activité utilisateur -> rallume l'écran s'il est déjà éteint.
    caffeinate -u -t 2
    # -d : empêche l'extinction de l'écran ; -i : empêche la veille système.
    # -t borne la durée : si le scrape est interrompu, la machine reprend son
    # comportement normal sans intervention.
    nohup caffeinate -d -i -t $((MINUTES * 60)) >/dev/null 2>&1 &
    echo $! > "$PIDFILE"
    echo "Écran maintenu allumé ${MINUTES} min (pid $(cat "$PIDFILE"))"
    ;;
  stop)
    stop_existing
    ;;
  *)
    echo "usage: keep_awake.sh [start [minutes] | stop]" >&2
    exit 2
    ;;
esac
