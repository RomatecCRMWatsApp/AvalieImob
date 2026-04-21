# 📱 Romatec AvaliImob — Publicação Play Store

Este documento contém todas as instruções para publicar o AvaliImob na Google Play Store usando Trusted Web Activity (TWA).

---

## ✅ PRÉ-REQUISITOS

- [x] PWA funcional com HTTPS
- [x] manifest.json completo
- [x] Service Worker registrado
- [x] assetlinks.json servido em `/.well-known/assetlinks.json`
- [x] Página de privacidade em `/privacidade`

---

## 🔐 ETAPA 1: Gerar Keystore (FAÇA UMA VEZ SÓ)

### No Windows (PowerShell como Administrador):

```powershell
# Navegue até a pasta do projeto
cd "C:\Users\Ronicley Pinto\Documents\ROMATEC_AVALIEIMOB_\AvalieImob"

# Encontre o keytool no Java (ajuste o caminho conforme sua instalação)
$KEYTOOL = "C:\Program Files\Java\jdk-17\bin\keytool.exe"

# Gere o keystore
& $KEYTOOL -genkey -v `
  -keystore romatec-avalieimob.keystore `
  -alias romatec `
  -keyalg RSA `
  -keysize 2048 `
  -validity 10000 `
  -dname "CN=Romatec Consultoria Imobiliaria, OU=Tecnologia, O=J R P Bezerra Ltda, L=Acailandia, ST=Maranhao, C=BR" `
  -storepass SUA_SENHA_SEGURA `
  -keypass SUA_SENHA_SEGURA
```

### No Linux/Mac:

```bash
cd ~/Documents/ROMATEC_AVALIEIMOB_/AvalieImob

keytool -genkey -v \
  -keystore romatec-avalieimob.keystore \
  -alias romatec \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -dname "CN=Romatec Consultoria Imobiliaria, OU=Tecnologia, O=J R P Bezerra Ltda, L=Acailandia, ST=Maranhao, C=BR"
```

---

## 🔑 ETAPA 2: Extrair Fingerprint SHA-256

### Windows:
```powershell
$KEYTOOL = "C:\Program Files\Java\jdk-17\bin\keytool.exe"
& $KEYTOOL -list -v -keystore romatec-avalieimob.keystore -alias romatec | findstr SHA256
```

### Linux/Mac:
```bash
keytool -list -v -keystore romatec-avalieimob.keystore -alias romatec | grep SHA256
```

**Saída esperada:**
```
SHA256: A1:B2:C3:D4:E5:F6:... (formato com dois pontos)
```

---

## 📝 ETAPA 3: Atualizar Fingerprint nos Arquivos

### 1. Atualize `backend/public/.well-known/assetlinks.json`:

Substitua `PLACEHOLDER_FINGERPRINT_SUBSTITUIR_APOS_GERAR_KEYSTORE` pelo fingerprint **sem os dois pontos**:

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "br.com.romatec.avalieimob",
    "sha256_cert_fingerprints": ["A1B2C3D4E5F6..."]
  }
}]
```

### 2. Atualize `twa-manifest.json`:

```json
"fingerprints": ["A1B2C3D4E5F6..."]
```

### 3. Commit e push:

```bash
git add backend/public/.well-known/assetlinks.json twa-manifest.json
git commit -m "feat(playstore): adiciona SHA-256 fingerprint do keystore"
git push origin main
```

---

## 🎨 ETAPA 4: Gerar Ícones Android

### Opção A: Usando Android Studio (Recomendado)

1. Abra o Android Studio
2. File → New → Image Asset
3. Selecione o ícone base: `frontend/public/brand/icone.png`
4. Configure:
   - Foreground Layer: ícone com padding 10%
   - Background Layer: cor #060e0a
5. Exporte para `android/app/src/main/res/`

### Opção B: Ferramenta Online

Use [https://romannurik.github.io/AndroidAssetStudio/icons-launcher.html](https://romannurik.github.io/AndroidAssetStudio/icons-launcher.html)

- **Foreground:** `frontend/public/brand/icone.png`
- **Background:** #060e0a
- **Nome:** ic_launcher
- **Download** e extraia para `android/app/src/main/res/`

### Ícones necessários:

```
android/app/src/main/res/
├── mipmap-mdpi/ic_launcher.png (48x48)
├── mipmap-hdpi/ic_launcher.png (72x72)
├── mipmap-xhdpi/ic_launcher.png (96x96)
├── mipmap-xxhdpi/ic_launcher.png (144x144)
├── mipmap-xxxhdpi/ic_launcher.png (192x192)
└── mipmap-xxxhdpi/ic_launcher_round.png (192x192)
```

---

## 🏗️ ETAPA 5: Build do AAB (Android App Bundle)

### Instalar Android SDK + Gradle:

1. Baixe Android Studio: https://developer.android.com/studio
2. Instale o SDK (API 34)
3. Configure variável de ambiente `ANDROID_HOME`

### Build:

```powershell
# Windows
cd "C:\Users\Ronicley Pinto\Documents\ROMATEC_AVALIEIMOB_\AvalieImob\android"
.\gradlew.bat bundleRelease

