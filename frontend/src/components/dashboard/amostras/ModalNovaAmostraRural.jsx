// @module dashboard/amostras/ModalNovaAmostraRural — Modal completo de amostra RURAL.
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Loader2, Upload, X, Wheat } from 'lucide-react';
import { Button } from '../../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { useToast } from '../../../hooks/use-toast';
import { amostrasAPI, uploadAPI } from '../../../lib/api';
import {
  TIPOS_RURAL, TIPO_AMOSTRA_RURAL, TOPOGRAFIA, SOLO, RECURSOS_HIDRICOS, VEGETACAO,
  ATIVIDADE_PRINCIPAL, BENFEITORIAS_RURAL, SEDE_CASA,
  hoje, num, fmtBRL, fmtNum, calcRsHa, m2ToHa, m2ToAlq,
} from './amostraOptions';

const Label = ({ children }) => (
  <label className="text-xs font-semibold text-gray-600">{children}</label>
);
const inputCls =
  'w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-600 focus:border-amber-600';

const TextField = ({ label, value, onChange, type = 'text', placeholder = '', req = false }) => (
  <div>
    <Label>{label}{req && <span className="text-red-500"> *</span>}</Label>
    <input type={type} value={value ?? ''} placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)} className={inputCls} />
  </div>
);
const SelectField = ({ label, value, onChange, options, req = false }) => (
  <div>
    <Label>{label}{req && <span className="text-red-500"> *</span>}</Label>
    <select value={value ?? ''} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      <option value="">—</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  </div>
);
const COL_CLS = { 2: 'grid-cols-2', 3: 'grid-cols-3', 4: 'grid-cols-4' };
const Section = ({ title, children, cols = 2 }) => (
  <div className="space-y-2">
    <div className="text-[11px] font-bold uppercase tracking-wider text-amber-700 border-b border-amber-100 pb-1">{title}</div>
    <div className={`grid ${COL_CLS[cols] || 'grid-cols-2'} gap-3`}>{children}</div>
  </div>
);

const empty = () => ({
  referencia: '', tipo_imovel: 'Fazenda', tipo_amostra: 'Oferta de Mercado',
  denominacao: '', endereco_logradouro: '', bairro_localidade: '', municipio: 'Açailândia', uf: 'MA',
  area_m2: '',
  topografia: '', solo: '', recursos_hidricos: '', vegetacao: '', atividade_principal: '',
  lotacao_ua_ha: '', benfeitorias: '', sede_casa: '',
  valor_rs: '', fonte: '', data_coleta: hoje(), telefone_fonte: '',
  foto_url: '', planta_baixa_url: '', link_anuncio: '',
});

