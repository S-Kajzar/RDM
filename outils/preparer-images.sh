#!/usr/bin/env bash
# Prépare les images intégrées dans la page (ImageMagick 6 requis).
#   - src/images/originaux/*.png : figures d'origine (fond blanc, sans transparence)
#   - src/images/*.png           : versions quantifiées (PNG 8 bits) intégrées en data URI
#   - src/images/accueil.png     : montage d'illustration de la page d'accueil
# Usage : bash outils/preparer-images.sh   (depuis la racine du dépôt)
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=src/images/originaux
OUT=src/images

for f in "$SRC"/*.png; do
  b=$(basename "$f")
  convert "$f" -strip -colors 256 "PNG8:$OUT/$b"
done

# Montage d'accueil : traction-compression à gauche, cisaillement à droite
convert -size 1120x620 xc:white \
  \( "$SRC/t1-siege-fil.png" -resize 500x255 \) -gravity northwest -geometry +20+62 -composite \
  \( "$SRC/t3-tube.png" -resize 500x270 \) -gravity northwest -geometry +80+335 -composite \
  \( "$SRC/c2-pince.png" -resize 500x255 \) -gravity northwest -geometry +590+62 -composite \
  \( "$SRC/c7-axe-chape.png" -resize 510x255 \) -gravity northwest -geometry +590+350 -composite \
  -fill '#1C2530' -stroke none -draw 'rectangle 559,20 561,600' \
  -fill '#F2B705' -draw 'rectangle 20,14 330,46' -draw 'rectangle 590,14 760,46' \
  -font DejaVu-Sans-Bold -pointsize 21 -fill '#1C2530' -gravity northwest \
  -annotate +30+18 'Traction et compression' -annotate +600+18 'Cisaillement' \
  -strip -colors 256 "PNG8:$OUT/accueil.png"

ls -l "$OUT"/*.png
