# @module scripts/generate-keystore — Gera keystore para assinar APK/AAB Play Store
# NÃO execute este script diretamente — use como referência para criar o keystore localmente
# O keystore NUNCA deve ser commitado no GitHub

# Comando para gerar keystore:
# keytool -genkey -v \
#   -keystore romatec-avalieimob.keystore \
#   -alias romatec \
#   -keyalg RSA \
#   -keysize 2048 \
#   -validity 10000 \
#   -dname "CN=Romatec Consultoria Imobiliaria, OU=Tecnologia, O=J R P Bezerra Ltda, L=Acailandia, ST=Maranhao, C=BR"

# Comando para extrair fingerprint SHA-256:
# keytool -list -v -keystore romatec-avalieimob.keystore -alias romatec | findstr SHA256

# Após gerar, atualize:
# 1. backend/public/.well-known/assetlinks.json — substitua PLACEHOLDER_FINGERPRINT
# 2. twa-manifest.json — adicione o fingerprint no array fingerprints
