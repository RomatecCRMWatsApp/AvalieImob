# @module services.inss_obra.prazos — Prazos do processo de regularização da obra.
#
# - CNO: inscrição em até 30 dias do início da obra (IN RFB 2.061/2021).
# - DARF da aferição: vence no dia 20 do mês seguinte ao da competência da aferição
#   (Lei 8.212/91, art. 30, I, "b"), antecipando para o dia útil anterior.
#   A competência é o mês em que a aferição é concluída no SERO (Manual p.28).
# Feriados: só os nacionais fixos. Feriado móvel/municipal fica a cargo do usuário —
# a tela avisa.
from __future__ import annotations

from datetime import date, timedelta

_FERIADOS_FIXOS = {(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15),
                   (11, 20), (12, 25)}


def _util(d: date) -> bool:
    return d.weekday() < 5 and (d.month, d.day) not in _FERIADOS_FIXOS


def dia_util_anterior_ou_igual(d: date) -> date:
    while not _util(d):
        d -= timedelta(days=1)
    return d


def prazo_cno(data_inicio: date) -> date:
    return data_inicio + timedelta(days=30)


def vencimento_darf(data_afericao: date) -> date:
    a, m = (data_afericao.year + 1, 1) if data_afericao.month == 12 else (data_afericao.year, data_afericao.month + 1)
    return dia_util_anterior_ou_igual(date(a, m, 20))


def _situacao(prazo: date, hoje: date, feito: bool) -> str:
    if feito:
        return "feito"
    if hoje > prazo:
        return "vencido"
    if (prazo - hoje).days <= 7:
        return "proximo"
    return "em_dia"


def montar(obra: dict, hoje: date) -> list[dict]:
    out = []
    ini = obra.get("data_inicio")
    if ini:
        d = date.fromisoformat(str(ini)[:10])
        p = prazo_cno(d)
        feito = bool(obra.get("cno"))
        out.append({"chave": "cno", "titulo": "Inscrição da obra no CNO",
                    "prazo": p.isoformat(), "situacao": _situacao(p, hoje, feito),
                    "base": "30 dias do início da obra (IN RFB 2.061/2021)"})
    af = obra.get("data_afericao")
    if af:
        d = date.fromisoformat(str(af)[:10])
        p = vencimento_darf(d)
        feito = (obra.get("checklist") or {}).get("darf_pago", {}).get("status") == "ok"
        out.append({"chave": "darf", "titulo": "Pagamento do DARF da aferição",
                    "prazo": p.isoformat(), "situacao": _situacao(p, hoje, feito),
                    "base": "Dia 20 do mês seguinte à aferição, antecipado para dia útil "
                            "(Lei 8.212/91, art. 30, I, b)"})
    return out
