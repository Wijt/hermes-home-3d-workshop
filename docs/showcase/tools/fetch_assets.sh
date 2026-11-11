#!/usr/bin/env bash
# Fetches what the motion-graphics film needs and the repository does not carry:
#   media/fonts/   Bricolage Grotesque (SIL Open Font License 1.1), six static cuts
#   media/sounds/  marimba and hand percussion from the Versilian Community Sample Library (CC0)
#   media/grain/   a tile of faint noise for the dark ground (written here by tools/make_grain.py)
# Run it once from anywhere; it writes inside docs/showcase/media/ only.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p media/fonts
base="https://raw.githubusercontent.com/ateliertriay/bricolage/main"
for f in BricolageGrotesque96pt-ExtraBold BricolageGrotesque96pt-Bold BricolageGrotesque-Regular BricolageGrotesque-Medium BricolageGrotesque-SemiBold BricolageGrotesque-Bold; do
  [ -s "media/fonts/$f.ttf" ] || curl -fsSL -o "media/fonts/$f.ttf" "$base/fonts/ttf/$f.ttf"
done
[ -s media/fonts/OFL.txt ] || curl -fsSL -o media/fonts/OFL.txt "$base/OFL.txt"
for pack in vcsl/marimba vcsl/cajon vcsl/shaker-small vcsl/claps vcsl/woodblock; do
  [ -d "media/sounds/${pack/\//-}" ] || raea sounds get "$pack" >/dev/null
done
[ -s media/grain/grain.png ] || python3 -I tools/make_grain.py >/dev/null
echo "fonts: $(ls media/fonts/*.ttf | wc -l) files; sounds: $(ls -d media/sounds/*/ | wc -l) packs"