# Linux/Mac
cd ~/Documents/ROMATEC_AVALIEIMOB_/AvalieImob/android
./gradlew bundleRelease
```

### Assinar o AAB:

```powershell
# Windows
jarsigner -verbose `
  -sigalg SHA256withRSA `
  -digestalg SHA-256 `
  -keystore ../romatec-avalieimob.keystore `
  -storepass SUA_SENHA_SEGURA `
  app/build/outputs/bundle/release/app-release.aab `
  romatec

# Linux/Mac
jarsigner -verbose \
  -sigalg SHA256withRSA \
  -digestalg SHA-256 \
  -keystore ../romatec-avalieimob.keystore \
  -storepass SUA_SENHA_SEGURA \
  app/build/outputs/bundle/release/app-release.aab \
  romatec
```

---

## 🚀 ETAPA 6: Publicar na Play Store

1. Acesse: https://play.google.com/console
2. Crie conta de desenvolvedor (taxa única de $25)
3. Clique em "Criar app"
   - Nome: Romatec AvaliImob
   - Idioma: Português (Brasil)
4. Preencha a ficha (use `PLAYSTORE_LISTING.md` como referência)
5. Em "App bundles", faça upload do `app-release.aab`
6. Configure assinatura de app (Play App Signing)
7. Preencha questionário de classificação de conteúdo
8. Defina preço e distribuição (Brasil)
9. Envie para revisão

---

## 📁 ESTRUTURA DE ARQUIVOS

```
AvalieImob/
├── android/                    ← Projeto Android TWA
│   ├── app/
│   │   ├── build.gradle
│   │   ├── proguard-rules.pro
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       └── res/
│   │           ├── drawable/splash.xml
│   │           ├── mipmap-*/ic_launcher.png
│   │           ├── values/colors.xml
│   │           ├── values/strings.xml
│   │           └── xml/file_paths.xml
│   ├── build.gradle
│   ├── gradle.properties
│   └── settings.gradle
├── backend/public/.well-known/
│   └── assetlinks.json         ← Digital Asset Links
├── scripts/
│   ├── generate-keystore.sh    ← Instruções keystore
│   └── build-playstore.ps1     ← Script de build
├── twa-manifest.json           ← Configuração TWA
├── PLAYSTORE_LISTING.md        ← Textos da ficha
├── romatec-avalieimob.keystore ← CHAVE PRIVADA (não commitar!)
└── README_PLAYSTORE.md         ← Este arquivo
```

---

## ⚠️ IMPORTANTE

- **NUNCA** commite o `.keystore` no GitHub
- **Guarde backup** do keystore em local seguro
- **Sem o keystore**, você não poderá atualizar o app
- O fingerprint SHA-256 deve ser exatamente igual no `assetlinks.json` e no app

---

## 🆘 SUPORTE

Em caso de problemas:
1. Verifique se `/.well-known/assetlinks.json` está acessível publicamente
2. Teste com [Google Digital Asset Links Tool](https://developers.google.com/digital-asset-links/tools/generator)
3. Verifique logs do Android Studio em caso de erro de build
