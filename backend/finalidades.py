# @module finalidades — Mapa único finalidade-chave → rótulo legível do PTAM.
# Extraído do antigo pdf/ptam_pdf.py (descontinuado). Fonte única consumida
# pelo gerador canônico services/ptam_pdf_v2.py.

FINALIDADE_MAP = {
    # Compra e Venda
    "cv_alienacao": "Compra e Venda — Alienação",
    "cv_aquisicao": "Compra e Venda — Aquisição",
    "cv_oferta": "Compra e Venda — Oferta Pública",
    "cv_dacao": "Compra e Venda — Dação em Pagamento",
    # Garantia Bancária
    "gar_sfh": "Garantia Bancária — Financiamento SFH",
    "gar_sfi": "Garantia Bancária — Financiamento SFI",
    "gar_credito_rural": "Garantia Bancária — Crédito Rural (Penhor Rural)",
    "gar_refinanciamento": "Garantia Bancária — Refinanciamento",
    "gar_lci_cri": "Garantia Bancária — LCI / CRI",
    "gar_ccb": "Garantia Bancária — CCB Imobiliária",
    # Judicial / Pericial
    "judicial_partilha": "Judicial — Partilha de Bens (Inventário / Divórcio)",
    "judicial_desapropriacao": "Judicial — Desapropriação",
    "judicial_indenizacao": "Judicial — Ação de Indenização",
    "judicial_execucao": "Judicial — Execução de Sentença",
    "judicial_usucapiao": "Judicial — Usucapião",
    "judicial_pericia": "Perícia Judicial (CPC art. 156)",
    # Locação
    "loc_fixacao": "Locação — Fixação de Aluguel",
    "loc_revisao": "Locação — Revisão de Aluguel (Lei 8.245/91)",
    "loc_renovatoria": "Locação — Ação Renovatória",
    # Seguros
    "seg_reposicao": "Seguros — Valor de Reposição",
    "seg_sinistro": "Seguros — Sinistro",
    "seg_risco": "Seguros — Valor em Risco",
    # Tributário / Fiscal
    "trib_itbi": "Tributário — Base de Cálculo ITBI",
    "trib_itcmd": "Tributário — Base de Cálculo ITCMD (Herança / Doação)",
    "trib_ir": "Tributário — Imposto de Renda (Ganho de Capital)",
    "trib_iptu_itr": "Tributário — IPTU / ITR Progressivo",
    # Incorporação e Registro
    "inc_registro": "Incorporação — Registro (Lei 4.591/64)",
    "inc_afetacao": "Incorporação — Patrimônio de Afetação (Lei 13.786/2018)",
    "inc_permuta": "Incorporação — Permuta",
    # Execução de Garantia
    "exec_fid_1": "Execução de Garantia — Alienação Fiduciária 1º Leilão (Lei 9.514/97 art. 27)",
    "exec_fid_2": "Execução de Garantia — Alienação Fiduciária 2º Leilão",
    "exec_hipoteca": "Execução de Garantia — Execução Hipotecária",
    "exec_consolidacao": "Execução de Garantia — Consolidação da Propriedade",
    # Desapropriação
    "desap_utilidade": "Desapropriação por Utilidade Pública (Dec.-Lei 3.365/41)",
    "desap_interesse_social": "Desapropriação por Interesse Social (Lei 4.132/62)",
    "desap_reforma_agraria": "Desapropriação — Reforma Agrária (LC 76/93)",
    # Regularização Fundiária
    "reurb_s_e": "Regularização Fundiária — REURB-S / REURB-E (Lei 13.465/2017)",
    "reurb_demarcacao": "Regularização Fundiária — Demarcação Urbanística",
    # Outros
    "outros_contab": "Contabilidade / Balanço Patrimonial (CPC 28 / IFRS 13)",
    "outros_fii": "Fundo de Investimento Imobiliário (FII)",
    "outros_ma": "Fusão e Aquisição (M&A)",
    "outros_bts": "Locação Built to Suit",
    "outros_diligencia": "Due Diligence Imobiliária",
    # Legacy values
    "compra_venda": "Compra e Venda",
    "financiamento": "Financiamento / Garantia Bancária",
    "judicial": "Uso Judicial / Inventário",
    "inventario": "Inventário / Partilha",
    "locacao": "Locação",
    "garantia": "Garantia de Crédito",
    "permuta": "Permuta",
    "outros": "Outros",
    # Especulação de Mercado Imobiliário 2026 — chave real do wizard (cv_*)
    "cv_especulacao": "Especulação de Mercado Imobiliário 2026 — Oferta e Venda Direta",
}

# Alias de compatibilidade com o nome antigo.
_FINALIDADE_MAP = FINALIDADE_MAP
