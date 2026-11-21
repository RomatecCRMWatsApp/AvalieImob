#!/usr/bin/env bash
# Teste de fumaça das calculadoras oficiais. Roda de DENTRO da rede privada (no Railway: a partir do backend).
# Uso: RR_URL=http://rtc-regime-regular:8080/api SN_URL=http://rtc-simples-nacional:8082/api ./smoke-test.sh
set -euo pipefail
RR_URL="${RR_URL:-http://localhost:8080/api}"
SN_URL="${SN_URL:-http://localhost:8082/api}"
DIR="$(cd "$(dirname "$0")" && pwd)"
falhas=0
ok()  { echo "OK    $1"; }
erro(){ echo "FALHA $1"; falhas=$((falhas+1)); }

code() { curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$@"; }

[ "$(code "$RR_URL/swagger-ui.html" -L)" = "200" ] && ok "regime regular: swagger" || erro "regime regular: swagger"
[ "$(code "$SN_URL/swagger-ui.html" -L)" = "200" ] && ok "simples nacional: swagger" || erro "simples nacional: swagger"
[ "$(code "$SN_URL/versao")" = "200" ] && ok "simples nacional: /versao" || erro "simples nacional: /versao"

# Cálculo oficial de exemplo (docs/exemplos.md do regime regular): 4 itens, o 4º com erro proposital REG-011.
resp="$(curl -s --max-time 30 -H 'Content-Type: application/json' \
  -d @"$DIR/fixtures/regime-regular-operacao-exemplo.json" \
  "$RR_URL/calculadora/observabilidade/regime-geral")"
if echo "$resp" | grep -q '"REG-011"' && echo "$resp" | grep -q '"vCBS"'; then
  ok "regime regular: cálculo de exemplo (itens calculados + REG-011 no item 4)"
else
  erro "regime regular: cálculo de exemplo"
fi

[ "$falhas" -eq 0 ] && echo "Tudo certo." || { echo "$falhas verificação(ões) falharam."; exit 1; }
