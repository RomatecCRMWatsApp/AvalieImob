# @module services.inferencia.design_matrix — especificação do modelo e matriz de delineamento.
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from services.inferencia.transformacoes import ErroInferencia, aplicar, rotular


@dataclass
class Regressor:
    campo: str
    transformacao: str = "identidade"
    tipo: str = "quantitativa"        # quantitativa | dicotomica | codigo_alocado
    rotulo: Optional[str] = None

    @property
    def nome(self) -> str:
        return rotular(self.transformacao, self.rotulo or self.campo)

    def to_dict(self) -> dict:
        return {"campo": self.campo, "transformacao": self.transformacao,
                "tipo": self.tipo, "rotulo": self.rotulo, "nome": self.nome}


@dataclass
class Especificacao:
    dependente: str
    transf_dependente: str = "identidade"
    regressores: list = field(default_factory=list)
    intercepto: bool = True

    def to_dict(self) -> dict:
        return {
            "dependente": {"campo": self.dependente,
                           "transformacao": self.transf_dependente},
            "regressores": [r.to_dict() for r in self.regressores],
            "intercepto": self.intercepto,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Especificacao":
        """Aceita o formato persistido em `modelos_inferencia.especificacao`."""
        d = d or {}
        dep = d.get("dependente") or {}
        if isinstance(dep, str):
            dep = {"campo": dep, "transformacao": "identidade"}
        regs = [Regressor(campo=r.get("campo"),
                          transformacao=r.get("transformacao") or "identidade",
                          tipo=r.get("tipo") or "quantitativa",
                          rotulo=r.get("rotulo"))
                for r in (d.get("regressores") or [])]
        return cls(dependente=dep.get("campo"),
                   transf_dependente=dep.get("transformacao") or "identidade",
                   regressores=regs,
                   intercepto=bool(d.get("intercepto", True)))


def filtrar_utilizados(amostra: pd.DataFrame) -> pd.DataFrame:
    """Só os dados marcados como utilizados. Sem a coluna, usa a amostra inteira."""
    if "utilizado" in amostra.columns:
        return amostra[amostra["utilizado"] != False].copy()   # noqa: E712
    return amostra.copy()


def montar(df: pd.DataFrame, esp: Especificacao):
    """Devolve (y, X_com_const, X_sem_const). Valida domínio das transformações."""
    faltando = [r.campo for r in esp.regressores if r.campo not in df.columns]
    if esp.dependente not in df.columns:
        faltando.append(esp.dependente)
    if faltando:
        raise ErroInferencia("Variável ausente na amostra: " + ", ".join(sorted(set(faltando))))

    y = aplicar(esp.transf_dependente, df[esp.dependente].to_numpy(float), esp.dependente)

    cols = {}
    for r in esp.regressores:
        if r.nome in cols:
            raise ErroInferencia(f"Regressor duplicado no modelo: {r.nome}")
        cols[r.nome] = aplicar(r.transformacao, df[r.campo].to_numpy(float), r.campo)
    X_sem_const = pd.DataFrame(cols, index=df.index)

    X = sm.add_constant(X_sem_const.copy(), has_constant="add") if esp.intercepto \
        else X_sem_const.copy()
    return y, X, X_sem_const


def validar_avaliando(esp: Especificacao, avaliando: dict) -> None:
    """Toda característica usada pelo modelo tem de vir do avaliando (falha cedo e clara)."""
    faltando = [r.campo for r in esp.regressores
                if (avaliando or {}).get(r.campo) is None]
    if faltando:
        raise ErroInferencia(
            "Característica do avaliando não informada: " + ", ".join(faltando))


def linha_avaliando(esp: Especificacao, avaliando: dict, colunas) -> pd.DataFrame:
    """Vetor x0 do imóvel avaliando, no MESMO espaço transformado do modelo."""
    validar_avaliando(esp, avaliando)
    linha = {}
    for r in esp.regressores:
        linha[r.nome] = aplicar(r.transformacao,
                                np.array([float(avaliando[r.campo])]), r.campo)[0]
    Xp = pd.DataFrame([linha])
    if esp.intercepto:
        Xp.insert(0, "const", 1.0)
    return Xp[list(colunas)]