const ModalNovaAmostraRural = ({ open, onClose, onSalvar, referenciaSugerida }) => {
  const { toast } = useToast();
  const [form, setForm] = useState(empty());
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState('');

  useEffect(() => {
    if (open) setForm((f) => ({ ...empty(), referencia: referenciaSugerida || f.referencia }));
  }, [open, referenciaSugerida]);

  const set = useCallback((k, v) => setForm((f) => ({ ...f, [k]: v })), []);
  const areaM2 = num(form.area_m2);
  const ha = useMemo(() => m2ToHa(areaM2), [areaM2]);
  const alq = useMemo(() => m2ToAlq(areaM2), [areaM2]);
  const rsHa = useMemo(() => calcRsHa(form.valor_rs, areaM2), [form.valor_rs, areaM2]);

  const handleUpload = async (campo, file) => {
    if (!file) return;
    setUploading(campo);
    try {
      const res = await uploadAPI.uploadImage(file);
      const imgId = res?.id || res?.image_id || res?.imageId;
      set(campo, imgId ? uploadAPI.getImageUrl(imgId) : (res?.url || ''));
    } catch (e) {
      toast({ title: 'Falha no upload', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setUploading(''); }
  };

  const salvar = async () => {
    if (!form.referencia || !num(form.area_m2) || !num(form.valor_rs) || !form.data_coleta) {
      toast({ title: 'Preencha Referência, Área, Valor e Data', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...form, categoria: 'rural',
        area_m2: num(form.area_m2),
        lotacao_ua_ha: num(form.lotacao_ua_ha) || null,
        valor_rs: num(form.valor_rs),
      };
      const saved = await amostrasAPI.create(payload);
      toast({ title: 'Amostra rural cadastrada' });
      onSalvar?.(saved);
      onClose?.();
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose?.()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-700">
            <Wheat className="w-5 h-5" /> Nova Amostra — Imóvel Rural
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          <Section title="Identificação" cols={3}>
            <TextField label="Referência" value={form.referencia} onChange={(v) => set('referencia', v)} placeholder="RM-001" req />
            <SelectField label="Tipo de Imóvel" value={form.tipo_imovel} onChange={(v) => set('tipo_imovel', v)} options={TIPOS_RURAL} req />
            <SelectField label="Tipo da Amostra" value={form.tipo_amostra} onChange={(v) => set('tipo_amostra', v)} options={TIPO_AMOSTRA_RURAL} req />
          </Section>

          <Section title="Localização" cols={2}>
            <TextField label="Denominação (fazenda/sítio)" value={form.denominacao} onChange={(v) => set('denominacao', v)} placeholder="Fazenda Boa Vista" />
            <TextField label="Endereço/Logradouro" value={form.endereco_logradouro} onChange={(v) => set('endereco_logradouro', v)} placeholder="Rodovia BR-010, km 1413" />
            <TextField label="Bairro/Localidade" value={form.bairro_localidade} onChange={(v) => set('bairro_localidade', v)} placeholder="Gleba Pequiá Brejão" />
            <div className="grid grid-cols-2 gap-3">
              <TextField label="Município" value={form.municipio} onChange={(v) => set('municipio', v)} />
              <TextField label="UF" value={form.uf} onChange={(v) => set('uf', v)} />
            </div>
          </Section>

          <Section title="Área Rural" cols={3}>
            <TextField label="Área (m²)" type="number" value={form.area_m2} onChange={(v) => set('area_m2', v)} req />
            <div>
              <Label>Hectares (calculado)</Label>
              <div className="mt-1 px-3 py-2 text-sm font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded-lg">{fmtNum(ha, 4)} ha</div>
            </div>
            <div>
              <Label>Alqueires mineiros (calc.)</Label>
              <div className="mt-1 px-3 py-2 text-sm font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded-lg">{fmtNum(alq, 4)} alq</div>
            </div>
          </Section>

          <Section title="Características Rurais" cols={2}>
            <SelectField label="Topografia" value={form.topografia} onChange={(v) => set('topografia', v)} options={TOPOGRAFIA} />
            <SelectField label="Solo" value={form.solo} onChange={(v) => set('solo', v)} options={SOLO} />
            <SelectField label="Recursos Hídricos" value={form.recursos_hidricos} onChange={(v) => set('recursos_hidricos', v)} options={RECURSOS_HIDRICOS} />
            <SelectField label="Vegetação" value={form.vegetacao} onChange={(v) => set('vegetacao', v)} options={VEGETACAO} />
            <SelectField label="Atividade Principal" value={form.atividade_principal} onChange={(v) => set('atividade_principal', v)} options={ATIVIDADE_PRINCIPAL} />
            <TextField label="Lotação (UA/ha)" type="number" value={form.lotacao_ua_ha} onChange={(v) => set('lotacao_ua_ha', v)} />
            <SelectField label="Benfeitorias" value={form.benfeitorias} onChange={(v) => set('benfeitorias', v)} options={BENFEITORIAS_RURAL} />
            <SelectField label="Sede/Casa" value={form.sede_casa} onChange={(v) => set('sede_casa', v)} options={SEDE_CASA} />
          </Section>

          <Section title="Transação" cols={2}>
            <TextField label="Valor (R$)" type="number" value={form.valor_rs} onChange={(v) => set('valor_rs', v)} req />
            <div>
              <Label>R$/ha (calculado)</Label>
              <div className="mt-1 px-3 py-2 text-sm font-bold text-amber-700 bg-amber-50 border border-amber-200 rounded-lg">{fmtBRL(rsHa)}/ha</div>
            </div>
            <TextField label="Fonte" value={form.fonte} onChange={(v) => set('fonte', v)} />
            <TextField label="Data da Coleta" type="date" value={form.data_coleta} onChange={(v) => set('data_coleta', v)} req />
            <TextField label="Telefone da Fonte" value={form.telefone_fonte} onChange={(v) => set('telefone_fonte', v)} placeholder="(99) 99999-9999" />
            <TextField label="Link do Anúncio" value={form.link_anuncio} onChange={(v) => set('link_anuncio', v)} />
          </Section>

          <Section title="Mídia" cols={2}>
            {[['foto_url', 'Foto da Amostra'], ['planta_baixa_url', 'Planta Baixa/Croqui (PDF/Imagem)']].map(([campo, lbl]) => (
              <div key={campo}>
                <Label>{lbl}</Label>
                {form[campo] ? (
                  <div className="mt-1 flex items-center gap-2 px-3 py-2 text-xs border border-amber-200 bg-amber-50 rounded-lg">
                    <span className="truncate text-amber-700 flex-1">Arquivo anexado</span>
                    <button onClick={() => set(campo, '')} className="text-red-500"><X className="w-4 h-4" /></button>
                  </div>
                ) : (
                  <label className="mt-1 flex items-center justify-center gap-2 px-3 py-2 text-xs border border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-amber-500 text-gray-500">
                    {uploading === campo ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                    Enviar arquivo
                    <input type="file" className="hidden" accept="image/*,application/pdf"
                      onChange={(e) => handleUpload(campo, e.target.files?.[0])} />
                  </label>
                )}
              </div>
            ))}
          </Section>
        </div>

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={() => onClose?.()}>Cancelar</Button>
          <Button onClick={salvar} disabled={saving} className="bg-amber-600 hover:bg-amber-700 text-white">
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}Salvar Amostra
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ModalNovaAmostraRural;
