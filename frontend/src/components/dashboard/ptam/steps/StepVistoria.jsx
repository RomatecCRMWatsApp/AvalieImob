import React from 'react';

const FIELDS = [
  { key: 'vistoria_date',           label: 'Data da Vistoria',                     type: 'date' },
  { key: 'vistoria_responsavel',    label: 'Responsável pela Vistoria',             type: 'text' },
  { key: 'vistoria_condicoes',      label: 'Condições de Acesso',                   type: 'text' },
  { key: 'vistoria_objective',      label: '1. Objetivo da Vistoria',               type: 'textarea' },
  { key: 'vistoria_methodology',    label: '2. Metodologia Adotada',                type: 'textarea' },
  { key: 'topography',              label: '3. Topografia',                          type: 'textarea' },
  { key: 'soil_vegetation',         label: '3. Solo e Cobertura Vegetal (geral)',    type: 'textarea' },
  { key: 'uso_atual',               label: '3.1 Uso Atual',                          type: 'textarea' },
  { key: 'cobertura_vegetal',       label: '3.2 Cobertura Vegetal',                  type: 'textarea' },
  { key: 'hidrografia',             label: '3.3 Hidrografia',                        type: 'textarea' },
  { key: 'benfeitorias',            label: '4. Benfeitorias Existentes',             type: 'textarea' },
  { key: 'infraestrutura_interna',  label: '5. Infraestrutura Interna',              type: 'textarea' },
  { key: 'accessibility',           label: '6. Acessibilidade e Infraestrutura',     type: 'textarea' },
  { key: 'urban_context',           label: '7. Contexto Urbano e Mercadológico',     type: 'textarea' },
  { key: 'conservation_state',      label: '8. Estado Geral de Conservação',         type: 'textarea' },
  { key: 'situacao_fundiaria',      label: '9. Situação Fundiária',                  type: 'textarea' },
  { key: 'passivo_ambiental',       label: '10. Passivo Ambiental',                  type: 'textarea' },
  { key: 'potencial_exploratorio',  label: '11. Potencial Exploratório',             type: 'textarea' },
  { key: 'aspectos_legais',         label: '12. Aspectos Legais',                    type: 'textarea' },
  { key: 'restricoes_uso',          label: '13. Restrições de Uso',                  type: 'textarea' },
  { key: 'vistoria_synthesis',      label: '14. Síntese Conclusiva da Vistoria',     type: 'textarea' },
];

export default function StepVistoria({ data, onChange }) {
  const handle = (key) => (e) => onChange({ ...data, [key]: e.target.value });

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold text-green-700">Vistoria Técnica</h2>
      <p className="text-sm text-gray-500">
        Preencha as 15 sub-seções de vistoria conforme o modelo PTAM nº 7010. Campos não preenchidos
        serão omitidos do relatório.
      </p>

      {FIELDS.map(({ key, label, type }) => (
        <div key={key} className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">{label}</label>
          {type === 'textarea' ? (
            <textarea
              rows={3}
              className="border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 resize-y"
              value={data[key] || ''}
              onChange={handle(key)}
              placeholder={`Descreva: ${label}`}
            />
          ) : (
            <input
              type={type}
              className="border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              value={data[key] || ''}
              onChange={handle(key)}
            />
          )}
        </div>
      ))}
    </div>
  );
}
