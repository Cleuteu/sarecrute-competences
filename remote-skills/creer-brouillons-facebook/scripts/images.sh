#!/bin/bash
# Prépare les visuels des brouillons Facebook pour file_upload, en un seul appel pour tout le run.
#
#   bash images.sh <dossier_de_travail_de_la_session> <<'EOF'
#   <idDrive>	<nom du fichier dans Drive>	<taille en octets>
#   EOF
#
#   bash images.sh --depuis-txt <dossier_des_txt> <dossier_de_travail_de_la_session> <<'EOF'
#   <idDrive>	<nom du fichier dans Drive>	<taille en octets>
#   EOF
#
# Entrée : une ligne par image distincte, champs séparés par une tabulation (la taille peut
# être vide). Sortie : une ligne par image, champs séparés par une tabulation :
#
#   <idDrive>	<statut>	<taille>	<chemin à passer à file_upload>
#
#   OK           chemin prêt pour file_upload
#   ABSENT       aucun fichier de ce nom dans le Drive synchronisé (ou aucun .txt pour cet id)
#   TAILLE       fichier trouvé mais incomplet (Drive en mode flux qui n'a pas fini) : ne pas
#                l'envoyer, la publication part sans image
#   HORS_SESSION aucun dossier où copier que file_upload accepte : en Claude Code, le dossier de
#                travail est lui-même dans un Drive (la copie y serait synchronisée chez tous) ;
#                en Cowork, aucun dossier connecté à la tâche hors Drive
#
# Pourquoi une copie : file_upload n'accepte que les fichiers que la session a le droit de lire.
# En Claude Code, c'est son dossier de travail et les dossiers ajoutés — vérifié le 01/11/2026 sous
# Windows : G:\Drive partagés\...\Publications, %TEMP% et le scratchpad sont refusés (« only files
# this session is allowed to read can be uploaded »), le dossier de travail est accepté. On copie
# donc chaque visuel dans <dossier_de_travail>/.sarecrute-images/, vidé à chaque run.
#
# En Cowork (/mnt/user-data présent), ce sont les dossiers connectés à la tâche ; outputs, uploads
# et working sont la sandbox, refusée depuis octobre 2026. Un visuel trouvé dans un dossier
# connecté (le Drive partagé) est rendu tel quel, sans copie. Un visuel décodé (--depuis-txt) est
# écrit dans le premier dossier connecté qui n'est pas un Drive, pour la même raison qu'en Claude
# Code : c'est un dossier que file_upload accepte.
#
# Le nom de la copie est l'id Drive (ASCII, unique) et son extension suit le CONTENU, pas le nom :
# un .jfif est un JPEG, mais file_upload l'annonce application/octet-stream, que Facebook refuse.

set -u

MODE=drive
if [ "${1:-}" = "--depuis-txt" ]; then
  MODE=txt
  TXT_DIR="${2:?usage : images.sh --depuis-txt <dossier_des_txt> <dossier_de_travail>}"
  shift 2
fi
WORK="${1:?usage : images.sh <dossier_de_travail_de_la_session>}"

# SARECRUTE_USER_DATA ne sert qu'aux tests (tests/images_sh.test.sh simule une tâche Cowork).
USER_DATA="${SARECRUTE_USER_DATA:-/mnt/user-data}"
COWORK=0
[ -d "$USER_DATA" ] && COWORK=1

# Chemin tel que file_upload l'attend : natif Windows sous Git Bash, inchangé ailleurs. Forme
# longue (-l) : Claude Code refuse un nom court 8.3 comme UTILIS~1 (« suspicious path spelling »).
natif() { if command -v cygpath >/dev/null 2>&1; then cygpath -w -l "$1"; else printf '%s\n' "$1"; fi; }

# Le dossier de travail en chemin POSIX, pour y écrire depuis bash.
if command -v cygpath >/dev/null 2>&1; then WORK="$(cygpath -u "$WORK")"; fi

taille() { wc -c < "$1" | tr -d ' '; }

# Décodeur base64 : -d partout, sauf les macOS d'avant 13 qui n'acceptent que -D. Choisi une fois
# à l'avance — un repli « -d || -D » dans le tube trouverait l'entrée déjà consommée.
if printf 'QQ==' | base64 -d >/dev/null 2>&1; then B64D="-d"; else B64D="-D"; fi

# Extension d'après les premiers octets du fichier.
extension() {
  local h
  h="$(head -c 12 "$1" | od -An -tx1 | tr -d ' \n')"
  case "$h" in
    89504e47*) echo png ;;
    ffd8ff*) echo jpg ;;
    47494638*) echo gif ;;
    52494646????????57454250*) echo webp ;;
    *) local e="${2##*.}"; echo "$e" | tr '[:upper:]' '[:lower:]' ;;
  esac
}

# Nom du dossier des Drive partagés : il suit la langue du système de la recruteuse (« Unidades
# compartidas » sur un poste en espagnol), pas celle du Drive.
PARTAGES=("Drive partagés" "Shared drives" "Unidades compartidas" "Geteilte Ablagen"
          "Drive condivisi" "Drives partilhados" "Drives compartilhados" "Gedeelde drives")

# Racines possibles du Drive partagé synchronisé, sans chemin présumé juste. Sous Git Bash, les
# lecteurs /c, /g… sont des montages virtuels : un motif /[a-z]/ ne les énumère PAS (c'est ce qui
# faisait échouer la 0.3.0 sous Windows) — on les teste donc un par un.
racines() {
  [ "$COWORK" = 1 ] && echo "$USER_DATA"
  local d s
  for d in "$HOME"/Library/CloudStorage/GoogleDrive-* \
           /a /b /c /d /e /f /g /h /i /j /k /l /m /n /o /p /q /r /s /t /u /v /w /x /y /z \
           "$HOME"/"Google Drive"*; do
    for s in "${PARTAGES[@]}"; do [ -d "$d/$s" ] && echo "$d/$s"; done
  done
}

