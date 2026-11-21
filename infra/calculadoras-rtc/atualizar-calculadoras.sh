#!/usr/bin/env bash
# Reconstrói as imagens das calculadoras na versão FIXADA em VERSOES.env.
# Para mudar de versão: edite VERSOES.env (tag + commit), rode este script e o smoke-test.sh.
# Nunca aponta para "main". O Dockerfile confere se o commit clonado é o esperado.
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./VERSOES.env; set +a
for S in regime-regular simples-nacional; do
  docker build -f Dockerfile.java -t "rtc-$S:local" \
    --build-arg SERVICE="$S" \
    --build-arg RTC_REGIME_REGULAR_TAG --build-arg RTC_REGIME_REGULAR_SHA \
    --build-arg RTC_SIMPLES_TAG --build-arg RTC_SIMPLES_SHA .
done
echo "Imagens prontas. Rode: docker compose --env-file VERSOES.env up -d"
