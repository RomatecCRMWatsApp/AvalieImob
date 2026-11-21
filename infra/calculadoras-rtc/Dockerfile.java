# syntax=docker/dockerfile:1.7
# Imagem das calculadoras Java (regime regular OU Simples Nacional) da Receita Federal.
# O código oficial é clonado na tag/commit FIXADOS (VERSOES.env) — não copiamos nem alteramos a lógica tributária.
#   SERVICE=regime-regular  → api-regime-geral.jar      (porta 8080, base /api)
#   SERVICE=simples-nacional → api-simples-nacional.jar (porta 8082, base /api)
# O banco SQLite (perfil offline) é gerado a partir do regime regular e embutido SOMENTE LEITURA.

# Imagem de execução (JRE). Pode ser trocada só para teste local.
ARG RUNTIME_IMAGE=eclipse-temurin:25-jre

FROM eclipse-temurin:25-jdk AS build
ARG SERVICE=regime-regular
ARG RTC_REGIME_REGULAR_TAG
ARG RTC_REGIME_REGULAR_SHA
ARG RTC_SIMPLES_TAG
ARG RTC_SIMPLES_SHA
# Opcional, só para build atrás de proxy (vazio em produção).
ARG JAVA_TOOL_OPTIONS=""
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates && rm -rf /var/lib/apt/lists/*
# CA extra opcional (só para builds atrás de proxy corporativo/sandbox). Em produção não é passado.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then \
      keytool -importcert -noprompt -alias extra-ca -file /run/secrets/extra_ca -cacerts -storepass changeit && \
      cp /run/secrets/extra_ca /usr/local/share/ca-certificates/extra-ca.crt && update-ca-certificates; \
    fi
WORKDIR /src
# 1) regime regular: sempre (fornece o banco SQLite oficial)
RUN git clone --depth 1 --branch "${RTC_REGIME_REGULAR_TAG}" https://github.com/ReceitaFederal/calculadora-rtc-regime-regular.git rr \
 && test "$(git -C rr rev-parse HEAD)" = "${RTC_REGIME_REGULAR_SHA}"
WORKDIR /src/rr
RUN mkdir -p ./calculadora/db \
 && ./mvnw -q flyway:migrate -Dflyway.configFiles=./flyway/flyway-pro.conf --batch-mode --errors
# 2) empacota o serviço pedido
WORKDIR /src
RUN if [ "${SERVICE}" = "simples-nacional" ]; then \
      git clone --depth 1 --branch "${RTC_SIMPLES_TAG}" https://github.com/ReceitaFederal/calculadora-rtc-simples-nacional.git svc && \
      test "$(git -C svc rev-parse HEAD)" = "${RTC_SIMPLES_SHA}"; \
    else ln -s /src/rr /src/svc; fi
WORKDIR /src/svc
RUN ./mvnw -q -DskipTests package --batch-mode --errors \
 && cp target/api-*.jar /src/app.jar \
 && cp LICENSE /src/LICENSE.receita

FROM ${RUNTIME_IMAGE}
RUN useradd -r -u 10001 rtc
WORKDIR /app
COPY --from=build /src/app.jar /app/app.jar
COPY --from=build /src/LICENSE.receita /app/LICENSE.receita
COPY --from=build --chown=root:root /src/rr/calculadora/db/calculadora-pro.db /app/calculadora/db/calculadora-pro.db
RUN chmod 0444 /app/calculadora/db/calculadora-pro.db
USER rtc
# Heap limitado à fração da RAM do container (Railway define o limite da instância).
ENV JAVA_OPTS="-XX:MaxRAMPercentage=70 -XX:+UseSerialGC -Xss512k"
EXPOSE 8080 8082
# Executa a partir de /app para que ./calculadora/db seja encontrado.
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -Dspring.profiles.active=offline -jar /app/app.jar"]
