# @module pdf.templates.resilient — DocTemplates resilientes a LayoutError.
#
# Problema: o ReportLab aborta o PDF INTEIRO com
#   LayoutError: Flowable <...> too large on page N in frame ...
# quando UM flowable precisa de altura maior que a do frame e não pode ser
# dividido (Spacer/Image/linha de Table/parágrafo indivisível). Isso vinha
# derrubando a geração do contrato ("Erro ao gerar PDF") de forma intermitente
# e difícil de reproduzir, dependente dos dados.
#
# Solução (à prova de falha, não-intrusiva): em vez de prevenir cada gatilho
# específico (tentado sem sucesso em releases anteriores), tornamos o próprio
# motor de layout resiliente — um flowable não-posicionável é REGISTRADO em log
# (com suas dimensões reais, para diagnóstico) e PULADO, e o documento é gerado
# mesmo assim. O caso normal (sem LayoutError) é byte-a-byte idêntico ao padrão.
import logging

from reportlab.platypus import SimpleDocTemplate, BaseDocTemplate
from reportlab.platypus.doctemplate import LayoutError

logger = logging.getLogger("romatec")


class _ResilientFlowMixin:
    """Sobrescreve handle_flowable para não derrubar o build inteiro quando um
    único flowable é grande demais para o frame e indivisível."""

    def handle_flowable(self, flowables):
        # ReportLab faz `del flowables[0]` no INÍCIO de handle_flowable (extrai o
        # flowable da lista antes de posicioná-lo). Quando o LayoutError é
        # levantado, o flowable problemático JÁ saiu da lista — basta capturá-lo
        # aqui (para log), engolir a exceção e retornar: o laço de build segue
        # com o restante. Não removemos nada da lista (seria descartar um inocente).
        culprit = flowables[0] if flowables else None
        try:
            return super().handle_flowable(flowables)
        except LayoutError:
            try:
                ident = culprit.identity(80)
                w = getattr(culprit, "width", getattr(culprit, "_width", "?"))
                h = getattr(culprit, "height", getattr(culprit, "_height", "?"))
            except Exception:
                ident, w, h = repr(culprit), "?", "?"
            logger.warning(
                "PDF resiliente: flowable nao-posicionavel pulado (%sx%s) | %s | %s",
                w, h, type(culprit).__name__, ident,
            )
            return


class ResilientSimpleDocTemplate(_ResilientFlowMixin, SimpleDocTemplate):
    pass


class ResilientBaseDocTemplate(_ResilientFlowMixin, BaseDocTemplate):
    pass
