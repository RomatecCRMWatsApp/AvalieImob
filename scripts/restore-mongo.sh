#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Restauração de backup AvalieImob a partir do Cloudflare R2.
# Uso:
#   ./restore-mongo.sh avalieimob_20260608_030000.tar.gz "mongodb+srv://...DESTINO"
#
# Requer: rclone configurado (remote "R2") + mongorestore no PATH.
# Variáveis de ambiente esperadas (mesmas do workflow):
#   RCLONE_CONFIG_R2_TYPE=s3
#   RCLONE_CONFIG_R2_PROVIDER=Cloudflare
#   RCLONE_CONFIG_R2_ACCESS_KEY_ID, RCLONE_CONFIG_R2_SECRET_ACCESS_KEY, RCLONE_CONFIG_R2_ENDPOINT
#   R2_BUCKET=avalieimob-backups
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

FILE="${1:?Informe o nome do arquivo de backup (ex.: avalieimob_AAAAMMDD_HHMMSS.tar.gz)}"
TARGET_URI="${2:?Informe a MONGO_URI de destino}"
BUCKET="${R2_BUCKET:-avalieimob-backups}"
WORK="$(mktemp -d)"

echo "→ Baixando ${FILE} do R2"
rclone copyto "R2:${BUCKET}/${FILE}" "${WORK}/${FILE}" --retries 3

echo "→ Extraindo"
tar -xzf "${WORK}/${FILE}" -C "${WORK}"
DUMP_DIR="$(find "${WORK}" -maxdepth 1 -type d -name 'avalieimob_*' | head -n 1)"

echo "→ Restaurando para o destino (gzip)"
echo "  ATENÇÃO: --drop sobrescreve coleções existentes no destino."
read -r -p "  Confirmar restore com --drop? [s/N] " ok
if [[ "${ok,,}" != "s" ]]; then echo "Cancelado."; rm -rf "${WORK}"; exit 0; fi

mongorestore --uri="${TARGET_URI}" --gzip --drop "${DUMP_DIR}"

echo "→ Limpando temporários"
rm -rf "${WORK}"
echo "✅ Restore concluído a partir de ${FILE}"
