// @module ptam/steps/StepResultado — Step 11: Resultado da Avaliação (valor unitário, total, intervalo, validade)
import React, { useCallback, useEffect, useState } from 'react';
import { Sigma, Link2, Unlink, Loader2, AlertTriangle } from 'lucide-react';
import { Input } from '../../../ui/input';
import { Button } from '../../../ui/button';
import { useToast } from '../../../../hooks/use-toast';
import { inferenciaAPI } from '../../../../lib/api';
import { Field, SectionHeader, StatBox } from '../shared/primitives';
import { isRural } from '../shared/RuralDocSection';
import { M2_PER_HA, fmtBR } from '@/utils/areaConversao';

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

// Tratamento CIENTÍFICO: em vez de digitar o valor, o laudo puxa de um modelo de
// regressão HOMOLOGADO (menu Laudos ▸ Tratamento Científico). É o caminho do Grau III.
const VinculoInferencia = ({ form, setForm }) => {
  const { toast } = useToast();
  const [modelos, setModelos] = useState([]);
  const [sel, setSel] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const vinculado = form.inferencia_modelo_id;
  const snap = form.inferencia_snapshot || null;
  const enq = snap?.enquadramento || {};

  const load = useCallback(async () => {
    if (!form.id) return;
    try {
      const d = await inferenciaAPI.modelosDoPtam(form.id);
      setModelos(Array.isArray(d?.modelos) ? d.modelos : []);
    } catch { /* sem modelos ainda — o bloco só mostra o caminho */ }
  }, [form.id]);
  useEffect(() => { load(); }, [load]);

  const vincular = async () => {
    if (!sel) return;
    setOcupado(true);
    try {
      const r = await inferenciaAPI.vincularPtam(sel, form.id);
      setForm((f) => ({ ...f, ...r.valores, inferencia_modelo_id: sel }));
      toast({ title: 'Laudo alimentado pela regressão',
              description: 'Valor, intervalo e graus vieram do modelo homologado.' });
    } catch (e) {
      toast({ title: 'Não foi possível vincular', description: e.response?.data?.detail,
              variant: 'destructive' });
    } finally { setOcupado(false); }
  };

  const desvincular = async () => {
    setOcupado(true);
    try {
      await inferenciaAPI.desvincularPtam(form.id);
      setForm((f) => ({ ...f, inferencia_modelo_id: null, inferencia_snapshot: null }));
      toast({ title: 'Voltou ao tratamento por fatores' });
    } catch (e) {
      toast({ title: 'Erro ao desvincular', description: e.response?.data?.detail,
              variant: 'destructive' });
    } finally { setOcupado(false); }
  };

  return (
    <div className="mb-6 rounded-xl border p-4"
         style={{ borderColor: vinculado ? '#0C3320' : '#E5E7EB',
                  background: vinculado ? '#F0FDF4' : '#FFFFFF' }}>
      <div className="flex items-center gap-2 mb-2">
        <Sigma className="w-4 h-4" style={{ color: '#C9A84C' }} />
        <span className="text-xs font-bold uppercase tracking-wide text-gray-600">
          Tratamento científico (inferência estatística)
        </span>
      </div>

      {vinculado ? (
        <>
          <p className="text-sm text-gray-700">
            O valor deste laudo vem do modelo <strong>{snap?.nome || 'homologado'}</strong>
            {snap?.versao ? ` (v${snap.versao})` : ''} — regressão sobre{' '}
            {snap?.resultado?.n ?? '—'} dados de mercado.
          </p>
          <div className="flex flex-wrap gap-2 mt-2 mb-3">
            <span className="text-[11px] font-bold text-white px-2 py-0.5 rounded"
                  style={{ background: enq.grau_fundamentacao === 'III' ? '#059669' : '#D97706' }}>
              Fundamentação {enq.grau_fundamentacao || '—'}
            </span>
            <span className="text-[11px] font-bold text-white px-2 py-0.5 rounded"
                  style={{ background: enq.grau_precisao === 'III' ? '#059669' : '#D97706' }}>
              Precisão {enq.grau_precisao || '—'}
            </span>
          </div>
          <p className="text-[11px] text-gray-500 mb-3">
            Os campos abaixo foram preenchidos pela regressão, e o laudo passa a trazer as
            seções de amostra, pressupostos, gráficos e enquadramento. Os números ficam
            congelados neste laudo mesmo que o modelo seja versionado depois.
          </p>
          <Button size="sm" variant="outline" onClick={desvincular} disabled={ocupado}>
            {ocupado ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                     : <Unlink className="w-4 h-4 mr-2" />}
            Voltar ao tratamento por fatores
          </Button>
        </>
      ) : (
        <>
          <p className="text-sm text-gray-600 mb-3">
            Em vez de informar o valor à mão, você pode puxá-lo de um modelo de regressão
            homologado — é o caminho que sustenta o <strong>Grau III</strong> em perícia,
            desapropriação e servidão.
          </p>
          {modelos.length === 0 ? (
            <p className="text-xs text-amber-700 flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>
                Nenhum modelo homologado ainda. Monte em <strong>Laudos ▸ Tratamento
                Científico</strong> e homologue para poder usar aqui.
              </span>
            </p>
          ) : (
            <div className="flex flex-wrap items-end gap-2">
              <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg min-w-[260px]"
                      value={sel} onChange={(e) => setSel(e.target.value)}>
                <option value="">Selecione o modelo homologado…</option>
                {modelos.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nome} (v{m.versao})
                    {m.enquadramento?.grau_fundamentacao
                      ? ` — Grau ${m.enquadramento.grau_fundamentacao}` : ''}
                  </option>
                ))}
              </select>
              <Button size="sm" onClick={vincular} disabled={!sel || ocupado}
                      style={{ background: '#0C3320' }} className="text-white">
                {ocupado ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                         : <Link2 className="w-4 h-4 mr-2" />}
                Usar no laudo
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export const StepResultado = ({ form, setForm }) => {
  const val = Number(form.resultado_valor_total || 0);
  const inf = val * 0.85;
  const sup = val * 1.15;
  // Usa area_a_considerar como prioridade; cai em construida → terreno → property_area_sqm
  const area = Number(
    form.imovel_area_a_considerar ||
    form.imovel_area_construida ||
    form.imovel_area_terreno ||
    form.property_area_sqm || 0
  );
  const vuCalc = area > 0 ? val / area : 0;
  // Rural: valor unitário em R$/ha (R$/m² × 10.000) e área em ha como grandeza principal.
  const rural = isRural(form.property_type);
  const vuM2 = Number(form.resultado_valor_unitario || vuCalc);
  const areaHa = area / M2_PER_HA;

  return (
    <div>
      <SectionHeader
        title="11. Resultado da Avaliação"
        subtitle="Preencha ou confirme o valor de avaliação do imóvel."
      />

      <VinculoInferencia form={form} setForm={setForm} />

      {val > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {rural ? (
            <>
              <StatBox label="Valor Unitário (R$/ha)" value={fmtBRL(vuM2 * M2_PER_HA)} unit={`${fmtBRL(vuM2)}/m²`} />
              <StatBox label="Valor Total" value={fmtBRL(val)} />
              <StatBox label="Área Considerada (ha)" value={fmtBR(areaHa, 4)} unit={`${area.toLocaleString('pt-BR')} m²`} />
            </>
          ) : (
            <>
              <StatBox label="Valor Unitário (R$/m²)" value={fmtBRL(vuM2)} />
              <StatBox label="Valor Total" value={fmtBRL(val)} />
              <StatBox label="Área Considerada (m²)" value={area || '—'} unit="m²" />
            </>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor Unitário (R$/m²)">
          <Input
            type="number" step="0.01"
            value={form.resultado_valor_unitario}
            onChange={(e) => setForm({ ...form, resultado_valor_unitario: Number(e.target.value) })}
            placeholder="0,00"
          />
          {rural && Number(form.resultado_valor_unitario) > 0 && (
            <p className="mt-1 text-xs text-emerald-600 font-medium">
              = {fmtBRL(Number(form.resultado_valor_unitario) * M2_PER_HA)}/ha
            </p>
          )}
        </Field>
        <Field label="Valor Total (R$)">
          <Input
            type="number" step="0.01"
            value={form.resultado_valor_total}
            onChange={(e) => {
              const v = Number(e.target.value);
              setForm({ ...form, resultado_valor_total: v, total_indemnity: v });
            }}
            placeholder="0,00"
          />
        </Field>
        <Field label="Intervalo Inferior (R$)">
          <Input
            type="number" step="0.01"
            value={form.resultado_intervalo_inf || inf}
            onChange={(e) => setForm({ ...form, resultado_intervalo_inf: Number(e.target.value) })}
            placeholder="R$ automático (−15%)"
          />
        </Field>
        <Field label="Intervalo Superior (R$)">
          <Input
            type="number" step="0.01"
            value={form.resultado_intervalo_sup || sup}
            onChange={(e) => setForm({ ...form, resultado_intervalo_sup: Number(e.target.value) })}
            placeholder="R$ automático (+15%)"
          />
        </Field>
        <Field label="Campo de Arbítrio — mínimo (R$)">
          <Input
            type="number" step="0.01"
            value={form.campo_arbitrio_min || inf}
            onChange={(e) => setForm({ ...form, campo_arbitrio_min: Number(e.target.value) })}
            placeholder="−15% do valor"
          />
        </Field>
        <Field label="Campo de Arbítrio — máximo (R$)">
          <Input
            type="number" step="0.01"
            value={form.campo_arbitrio_max || sup}
            onChange={(e) => setForm({ ...form, campo_arbitrio_max: Number(e.target.value) })}
            placeholder="+15% do valor"
          />
        </Field>
        <Field label="Grau de Precisão (NBR 14653-1 item 9)">
          <select
            value={form.grau_precisao || 'I'}
            onChange={(e) => setForm({ ...form, grau_precisao: e.target.value })}
            className="w-full h-9 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="I">Grau I</option>
            <option value="II">Grau II</option>
            <option value="III">Grau III</option>
          </select>
        </Field>
        <Field label="Prazo de validade do laudo (meses)">
          <Input
            type="number" min="1" max="24"
            value={form.prazo_validade_meses || 6}
            onChange={(e) => setForm({ ...form, prazo_validade_meses: Number(e.target.value) })}
          />
        </Field>
        <Field label="Data de referência da avaliação">
          <Input
            type="date"
            value={form.resultado_data_referencia || ''}
            onChange={(e) => setForm({ ...form, resultado_data_referencia: e.target.value })}
          />
        </Field>
        <Field label="Validade do laudo (data)">
          <Input
            type="date"
            value={form.resultado_prazo_validade || ''}
            onChange={(e) => setForm({ ...form, resultado_prazo_validade: e.target.value })}
          />
        </Field>
        <Field label="Valor total por extenso" full>
          <Input
            value={form.total_indemnity_words || ''}
            onChange={(e) => setForm({ ...form, total_indemnity_words: e.target.value })}
            placeholder="Ex: Um milhão, duzentos e cinquenta mil reais"
          />
        </Field>
      </div>

      {val > 0 && (
        <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
          <div className="text-xs text-emerald-700 uppercase tracking-wider mb-2">Intervalo de valores sugerido (±15%)</div>
          <div className="flex items-center gap-6 text-sm text-emerald-900">
            <span className="font-medium">Mínimo: {fmtBRL(inf)}</span>
            <span className="text-gray-400">•</span>
            <span className="font-bold text-lg">{fmtBRL(val)}</span>
            <span className="text-gray-400">•</span>
            <span className="font-medium">Máximo: {fmtBRL(sup)}</span>
          </div>
        </div>
      )}
    </div>
  );
};
