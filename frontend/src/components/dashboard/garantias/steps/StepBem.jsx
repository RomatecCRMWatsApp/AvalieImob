// @module Garantias/steps/StepBem — Rural: Step 3 — Descrição do Bem (dinâmico por tipo de garantia)

import React from 'react';
import { SectionTitle, Field, Input, Select, Textarea } from './shared.js';
import ImageUploader from '../../ptam/ImageUploader';

const StepBem = ({ form, set }) => {
  const tipo = form.tipo_garantia;
  return (
    <div className="space-y-6">
      <SectionTitle>Descrição do Bem</SectionTitle>
      <Field label="Descrição Geral" required>
        <Textarea value={form.descricao_bem} onChange={(e) => set('descricao_bem', e.target.value)} rows={4} placeholder="Descreva detalhadamente o bem dado em garantia..." />
      </Field>

      {/* ── Imóvel Rural ─────────────────────────────────────────────────── */}
      {tipo === 'imovel_rural' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Imóvel Rural</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Área Total (ha — hectares)">
              <Input type="number" value={form.area_total_ha} onChange={(e) => set('area_total_ha', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Área Construída / Benfeitorias (m²)">
              <Input type="number" value={form.area_construida_m2} onChange={(e) => set('area_construida_m2', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Uso Atual">
              <Select value={form.uso_atual} onChange={(e) => set('uso_atual', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="pastagem">Pastagem</option>
                <option value="lavoura">Lavoura</option>
                <option value="floresta">Floresta</option>
                <option value="misto">Misto</option>
                <option value="outros">Outros</option>
              </Select>
            </Field>
          </div>
          <Field label="Benfeitorias">
            <Textarea value={form.benfeitorias} onChange={(e) => set('benfeitorias', e.target.value)} placeholder="Casas, currais, armazéns, poços, cercas..." />
          </Field>
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Topografia">
              <Input value={form.topografia} onChange={(e) => set('topografia', e.target.value)} placeholder="Plana, ondulada, montanhosa..." />
            </Field>
            <Field label="Solo / Vegetação">
              <Input value={form.solo_vegetacao} onChange={(e) => set('solo_vegetacao', e.target.value)} placeholder="Latossolo vermelho, cerrado..." />
            </Field>
          </div>

          {/* Registros Rurais */}
          <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/50 p-5">
            <div className="text-sm font-semibold text-emerald-800 mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
              Registros Rurais
              <span className="text-xs font-normal text-emerald-600 ml-1">— documentação específica de imóvel rural</span>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <Field label="Certificacao SIGEF (UUID)">
                <Input value={form.certificacao_sigef || ''} onChange={(e) => set('certificacao_sigef', e.target.value)} placeholder="b533967e-f6b0-4b19-b4a1-fc834e1f9ebb" />
              </Field>
              <Field label="Codigo do Imovel Rural (INCRA)">
                <Input value={form.cadastro_incra || ''} onChange={(e) => set('cadastro_incra', e.target.value)} placeholder="950.203.934.550-0" />
              </Field>
              <Field label="Numero do CCIR">
                <Input value={form.ccir || ''} onChange={(e) => set('ccir', e.target.value)} placeholder="76280733267" />
              </Field>
              <Field label="CIB / NIRF">
                <Input value={form.nirf_cib || ''} onChange={(e) => set('nirf_cib', e.target.value)} placeholder="5.690.070-8" />
              </Field>
              <Field label="Registro no CAR">
                <Input value={form.car || ''} onChange={(e) => set('car', e.target.value)} placeholder="MA-2100055-F942.2E73.176D.42D5.B1C6.6A2F.01F5.B64F" />
              </Field>
              <Field label="Perímetro (m)">
                <Input
                  type="number"
                  value={form.perimetro_m ?? ''}
                  onChange={(e) => set('perimetro_m', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  placeholder="Perímetro total em metros"
                />
              </Field>
            </div>

            {/* Documentos Rurais — Upload */}
            <div className="mt-5 space-y-5">
              <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">Documentos Rurais — Upload</div>
              <ImageUploader label="Mapa Georreferenciado / Certificado SIGEF" images={form.doc_mapa_sigef || []} onImagesChange={(ids) => set('doc_mapa_sigef', ids)} maxImages={3} />
              <ImageUploader label="Memorial Descritivo Topográfico / SIGEF" images={form.doc_memorial_descritivo || []} onImagesChange={(ids) => set('doc_memorial_descritivo', ids)} maxImages={3} />
              <ImageUploader label="CCIR — Certificado de Cadastro de Imóvel Rural" images={form.doc_ccir || []} onImagesChange={(ids) => set('doc_ccir', ids)} maxImages={3} />
              <div>
                <ImageUploader label="ITR — Imposto Territorial Rural" images={form.doc_itr || []} onImagesChange={(ids) => set('doc_itr', ids)} maxImages={5} />
                <p className="text-xs text-emerald-700 mt-1">Envie os últimos 5 exercícios (máx. 5 arquivos)</p>
              </div>
              <ImageUploader label="CAR — Cadastro Ambiental Rural" images={form.doc_car || []} onImagesChange={(ids) => set('doc_car', ids)} maxImages={3} />
            </div>
          </div>
        </div>
      )}

      {/* ── Grãos / Safra ────────────────────────────────────────────────── */}
      {tipo === 'graos_safra' && (
        <div className="space-y-4">
          <SectionTitle>Dados dos Grãos / Safra</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Cultura">
              <Select value={form.cultura} onChange={(e) => set('cultura', e.target.value)}>
                <option value="">Selecionar...</option>
                {['Soja','Milho','Café','Cana-de-açúcar','Algodão','Arroz','Feijão','Trigo','Sorgo','Outros'].map((c) => (
                  <option key={c} value={c.toLowerCase()}>{c}</option>
                ))}
              </Select>
            </Field>
            <Field label="Quantidade (toneladas)"><Input type="number" value={form.quantidade_toneladas} onChange={(e) => set('quantidade_toneladas', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Sacas (60 kg)"><Input type="number" value={form.sacas} onChange={(e) => set('sacas', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Produtividade (sc/ha)"><Input type="number" value={form.produtividade_sc_ha} onChange={(e) => set('produtividade_sc_ha', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Safra Referência"><Input value={form.safra_referencia} onChange={(e) => set('safra_referencia', e.target.value)} placeholder="Ex.: 2024/2025" /></Field>
            <Field label="Local de Armazenagem"><Input value={form.local_armazenagem} onChange={(e) => set('local_armazenagem', e.target.value)} /></Field>
          </div>
        </div>
      )}

      {/* ── Bovinos ──────────────────────────────────────────────────────── */}
      {tipo === 'bovinos' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Rebanho Bovino</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Raça / Tipo"><Input value={form.raca_tipo} onChange={(e) => set('raca_tipo', e.target.value)} placeholder="Ex.: Nelore, Angus..." /></Field>
            <Field label="Quantidade (cabeças)"><Input type="number" value={form.quantidade_cabecas} onChange={(e) => set('quantidade_cabecas', parseInt(e.target.value) || 0)} /></Field>
            <Field label="Categoria">
              <Select value={form.categoria} onChange={(e) => set('categoria', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="boi_gordo">Boi Gordo</option>
                <option value="vaca">Vaca</option>
                <option value="novilha">Novilha</option>
                <option value="bezerro">Bezerro</option>
                <option value="touro">Touro</option>
                <option value="misto">Misto</option>
              </Select>
            </Field>
            <Field label="Peso Médio (kg)"><Input type="number" value={form.peso_medio_kg} onChange={(e) => set('peso_medio_kg', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Aptidão">
              <Select value={form.aptidao} onChange={(e) => set('aptidao', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="corte">Corte</option>
                <option value="leite">Leite</option>
                <option value="misto">Misto</option>
              </Select>
            </Field>
            <Field label="Local do Rebanho"><Input value={form.local_rebanho} onChange={(e) => set('local_rebanho', e.target.value)} /></Field>
          </div>
        </div>
      )}

      {/* ── Equipamentos / Veículos / Outros ─────────────────────────────── */}
      {(tipo === 'equipamentos' || tipo === 'veiculos' || tipo === 'outros') && (
        <div className="space-y-4">
          <SectionTitle>Dados do {tipo === 'equipamentos' ? 'Equipamento' : tipo === 'veiculos' ? 'Veículo' : 'Bem'}</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Marca"><Input value={form.marca} onChange={(e) => set('marca', e.target.value)} /></Field>
            <Field label="Modelo"><Input value={form.modelo} onChange={(e) => set('modelo', e.target.value)} /></Field>
            <Field label="Ano de Fabricação"><Input type="number" value={form.ano_fabricacao} onChange={(e) => set('ano_fabricacao', parseInt(e.target.value) || 0)} /></Field>
            <Field label="Número de Série / Chassi"><Input value={form.numero_serie} onChange={(e) => set('numero_serie', e.target.value)} /></Field>
            {tipo === 'equipamentos' && (
              <Field label="Potência"><Input value={form.potencia} onChange={(e) => set('potencia', e.target.value)} placeholder="Ex.: 150 cv" /></Field>
            )}
            <Field label={tipo === 'equipamentos' ? 'Horímetro' : 'Hodômetro'}>
              <Input value={form.horimetro_hodometro} onChange={(e) => set('horimetro_hodometro', e.target.value)} />
            </Field>
          </div>
        </div>
      )}
    </div>
  );
};

export default StepBem;
