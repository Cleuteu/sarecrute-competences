#!/bin/bash
# Épingle le script de préparation des visuels de `creer-brouillons-facebook` (scripts/images.sh).
#
# Bugs d'origine, tous silencieux :
# - 0.3.0 cherchait le Drive par `for root in /[a-z]/"Drive partagés"` : sous Git Bash, les
#   lecteurs /c, /g… ne sont pas énumérés par ce motif. Rien n'était trouvé, sur tous les postes
#   Windows, et le run basculait sur un repli python3 absent sous Windows.
# - file_upload refuse tout fichier hors du dossier de travail de la session (« only files this
#   session is allowed to read ») : le chemin du Drive, %TEMP% et le scratchpad sont refusés.
#   La recruteuse lisait « l'outil d'upload refuse » et rapportait « Facebook refuse le dépôt ».
# - un .jfif part en application/octet-stream (type déduit du nom), que Facebook refuse.
#
#   bash tests/images_sh.test.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/remote-skills/creer-brouillons-facebook/scripts/images.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
ko=0
ok() { if [ "$2" = "$3" ]; then echo "  ok   $1"; else ko=$((ko+1)); echo "  KO   $1"; echo "       attendu: $3"; echo "       obtenu:  $2"; fi; }

# Un faux Drive synchronisé, sous un HOME de test (racine « ~/Google Drive* » du script).
PUB="$T/home/Google Drive/Drive partagés/Sarecrute/Publications"
mkdir -p "$PUB" "$T/travail"
printf '\x89PNG\r\n\x1a\n0123456789' > "$PUB/visuel test l'été.png"
printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01xyz' > "$PUB/zz test paco.jfif"
printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01' > "$PUB/zz test [crochets].jpg"

lancer() { HOME="$T/home" bash "$SCRIPT" "$@"; }

echo
echo "Drive synchronisé : copie dans le dossier de travail, extension d'après le contenu"
out="$(printf 'ID1\tvisuel test l'"'"'été.png\t18\r\nID2\tzz test paco.jfif\t15\nID3\tzz test [crochets].jpg\t12\nID4\tinexistant zz.png\t5\nID5\tvisuel test l'"'"'été.png\t999\n' | lancer "$T/travail")"
ligne() { printf '%s\n' "$out" | grep "^$1"$'\t' | cut -f"$2"; }
ok "png trouvé (apostrophe, accent, fin de ligne CRLF)" "$(ligne ID1 2)" "OK"
ok "copie dans .sarecrute-images du dossier de travail" "$(ligne ID1 4 | sed 's#\\#/#g; s#.*/\.sarecrute-images/##')" "ID1.png"
ok "jfif copié en .jpg"                    "$(ligne ID2 4 | sed 's#.*\.##')" "jpg"
ok "crochets dans le nom (motif find échappé)" "$(ligne ID3 2)" "OK"
ok "fichier absent"                         "$(ligne ID4 2)" "ABSENT"
ok "taille différente de fileSize"          "$(ligne ID5 2)" "TAILLE"
ok "aucune copie laissée pour un TAILLE"     "$(ls "$T/travail/.sarecrute-images" | sort | tr '\n' ' ')" "ID1.png ID2.jpg ID3.jpg "

echo
echo "Poste en espagnol : le dossier des Drive partagés s'appelle « Unidades compartidas »"
PUB_ES="$T/home/Google Drive/Unidades compartidas/Sarecrute/Publications"
mkdir -p "$PUB_ES"
printf '\x89PNG\r\n\x1a\nes' > "$PUB_ES/zz visuel espagnol.png"
out="$(printf 'IDES\tzz visuel espagnol.png\t10\n' | lancer "$T/travail")"
ok "trouvé sous Unidades compartidas"        "$(ligne IDES 2)" "OK"

echo
echo "Dossier de travail dans un Drive : on n'y écrit rien"
out="$(printf 'ID1\tvisuel test l'"'"'été.png\t18\n' | lancer "$T/home/Google Drive/Drive partagés/Autre")"
ok "HORS_SESSION"                           "$(ligne ID1 2)" "HORS_SESSION"

