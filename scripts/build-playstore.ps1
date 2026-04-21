# @module scripts/build-playstore — Build completo para Play Store
# Fase 2: Execute após gerar keystore e ícones

echo "🚀 Build AvaliImob — Play Store"
echo "================================"

# 1. Build do PWA
echo "🏗️ Build do frontend..."
cd ..
npm run build

# 2. Build Android
echo "🤖 Build Android..."
cd android
.\gradlew bundleRelease

# 3. Assinar AAB (ajuste o caminho do keystore)
echo "🔑 Assinando AAB..."
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 -keystore ../romatec-avalieimob.keystore app/build/outputs/bundle/release/app-release.aab romatec

echo "✅ Concluído!"
echo "📦 AAB: android/app/build/outputs/bundle/release/app-release.aab"
echo ""
echo "PRÓXIMOS PASSOS:"
echo "1. Acesse: https://play.google.com/console"
echo "2. Crie novo app: br.com.romatec.avalieimob"
echo "3. Faça upload do AAB gerado"
