// @module ptam/steps/StepImovelId — Step 3: Identificação do Imóvel (localização, registros, área, fotos)
import React, { useState, useEffect } from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { Field, SectionHeader } from '../shared/primitives';
import ProprietariosSection from '../shared/ProprietariosSection';
import RuralDocSection, { isRural } from '../shared/RuralDocSection';
import ImageUploader from '../ImageUploader';
import ImovelMap from '../../../maps/ImovelMap';
import StreetView from '../../../maps/StreetView';
import { ConsultaSIGEF } from '../ConsultaSIGEF';

export const StepImovelId = ({ form, setForm }) => {
  const rural = isRural(form.property_type);

  const [enderecoGeocode, setEnderecoGeocode] = useState('');
  useEffect(() => {
    const parts = [
      form.property_address,
      form.property_neighborhood,
      form.property_city,
      form.property_state,
    ].filter(Boolean).join(', ');
    const timer = setTimeout(() => setEnderecoGeocode(parts), 800);
    return () => clearTimeout(timer);
  }, [form.property_address, form.property_neighborhood, form.property_city, form.property_state]);

  return (
  <div>
    <SectionHeader
      title="3. Identificação do Imóvel"
      subtitle="Localização, registro e classificação do imóvel avaliando."
    />
    {rural && (
      <div className="mb-4 flex items-center gap-2 text-xs bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-emerald-800">
        <span className="font-semibold">Modo Rural ativo</span> — unidades de área em hectares (ha) e campos rurais habilitados
        {form.dados_incra_automaticos && (
          <span className="ml-auto px-2 py-0.5 rounded-full bg-emerald-200 text-emerald-800 font-semibold text-xs">
            Dados via SIGEF
          </span>
        )}
      </div>
    )}
    {rural && (
      <div className="grid grid-cols-2 gap-4 mb-2">
        <ConsultaSIGEF form={form} setForm={setForm} />
        <div className="col-span-2 text-center text-xs text-gray-400 font-medium py-1">
          — ou preencha manualmente abaixo —
        </div>
      </div>
    )}
    <div className="grid grid-cols-2 gap-4">
      <Field label="Tipo de imóvel" full>
        <Select value={form.property_type} onValueChange={(v) => setForm({ ...form, property_type: v })}>
          <SelectTrigger><SelectValue placeholder="Selecione o tipo..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="casa">Casa</SelectItem>
            <SelectItem value="apartamento">Apartamento</SelectItem>
            <SelectItem value="terreno">Terreno Urbano</SelectItem>
            <SelectItem value="rural">Imóvel Rural</SelectItem>
            <SelectItem value="fazenda">Fazenda</SelectItem>
            <SelectItem value="sitio">Sítio</SelectItem>
            <SelectItem value="chacara">Chácara</SelectItem>
            <SelectItem value="terreno_rural">Terreno Rural / Gleba</SelectItem>
            <SelectItem value="comercial">Sala / Loja Comercial</SelectItem>
            <SelectItem value="industrial">Galpão / Industrial</SelectItem>
            <SelectItem value="outros">Outros</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Rótulo / Título do imóvel" full>
        <Input value={form.property_label} onChange={(e) => setForm({ ...form, property_label: e.target.value })} placeholder={rural ? 'Ex: Fazenda Santa Luzia, Gleba A' : 'Ex: Apartamento 302, Bloco A, Edifício Alfa'} />
      </Field>
      <Field label={rural ? 'Localidade / Logradouro' : 'Endereço completo'} full>
        <Input value={form.property_address} onChange={(e) => setForm({ ...form, property_address: e.target.value })} placeholder={rural ? 'Estrada, rodovia, km, zona rural...' : 'Rua, número, complemento'} />
      </Field>
      {!rural && (
        <Field label="Bairro">
          <Input value={form.property_neighborhood} onChange={(e) => setForm({ ...form, property_neighborhood: e.target.value })} />
        </Field>
      )}
      <Field label="Cidade">
        <Input value={form.property_city} onChange={(e) => setForm({ ...form, property_city: e.target.value })} />
      </Field>
      <Field label="Estado (UF)">
        <Input value={form.property_state} onChange={(e) => setForm({ ...form, property_state: e.target.value })} placeholder="MA" maxLength={2} />
      </Field>
      <Field label="CEP">
        <Input value={form.property_cep} onChange={(e) => setForm({ ...form, property_cep: e.target.value })} placeholder="00000-000" />
      </Field>
      <Field label="Matrícula">
        <Input value={form.property_matricula} onChange={(e) => setForm({ ...form, property_matricula: e.target.value })} />
      </Field>
      <Field label="Cartório / Ofício de Registro" full>
        <Input value={form.property_cartorio} onChange={(e) => setForm({ ...form, property_cartorio: e.target.value })} placeholder="Ex: 1º Ofício de Registro de Imóveis de ..." />
      </Field>
      <Field label="Latitude (GPS)">
        <Input value={form.property_gps_lat} onChange={(e) => setForm({ ...form, property_gps_lat: e.target.value })} placeholder="-4.9485" />
      </Field>
      <Field label="Longitude (GPS)">
        <Input value={form.property_gps_lng} onChange={(e) => setForm({ ...form, property_gps_lng: e.target.value })} placeholder="-47.4009" />
      </Field>

      <div className="col-span-2 space-y-3 mt-2">
        <div className="text-sm font-semibold text-gray-900">Localização</div>
        <ImovelMap
          endereco={enderecoGeocode}
          lat={form.property_gps_lat}
          lng={form.property_gps_lng}
          height={280}
        />
        <StreetView
          lat={form.property_gps_lat || null}
          lng={form.property_gps_lng || null}
          endereco={enderecoGeocode}
          height={240}
        />
      </div>

      <ProprietariosSection form={form} setForm={setForm} />
      {rural ? (
        <>
          <Field label="Área total (ha — hectares)">
            <Input type="number" step="0.0001" value={form.property_area_ha} onChange={(e) => setForm({ ...form, property_area_ha: Number(e.target.value) })} placeholder="0,0000" />
          </Field>
          <Field label="Área construída / benfeitorias (m²)">
            <Input type="number" step="0.01" value={form.property_area_sqm} onChange={(e) => setForm({ ...form, property_area_sqm: Number(e.target.value) })} placeholder="Área das construções em m²" />
          </Field>
          <Field label="CCIR (Certificado de Cadastro de Imóvel Rural)">
            <Input value={form.ccir_numero || form.ccir || ''} onChange={(e) => setForm({ ...form, ccir_numero: e.target.value, ccir: e.target.value })} placeholder="XXX.XXX.XXX-XXXXXX" />
          </Field>
          <Field label="Código SIGEF (UUID)">
            <Input value={form.sigef_codigo || form.certificacao_sigef || ''} onChange={(e) => setForm({ ...form, sigef_codigo: e.target.value, certificacao_sigef: e.target.value })} placeholder="b533967e-f6b0-4b19-b4a1-fc834e1f9ebb" className="font-mono text-xs" />
          </Field>
          <Field label="Código CAR (Cadastro Ambiental Rural)">
            <Input value={form.car_numero || form.car || ''} onChange={(e) => setForm({ ...form, car_numero: e.target.value, car: e.target.value })} placeholder="MA-2100055-F942.2E73..." />
          </Field>
          <Field label="NIRF / ITR (Imposto Territorial Rural)">
            <Input value={form.nirf_numero || form.nirf_cib || ''} onChange={(e) => setForm({ ...form, nirf_numero: e.target.value, nirf_cib: e.target.value })} placeholder="5.690.070-8" />
          </Field>
          <Field label="Módulo Fiscal do Município (ha)">
            <Input type="number" step="0.01" value={form.modulo_fiscal_ha ?? ''} onChange={(e) => setForm({ ...form, modulo_fiscal_ha: e.target.value === '' ? null : Number(e.target.value) })} placeholder="65" />
          </Field>
          <Field label="Nº de Módulos Fiscais (calculado)">
            <Input
              type="number" step="0.01"
              value={form.numero_modulos_fiscais ?? (form.property_area_ha && form.modulo_fiscal_ha ? (Number(form.property_area_ha) / Number(form.modulo_fiscal_ha)).toFixed(2) : '')}
              onChange={(e) => setForm({ ...form, numero_modulos_fiscais: e.target.value === '' ? null : Number(e.target.value) })}
              placeholder="Calculado automaticamente"
            />
          </Field>
          <Field label="Área explorada (ha)">
            <Input type="number" step="0.0001" value={form.area_explorada_ha ?? ''} onChange={(e) => setForm({ ...form, area_explorada_ha: e.target.value === '' ? null : Number(e.target.value) })} placeholder="0,0000" />
          </Field>
          <Field label="Área de Reserva Legal (ha)">
            <Input type="number" step="0.0001" value={form.area_reserva_legal_ha ?? ''} onChange={(e) => setForm({ ...form, area_reserva_legal_ha: e.target.value === '' ? null : Number(e.target.value) })} placeholder="0,0000" />
          </Field>
          <Field label="Área APP — Preservação Permanente (ha)">
            <Input type="number" step="0.0001" value={form.area_app_ha ?? ''} onChange={(e) => setForm({ ...form, area_app_ha: e.target.value === '' ? null : Number(e.target.value) })} placeholder="0,0000" />
          </Field>
          <Field label="Área de Vegetação Nativa (ha)">
            <Input type="number" step="0.0001" value={form.area_vegetacao_nativa_ha ?? ''} onChange={(e) => setForm({ ...form, area_vegetacao_nativa_ha: e.target.value === '' ? null : Number(e.target.value) })} placeholder="0,0000" />
          </Field>
        </>
      ) : (
        <>
          <Field label="Área total (m²)">
            <Input type="number" step="0.01" value={form.property_area_sqm} onChange={(e) => setForm({ ...form, property_area_sqm: Number(e.target.value) })} />
          </Field>
          <Field label="Área (hectares)">
            <Input type="number" step="0.0001" value={form.property_area_ha} onChange={(e) => setForm({ ...form, property_area_ha: Number(e.target.value) })} />
          </Field>
        </>
      )}
      <Field label="Confrontações / Limites" full>
        <Textarea value={form.property_confrontations} onChange={(e) => setForm({ ...form, property_confrontations: e.target.value })} rows={3} placeholder="Norte: ..., Sul: ..., Leste: ..., Oeste: ..." />
      </Field>
      <Field label="Descrição geral do imóvel" full>
        <Textarea value={form.property_description} onChange={(e) => setForm({ ...form, property_description: e.target.value })} rows={4} />
      </Field>

      <RuralDocSection form={form} setForm={setForm} />
    </div>

    <div className="mt-8 space-y-6 border-t border-gray-100 pt-6">
      <ImageUploader
        label="Fotos do Imóvel (máx 20)"
        images={form.fotos_imovel || []}
        onImagesChange={(ids) => setForm({ ...form, fotos_imovel: ids })}
        maxImages={20}
      />
      <ImageUploader
        label="Documentos do Imóvel — matrícula, IPTU, escritura (máx 10)"
        images={form.fotos_documentos || []}
        onImagesChange={(ids) => setForm({ ...form, fotos_documentos: ids })}
        maxImages={10}
        acceptPdf
      />
    </div>

    <div className="mt-8 border-t border-gray-100 pt-6">
      <div className="text-sm font-semibold text-gray-900 mb-3">Documentação Analisada <span className="text-xs font-normal text-gray-400">(NBR 14653 — Seção 2)</span></div>
      <div className="grid grid-cols-2 gap-2">
        {[
          { id: 'matricula', label: 'Matrícula do imóvel' },
          { id: 'IPTU', label: 'Carnê de IPTU' },
          { id: 'planta', label: 'Planta / Projeto aprovado' },
          { id: 'escritura', label: 'Escritura / Contrato' },
          { id: 'fotos', label: 'Fotografias do imóvel' },
          { id: 'habite_se', label: 'Habite-se / Auto de conclusão' },
          { id: 'geo_rural', label: 'Georreferenciamento (rural)' },
          { id: 'outros_docs', label: 'Outros documentos' },
        ].map(({ id, label }) => {
          const checked = (form.documentos_analisados || []).includes(id);
          return (
            <label key={id} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                checked={checked}
                onChange={(e) => {
                  const prev = form.documentos_analisados || [];
                  const next = e.target.checked ? [...prev, id] : prev.filter((d) => d !== id);
                  setForm({ ...form, documentos_analisados: next });
                }}
              />
              {label}
            </label>
          );
        })}
      </div>
    </div>
  </div>
  );
};