echo
echo "Repli : décodage des .txt du connecteur Drive, sans python ni jq"
mkdir -p "$T/txt"
b64="$(printf '\x89PNG\r\n\x1a\nabc/def' | base64 | tr -d '\n' | sed 's#/#\\/#g')"
printf '{"content":"%s","id":"IDX","mimeType":"image/png","title":"x.png"}' "$b64" > "$T/txt/mcp-abc-download_file_content-1.txt"
printf '{"content":"AAAA","id":"AUTRE","title":"y.png"}' > "$T/txt/mcp-abc-download_file_content-2.txt"
out="$(printf 'IDX\tx.png\t15\nIDZ\tz.png\t\n' | lancer --depuis-txt "$T/txt" "$T/travail")"
ok "décodé et mappé par id"                 "$(ligne IDX 2)" "OK"
ok "décodé à l'octet près (\\/ du JSON compris)" "$(cmp -s "$T/travail/.sarecrute-images/IDX.png" <(printf '\x89PNG\r\n\x1a\nabc/def'); echo $?)" "0"
ok "id sans .txt"                           "$(ligne IDZ 2)" "ABSENT"

echo
echo "Cowork : /mnt/user-data simulé (SARECRUTE_USER_DATA)"
cowork() { local ud="$1"; shift; HOME="$T/home" SARECRUTE_USER_DATA="$ud" bash "$SCRIPT" "$@"; }
# Sous Git Bash le script rend des chemins Windows (cygpath) ; dans le Linux de Cowork, tels quels.
chemin() { if command -v cygpath >/dev/null 2>&1; then cygpath -w -l "$1"; else printf '%s\n' "$1"; fi; }
UD="$T/cowork-drive"; mkdir -p "$UD/outputs" "$UD/uploads" "$UD/Sarecrute/Publications"
printf '\x89PNG\r\n\x1a\ncw' > "$UD/Sarecrute/Publications/zz cowork.png"
cp "$UD/Sarecrute/Publications/zz cowork.png" "$UD/outputs/zz cowork.png"
out="$(printf 'IDC\tzz cowork.png\t10\n' | cowork "$UD" ignore)"
ok "Drive connecté : chemin rendu tel quel"    "$(ligne IDC 4)" "$(chemin "$UD/Sarecrute/Publications/zz cowork.png")"
ok "rien écrit dans le Drive connecté"          "$(ls -A "$UD/Sarecrute" | tr '\n' ' ')" "Publications "
mkdir -p "$T/cw-out-seul/outputs"; cp "$UD/outputs/zz cowork.png" "$T/cw-out-seul/outputs/"
out="$(printf 'IDC\tzz cowork.png\t10\n' | cowork "$T/cw-out-seul" ignore)"
ok "un fichier dans outputs seul est ignoré"    "$(ligne IDC 2)" "ABSENT"
UD2="$T/cowork-bureau"; mkdir -p "$UD2/outputs" "$UD2/uploads" "$UD2/Bureau Sarecrute"
out="$(printf 'IDX\tx.png\t15\n' | cowork "$UD2" --depuis-txt "$T/txt" ignore)"
ok "décodé dans le dossier connecté, pas la sandbox" "$(ligne IDX 4)" "$(chemin "$UD2/Bureau Sarecrute/.sarecrute-images/IDX.png")"
UD3="$T/cowork-sans-dossier"; mkdir -p "$UD3/outputs" "$UD3/uploads"
out="$(printf 'IDX\tx.png\t15\n' | cowork "$UD3" --depuis-txt "$T/txt" ignore)"
ok "aucun dossier connecté : HORS_SESSION"       "$(ligne IDX 2)" "HORS_SESSION"

echo
echo "Fins de ligne du script lui-même (git clone sous Windows, core.autocrlf=true)"
ok "images.sh indexé sans CR"               "$(git -C "$ROOT" cat-file -p :remote-skills/creer-brouillons-facebook/scripts/images.sh | tr -cd '\r' | wc -c | tr -d ' ')" "0"
ok ".gitattributes impose LF aux .sh"       "$(git -C "$ROOT" check-attr eol -- remote-skills/creer-brouillons-facebook/scripts/images.sh | sed 's/.*: //')" "lf"

echo
[ "$ko" = 0 ] && echo "OK — tout passe" || { echo "$ko échec(s)"; exit 1; }
