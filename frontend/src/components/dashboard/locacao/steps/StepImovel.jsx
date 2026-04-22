// @module locacao/steps/StepImovel — Step 3: Identificação do Imóvel para Locação
import React from 'react';
import { Field, Input, Textarea, Select, Grid } from '../shared/primitives';
import { IMOVEL_TIPO_OPTIONS, CONSERVACAO_OPTIONS, PADRAO_OPTIONS } from '../locacaoHelpers';

export const StepImovel = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const consideraTerreno = !!form.considerar_area_terreno;
  const consideraConstruida = form.considerar_area_construida !== false; // default true

  const handleAreaTerreno = (checked) => {
    // Pelo menos uma deve estar marcada
    if (!checked && !consideraConstruida) return;
    set('considerar_area_terreno', checked);
  };

  const handleAreaConstruida = (checked) => {
    // Pelo menos uma deve estar marcada
    if (!checked && !consideraTerreno) return;
    set('considerar_area_construida', checked);
  };

  return (
    <div className="space-y-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">3. Identificação do Imóvel</h3>
      <Grid cols={2}>
        <Field label="Endereço" className="md:col-span-2">
          <Input value={form.imovel_endereco} onChange={e => set('imovel_endereco', e.target.value)} placeholder="Rua, número, complemento" />
        </Field>
        <Field label="Bairro">
          <Input value={form.imovel_bairro} onChange={e => set('imovel_bairro', e.target.value)} />
        </Field>
        <Field label="Cidade">
          <Input value={form.imovel_cidade} onChange={e => set('imovel_cidade', e.target.value)} />
        </Field>
        <Field label="Estado">
          <Input value={form.imovel_estado} onChange={e => set('imovel_estado', e.target.value)} placeholder="UF" maxLength={2} />
        </Field>
        <Field label="CEP">
          <Input value={form.imovel_cep} onChange={e => set('imovel_cep', e.target.value)} placeholder="00000-000" />
        </Field>
        <Field label="Matrícula">
          <Input value={form.imovel_matricula} onChange={e => set('imovel_matricula', e.target.value)} />
        </Field>
        <Field label="Cartório de Registro">
          <Input value={form.imovel_cartorio} onChange={e => set('imovel_cartorio', e.target.value)} />
        </Field>
        <Field label="Tipo do Imóvel" className="md:col-span-2">
          <Select
            value={form.imovel_tipo}
            onChange={e => set('imovel_tipo', e.target.value)}
            options={IMOVEL_TIPO_OPTIONS}
            placeholder="Selecione..."
          />
        </Field>
        <Field label="Área do Terreno (m²)">
          <Input type="number" value={form.imovel_area_terreno} onChange={e => set('imovel_area_terreno', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Área Construída (m²)">
          <Input type="number" value={form.imovel_area_construida} onChange={e => set('imovel_area_construida', parseFloat(e.target.value) || 0)} />
        </Field>
      </Grid>

      {/* Seção: Áreas consideradas no cálculo */}
      <div className="border border-emerald-200 rounded-xl p-4 bg-emerald-50 space-y-4">
        <p className="text-sm font-semibold text-emerald-900">Áreas consideradas no cálculo do valor final</p>
        <p className="text-xs text-emerald-700">Selecione qual(is) área(s) deve(m) ser usadas para calcular o valor de locação. Pelo menos uma deve estar marcada.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Área do Terreno */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={consideraTerreno}
                onChange={e => handleAreaTerreno(e.target.checked)}
                className="w-4 h-4 accent-emerald-700"
              />
              <span className="text-sm font-medium text-gray-800">Considerar área do terreno</span>
            </label>
            {consideraTerreno && (
              <Field label="Valor do m² do Terreno (R$)">
                <Input
                  type="number"
                  value={form.valor_m2_terreno ?? ''}
                  onChange={e => set('valor_m2_terreno', e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="Ex: 500,00"
                />
              </Field>
            )}
          </div>

          {/* Área Construída */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={consideraConstruida}
                onChange={e => handleAreaConstruida(e.target.checked)}
                className="w-4 h-4 accent-emerald-700"
              />
              <span className="text-sm font-medium text-gray-800">Considerar área construída</span>
            </label>
            {consideraConstruida && (
              <Field label="Valor do m² da Construção (R$)">
                <Input
                  type="number"
                  value={form.valor_m2_construcao ?? ''}
                  onChange={e => set('valor_m2_construcao', e.target.value ? parseFloat(e.target.value) : null)}
                  placeholder="Ex: 855,77"
                />
              </Field>
            )}
          </div>
        </div>

        {/* Preview do cálculo */}
        {(consideraTerreno || consideraConstruida) && (
          <div className="mt-2 p-3 bg-white rounded-lg border border-emerald-100 text-xs text-gray-700 space-y-1">
            <p className="font-semibold text-emerald-800 mb-1">Pré-visualização do cálculo:</p>
            {consideraTerreno && form.valor_m2_terreno > 0 && form.imovel_area_terreno > 0 && (
              <p>Terreno: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(form.valor_m2_terreno)} × {form.imovel_area_terreno} m² = <strong>{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(form.valor_m2_terreno * form.imovel_area_terreno)}</strong></p>
            )}
            {consideraConstruida && form.valor_m2_construcao > 0 && form.imovel_area_construida > 0 && (
              <p>Construção: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(form.valor_m2_construcao)} × {form.imovel_area_construida} m² = <strong>{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(form.valor_m2_construcao * form.imovel_area_construida)}</strong></p>
            )}
            {(() => {
              const vtotal =
                (consideraTerreno && form.valor_m2_terreno > 0 ? form.valor_m2_terreno * (form.imovel_area_terreno || 0) : 0) +
                (consideraConstruida && form.valor_m2_construcao > 0 ? form.valor_m2_construcao * (form.imovel_area_construida || 0) : 0);
              return vtotal > 0 ? (
                <p className="font-semibold text-emerald-700 border-t border-emerald-100 pt-1 mt-1">
                  Valor Total: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(vtotal)}
                </p>
              ) : null;
            })()}
          </div>
        )}
      </div>

      <Grid cols={2}>
        <Field label="Idade Aparente (anos)">
          <Input type="number" value={form.imovel_idade} onChange={e => set('imovel_idade', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Nº de Quartos">
          <Input type="number" min={0} value={form.imovel_num_quartos} onChange={e => set('imovel_num_quartos', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Estado de Conservação">
          <Select value={form.imovel_estado_conservacao} onChange={e => set('imovel_estado_conservacao', e.target.value)} options={CONSERVACAO_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Padrão de Acabamento">
          <Select value={form.imovel_padrao_acabamento} onChange={e => set('imovel_padrao_acabamento', e.target.value)} options={PADRAO_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Nº de Banheiros">
          <Input type="number" min={0} value={form.imovel_num_banheiros} onChange={e => set('imovel_num_banheiros', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Vagas de Garagem">
          <Input type="number" min={0} value={form.imovel_num_vagas} onChange={e => set('imovel_num_vagas', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Piscina" className="flex items-center gap-2 pt-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.imovel_piscina} onChange={e => set('imovel_piscina', e.target.checked)} className="w-4 h-4 accent-emerald-700" />
            <span className="text-sm text-gray-700">Possui piscina</span>
          </label>
        </Field>
        <Field label="Características Adicionais" className="md:col-span-2">
          <Textarea value={form.imovel_caracteristicas} onChange={e => set('imovel_caracteristicas', e.target.value)} placeholder="Churrasqueira, área de lazer, varanda..." />
        </Field>
      </Grid>
    </div>
  );
};
