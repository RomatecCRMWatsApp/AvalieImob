# Inventário — motores de tratamento de amostras × kit "Análise Estatística Avançada"

Etapa A do kit (15/11/2026). Levantado no repositório real em 15/11/2026 (v1.4.1518).

## O que já existe (em produção desde v1.4.1438 / v1.4.1444)

| Peça | Arquivo | O que faz |
|---|---|---|
| Fatores (homogeneização) | fluxo PTAM (`routes/ptam.py`, `services/ptam_pdf_v2.py`) | Tratamento por fatores — **intocado** |
| Inferência (MCDDM) | `backend/services/inferencia/` | Caminho paralelo, coleção própria `modelos_inferencia` |
| Estimação | `estimacao.py` | OLS via `statsmodels` (QR/pinv), t/F/p bicaudais pelas caudas da SciPy, R²/R²aj, micronumerosidade 3(k+1) bloqueante |
| Transformações | `transformacoes.py` | identidade, ln, inverso, quadrado, raiz — domínio inválido falha apontando dado e variável |
| Diagnóstico | `diagnostico.py` | KS/Lilliefors, Jarque-Bera, Breusch-Pagan, White, Durbin-Watson, aderência ±1/1,64/1,96σ, correlação, VIF, resíduos > 2σ |
| Predição | `predicao.py` | IC 80% da média **e** IP 80% de nova observação separados; limites destransformados (não a amplitude); ln → mediana declarada |
| Enquadramento | `enquadramento.py` + `params/nbr14653_*.json` | Graus por item, grau final e bloqueios ao Grau III; limiares em JSON, nunca hard-coded |
| Revisões | `routes/inferencia.py` | Homologado é imutável (409), "nova versão", descarte exige motivo, isolamento por `user_id` |
| Laudo | `relatorio.py`, `blocos_ptam.py`, `graficos.py` | Laudo em 9 seções + bloco no PTAM vinculado (snapshot congelado com deepcopy) |

## Diferenças frente ao kit — tratadas nesta versão (aditivas)

1. **Posto/condicionamento** — o statsmodels resolve por pseudo-inversa e, com variável
   redundante, devolvia coeficientes arbitrários em silêncio. Agora `estimacao.validar_entrada`
   bloqueia: valor ausente/não finito, n ≤ p, dependente constante, matriz sem posto completo
   (na matriz padronizada) e número de condição > 1e8; e `ajustar` bloqueia variância residual nula.
2. **Influência** — `diagnostico.rodar` passou a devolver alavancagem, resíduo studentizado
   interno e distância de Cook por dado, com triagem 2p/n e 4/n. Só sinaliza: nenhum dado é
   excluído automaticamente. Exibido na aba Diagnóstico e no laudo.
3. **Limiares não conferidos** — `enquadramento` informa `parametros_conferidos`. Enquanto
   `params/nbr14653_*.json` tiver `_conferido_por` nulo, a tela avisa que o grau é triagem.
   O grau calculado **não mudou**.
4. **Benchmark** — `tests/test_inferencia_benchmark.py` confere o motor contra o fixture
   sintético do kit (coeficientes, EP, t, p, F, R²aj, IC/IP 80%, alavancagem, Cook,
   studentizado — tolerância 1e-9) + metamórficos (ordem das linhas, mudança de unidade) e
   os bloqueios do §5.

Resultados de entradas válidas são idênticos aos anteriores (suíte de inferência: 52 testes
anteriores passando sem alteração).

## Pendente (não implementado — não anunciar como disponível)

- Variáveis categóricas/códigos alocados com dicionário, proxies e interações.
- Transformações adicionais do kit (7 anunciadas; o motor tem 5) e Box-Cox.
- Comparação limitada de modelos candidatos com registro dos descartados.
- Análise de sensibilidade e política de média × mediana com correção de viés no ln.
- Perfil normativo conferido pelo RT (`_conferido_por`) — passo do responsável técnico,
  com a cópia autorizada das NBR 14653-2 e 14653-3.
- Benchmark contra Excel/R e amostras de mercado autorizadas.

## Rollback

As mudanças de motor são aditivas: reverter o commit volta ao comportamento anterior.
Modelos já homologados e PDFs emitidos não são recalculados (snapshot imutável).
