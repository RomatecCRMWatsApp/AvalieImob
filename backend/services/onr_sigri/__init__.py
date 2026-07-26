# @package services.onr_sigri — Gerador de Arquivo ONR (SIG-RI) STANDALONE.
#
# Módulo SEPARADO dos procedimentos do Geo Urbano (remembramento/desdobro/
# retificação/usucapião/reurb). Fluxo próprio: o RT sobe o MAPA já pronto + o
# MEMORIAL + a ART/TRT + a CERTIDÃO; o sistema EXTRAI a poligonal do memorial e
# GERA o pacote shapefile SIG-RI para envio ao mapa.onr.org.br.
#
# REUTILIZA (sem alterar) o motor SIG-RI: services.geo_urbano.geodesia,
# schema_onr, geo_export e validacao_onr.