# Échappe les métacaractères de find -name ([ ] * ? \) d'un nom de fichier.
motif() { printf '%s' "$1" | sed 's/[][*?\\]/\\&/g'; }

trouver() {
  local nom="$1" r p
  while IFS= read -r r; do
    for p in "$r/Sarecrute/Publications/$nom" "$r/Publications/$nom"; do
      [ -f "$p" ] && { echo "$p"; return; }
    done
  done <<< "$RACINES"
  # outputs et working (sandbox Cowork) sont exclus : file_upload y refuse tout.
  while IFS= read -r r; do
    [ -n "$r" ] || continue
    p="$(find "$r" -maxdepth 6 \( -path "$USER_DATA/outputs" -o -path "$USER_DATA/working" \) -prune \
           -o -type f -name "$(motif "$nom")" -print 2>/dev/null | head -1)"
    [ -n "$p" ] && { echo "$p"; return; }
  done <<< "$RACINES"
}

# Cowork : premier dossier connecté à la tâche, accessible en écriture, qui n'est pas un Drive
# (un dossier qui contient « Publications » l'est : on n'y écrit jamais, la copie serait
# synchronisée dans le Drive partagé, chez toutes les recruteuses).
relais_cowork() {
  local d
  for d in "$USER_DATA"/*/; do
    d="${d%/}"
    case "${d##*/}" in outputs|uploads|working) continue ;; esac
    [ -w "$d" ] || continue
    [ -n "$(find "$d" -maxdepth 2 -type d -name Publications 2>/dev/null | head -1)" ] && continue
    echo "$d"; return
  done
}

dans_un_drive() {
  case "$1" in
    */"Drive partagés"*|*/"Shared drives"*|*/GoogleDrive-*|*/"Google Drive"*|*/"My Drive"*|*/"Mon Drive"*) return 0 ;;
  esac
  return 1
}

if [ "$COWORK" = 1 ]; then
  r="$(relais_cowork)"
  OUT="${r:+$r/.sarecrute-images}"
elif dans_un_drive "$WORK"; then
  OUT=""
else
  OUT="$WORK/.sarecrute-images"
fi
# En Cowork, le relais ne sert qu'aux visuels décodés : on n'y touche pas en mode Drive.
if [ -n "$OUT" ] && { [ "$COWORK" = 0 ] || [ "$MODE" = txt ]; }; then
  mkdir -p "$OUT" && rm -f "$OUT"/* 2>/dev/null
fi

[ "$MODE" = drive ] && RACINES="$(racines)"

while IFS=$'\t' read -r id nom attendu || [ -n "${id:-}" ]; do
  id="${id%$'\r'}"; nom="${nom%$'\r'}"; attendu="${attendu%$'\r'}"
  [ -n "$id" ] || continue

  if [ "$MODE" = txt ]; then
    # Résultat de download_file_content sauvegardé par l'application : du JSON avec "id" et
    # "content" (base64). Ni python ni jq : python3 est un alias factice du Microsoft Store
    # sur les postes Windows.
    src=""
    for f in "$TXT_DIR"/*download_file_content*.txt; do
      [ -f "$f" ] || continue
      grep -q "\"id\" *: *\"$id\"" "$f" && { src="$f"; break; }
    done
    if [ -z "$src" ]; then printf '%s\tABSENT\t\t\n' "$id"; continue; fi
    if [ -z "$OUT" ]; then printf '%s\tHORS_SESSION\t\t\n' "$id"; continue; fi
    tmp="$OUT/$id.bin"
    grep -o '"content" *: *"[^"]*"' "$src" | head -1 | sed 's/^"content" *: *"//; s/"$//; s#\\/#/#g' \
      | base64 "$B64D" > "$tmp"
    n="$(taille "$tmp")"
    if [ -n "$attendu" ] && [ "$n" != "$attendu" ]; then
      rm -f "$tmp"; printf '%s\tTAILLE\t%s\t\n' "$id" "$n"; continue
    fi
    dst="$OUT/$id.$(extension "$tmp" "$nom")"
    mv -f "$tmp" "$dst"
    printf '%s\tOK\t%s\t%s\n' "$id" "$n" "$(natif "$dst")"
    continue
  fi

  src="$(trouver "$nom")"
  if [ -z "$src" ]; then printf '%s\tABSENT\t\t\n' "$id"; continue; fi

  # Lecture complète : un fichier en mode flux n'est qu'un espace réservé tant qu'on ne l'a pas lu.
  case "$src" in "$WORK"/*) dedans=1 ;; *) dedans=0 ;; esac
  if [ "$COWORK" = 1 ] || [ "$dedans" = 1 ]; then
    cat "$src" > /dev/null 2>&1
    n="$(taille "$src")"; dst="$src"
  elif [ -z "$OUT" ]; then
    printf '%s\tHORS_SESSION\t\t\n' "$id"; continue
  else
    dst="$OUT/$id.$(extension "$src" "$nom")"
    cat "$src" > "$dst" 2>/dev/null
    n="$(taille "$dst")"
    if [ -n "$attendu" ] && [ "$n" != "$attendu" ]; then
      sleep 3; cat "$src" > "$dst" 2>/dev/null; n="$(taille "$dst")"
    fi
  fi
  if [ -n "$attendu" ] && [ "$n" != "$attendu" ]; then
    [ "$dst" != "$src" ] && rm -f "$dst"
    printf '%s\tTAILLE\t%s\t\n' "$id" "$n"; continue
  fi
  printf '%s\tOK\t%s\t%s\n' "$id" "$n" "$(natif "$dst")"
done
