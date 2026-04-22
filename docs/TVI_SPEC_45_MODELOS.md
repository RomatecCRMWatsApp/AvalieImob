# TVI - Especificação Completa dos 45 Modelos

## Schema do Banco — vistoria_models

```json
{
  "id": "TVI-01",
  "nome": "Vistoria de Avaliação (PTAM)",
  "ramo": "GERAL",
  "aplicacao": "string descritiva",
  "normas": ["NBR 14653"],
  "requer_art": true,
  "campos": [
    {
      "id": "campo_unico_id",
      "secao": "Nome da Seção",
      "tipo": "text|number|select|multiselect|checkbox|tabela|foto|assinatura|data|caixa_texto",
      "label": "Label visível",
      "opcoes": ["opção1", "opção2"],
      "obrigatorio": true,
      "placeholder": "...",
      "ajuda": "texto de ajuda"
    }
  ],
  "secoes_obrigatorias": ["Identificação", "Responsável Técnico", "...", "Registro Fotográfico", "Conclusão Técnica", "Assinaturas"],
  "exportacao": { "pdf": true, "docx": true, "compartilhar_email": true, "compartilhar_whatsapp": true }
}
```

## Regras
1. NUNCA reutilizar campos entre modelos
2. Renderização dinâmica: só campos do modelo selecionado
3. FieldRenderer suporta: text, number, select, multiselect, checkbox, tabela, foto, assinatura, data, caixa_texto
4. PDF/DOCX só seções do modelo específico
5. Seed cria 45 modelos completos em JSON
