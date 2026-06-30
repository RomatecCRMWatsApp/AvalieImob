// @module topografia/GeoUrbanoUsucapiaoWizard — Wizard do serviço de Usucapião
// Extrajudicial (Prov. CNJ 149/2023). Componente PRÓPRIO (isolado do wizard de
// remembramento/desdobro/retificação), renderizado pelo GeoUrbanoWizard quando
// `tipo_servico === 'usucapiao'`. Reusa geoUrbanoAPI, autosave PATCH e preview de PDF.
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Plus, Trash2, FileText, Eye, Download, Send, ChevronRight, CheckCircle2, Clock,
} from 'lucide-react';
import { geoUrbanoAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import EtapaConcluidaBox from '../ptam/EtapaConcluidaBox';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const inp = 'w-full border rounded-lg px-3 py-2 text-sm';
const lbl = 'block text-xs font-medium text-gray-600 mb-1';

const PASSOS = ['Projeto', 'Posse', 'Provas', 'Partes', 'Anuências', 'Checklist', 'Geração', 'Entrega'];

const MODALIDADES = [
  { v: 'extraordinaria', l: 'Extraordinária (15/10 anos)' },
  { v: 'ordinaria', l: 'Ordinária (10/5 anos) — exige justo título' },
  { v: 'especial_urbana', l: 'Especial Urbana (5 anos / 250 m²)' },
  { v: 'especial_rural', l: 'Especial Rural (5 anos / 50 ha)' },
  { v: 'familiar', l: 'Familiar (2 anos / 250 m²)' },
  { v: 'coletiva', l: 'Coletiva (Estatuto da Cidade)' },
  { v: 'outra', l: 'Outra (cartório define)' },
];
const SITUACOES = [
  { v: 'nao_matriculado', l: 'Não matriculado / sem registro (pede abertura de matrícula)' },
  { v: 'matriculado_terceiro', l: 'Matriculado em nome de terceiro' },
  { v: 'transcricao_antiga', l: 'Transcrição antiga / parte de maior porção' },
];
const VINCULOS = [
  { v: 'proprio', l: 'Posse própria' },
  { v: 'de_cujus', l: 'De cujus (somada por sucessão)' },
  { v: 'cedente', l: 'Cedente' },
];
const TIPOS_PROVA = ['agua', 'luz', 'iptu', 'telefone', 'contrato', 'benfeitoria', 'comprovante_endereco', 'declaracao', 'foto', 'outro'];
const PAPEIS_PARTE = [
  { v: 'requerente', l: 'Requerente' },
  { v: 'conjuge', l: 'Cônjuge' },
  { v: 'advogado', l: 'Advogado(a)' },
  { v: 'herdeiro', l: 'Herdeiro(a)' },
  { v: 'testemunha', l: 'Testemunha' },
];
const TIPOS_CONFR = [
  { v: 'particular', l: 'Particular' },
  { v: 'via_publica', l: 'Via pública' },
  { v: 'area_publica', l: 'Área pública' },
];
const STATUS_ANUENCIA = ['pendente', 'assinada', 'recusada', 'notificado'];
const STATUS_CHK = ['pendente', 'anexado', 'dispensado'];
// chave da checklist → tipo de upload (quando há um direto)
const CHK_UPLOAD = {
  procuracao_oab: 'procuracao_oab', ata_notarial: 'ata_notarial_assinada', planta_memorial: 'planta_usucapiao',
  art_trt: 'art_trt', doc_requerente: 'doc_requerente', comprovante_endereco: 'doc_requerente',
  certidao_estado_civil: 'certidao_estado_civil', certidao_matricula: 'certidao_matricula',
  negativa_propriedade: 'negativa_propriedade', certidao_confrontante: 'certidao_confrontante',
  certidao_negativa_onus: 'certidao_negativa', iptu_valor_venal: 'iptu_usucapiao', provas_posse: 'prova_posse',
  certidao_distribuidor: 'certidao_distribuidor', justo_titulo: 'justo_titulo', certidao_obito: 'certidao_obito',
  formal_partilha: 'formal_partilha', certidao_herdeiros: 'doc_requerente', prova_posse_exclusiva: 'prova_posse',
  georef_sigef: 'planta_usucapiao', ccir: 'planta_usucapiao', car: 'planta_usucapiao',
};
const PECAS = [
  ['requerimento_usucapiao', 'Requerimento de Usucapião'],
  ['ata_notarial', 'Minuta da Ata Notarial'],
  ['memorial_descritivo', 'Memorial Descritivo'],
  ['edital_usucapiao', 'Edital'],
  ['dossie', 'Dossiê consolidado'],
  ['capa', 'Capa (Lupa Geo)'],
];

const fmtTipoProva = (t) => ({
  agua: 'Conta de água', luz: 'Conta de luz', iptu: 'IPTU', telefone: 'Telefone',
  contrato: 'Contrato', benfeitoria: 'Benfeitoria', comprovante_endereco: 'Comprovante de endereço',
  declaracao: 'Declaração', foto: 'Foto', outro: 'Outro',
}[t] || t);

export default function GeoUrbanoUsucapiaoWizard({ id }) {
  const nav = useNavigate();
  const { toast } = useToast();
  const [proj, setProj] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [valid, setValid] = useState(null);
  const [checklist, setChecklist] = useState([]);
  const [anuentes, setAnuentes] = useState([]);
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewBusy, setPreviewBusy] = useState(false);
  const previewRef = useRef('');
  const debounceRef = useRef(null);
  const dirtyRef = useRef(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const d = await geoUrbanoAPI.obter(id);
      setProj(d);
    } catch (e) {
      toast({ title: 'Erro ao carregar projeto', variant: 'destructive' });
    } finally { setLoading(false); }
  }, [id, toast]);

  useEffect(() => { carregar(); }, [carregar]);

  // payload editável persistido no PATCH (AtualizarProjetoBody aceita todos)
  const buildPayload = (p) => ({
    denominacao_imovel: p.denominacao_imovel, modalidade_usucapiao: p.modalidade_usucapiao,
    fundamento_legal: p.fundamento_legal, valor_atribuido: p.valor_atribuido,
    situacao_registral: p.situacao_registral, tema: p.tema, municipio: p.municipio, uf: p.uf,
    bairro: p.bairro, quadra: p.quadra, lote_resultante: p.lote_resultante, endereco: p.endereco,
    area_declarada_m2: p.area_declarada_m2, perimetro_m: p.perimetro_m,
    posse: p.posse, soma_posses: p.soma_posses, provas_posse: p.provas_posse,
    anuentes: p.anuentes, partes: p.partes, confrontantes: p.confrontantes, checklist: p.checklist,
    etapas_concluidas: p.etapas_concluidas, etapas_concluidas_em: p.etapas_concluidas_em,
  });

  const flush = useCallback(async (p) => {
    if (!p) return;
    try {
      setSaving(true);
      const d = await geoUrbanoAPI.atualizar(id, buildPayload(p));
      dirtyRef.current = false;
      // mantém completude/numero atualizados sem sobrescrever edição em curso
      setProj((cur) => (cur ? { ...cur, completude: d.completude, numero: d.numero || cur.numero } : cur));
    } catch (e) { /* silencioso — re-tenta na próxima edição */ } finally { setSaving(false); }
  }, [id]);

  // atualiza estado + agenda autosave (debounce)
  const upd = (partial) => {
    setProj((cur) => {
      const next = { ...cur, ...partial };
      dirtyRef.current = true;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => flush(next), 1200);
      return next;
    });
  };
  const updPosse = (partial) => upd({ posse: { ...(proj?.posse || {}), ...partial } });

  const flushNow = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (dirtyRef.current && proj) flush(proj);
  }, [flush, proj]);

  useEffect(() => () => flushNow(), [flushNow]);

  // validação ao vivo (modalidade / posse / soma / área)
  const recarregarValidacao = useCallback(async () => {
    try { setValid(await geoUrbanoAPI.usucapiaoValidacao(id)); } catch (e) { /* */ }
  }, [id]);
  const somaKey = JSON.stringify(proj?.soma_posses || []);
  const posseKey = JSON.stringify(proj?.posse || {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (proj) recarregarValidacao(); }, [proj?.modalidade_usucapiao, proj?.area_declarada_m2, somaKey, posseKey]);

  const recarregarChecklist = useCallback(async () => {
    try {
      const d = await geoUrbanoAPI.usucapiaoChecklist(id);
      setChecklist(d.checklist || []); setAnuentes(d.anuentes || []);
    } catch (e) { /* */ }
  }, [id]);

  // ── editores de listas embutidas ────────────────────────────────────────────
  const setLista = (campo, arr) => upd({ [campo]: arr });
  const addItem = (campo, item) => setLista(campo, [...(proj[campo] || []), item]);
  const updItem = (campo, i, partial) =>
    setLista(campo, (proj[campo] || []).map((x, j) => (j === i ? { ...x, ...partial } : x)));
  const rmItem = (campo, i) => setLista(campo, (proj[campo] || []).filter((_, j) => j !== i));

  const toggleEtapa = (idx, checked) => {
    const ec = { ...(proj.etapas_concluidas || {}), [idx]: checked };
    const em = { ...(proj.etapas_concluidas_em || {}), [idx]: checked ? new Date().toISOString() : null };
    upd({ etapas_concluidas: ec, etapas_concluidas_em: em });
  };

  // preview de PDF (blob → iframe)
  const carregarPreview = async (tipo) => {
    setPreviewBusy(true);
    try {
      const blob = await geoUrbanoAPI.documento(id, tipo, proj.tema);
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
      const url = URL.createObjectURL(blob);
      previewRef.current = url; setPreviewUrl(url);
    } catch (e) {
      toast({ title: 'Erro ao gerar a peça', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setPreviewBusy(false); }
  };
  useEffect(() => () => { if (previewRef.current) URL.revokeObjectURL(previewRef.current); }, []);

  const verBlob = async (promise, nome) => {
    const win = window.open('', '_blank');
    try {
      const blob = await promise;
      const url = URL.createObjectURL(blob);
      if (win) win.location.href = url; else window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      if (win) win.close();
      toast({ title: 'Erro ao abrir', description: nome || '', variant: 'destructive' });
    }
  };
  const baixarBlob = async (promise, nome) => {
    try {
      const blob = await promise;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = nome;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    } catch (e) { toast({ title: 'Erro ao baixar', variant: 'destructive' }); }
  };

  // upload genérico (provas / checklist)
  const enviarUpload = async (tipo, file, after) => {
    try {
      await geoUrbanoAPI.upload(id, tipo, file);
      toast({ title: 'Documento anexado ✓' });
      await carregar(); if (after) after();
    } catch (e) { toast({ title: 'Erro ao anexar', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
  };

  const irPasso = (n) => { flushNow(); setStep(n); if (n === 5) recarregarChecklist(); };

  const ehHerdeiro = useMemo(() =>
    (proj?.partes || []).some((x) => x.papel === 'herdeiro')
    || (proj?.soma_posses || []).some((x) => x.vinculo === 'de_cujus'), [proj]);
  const exigeJustoTitulo = proj?.modalidade_usucapiao === 'ordinaria';

  if (loading || !proj) return <div className="py-24"><BrandSpinner label="Carregando…" /></div>;

  const P = proj;
  const posse = P.posse || {};

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <header className="flex items-center gap-3 mb-5">
        <button onClick={() => { flushNow(); nav('/dashboard/topografia/geo-urbano'); }} className="p-2 rounded-lg hover:bg-gray-100">
          <ArrowLeft className="w-5 h-5" style={{ color: GREEN }} />
        </button>
        <div className="flex-1">
          <h1 className="text-lg font-bold leading-tight" style={{ color: GREEN }}>{P.denominacao_imovel || 'Usucapião'}</h1>
          <p className="text-xs text-gray-500">
            {P.numero || 'usucapião'} · Usucapião Extrajudicial · Etapa {step + 1} de {PASSOS.length}
            {saving ? ' · salvando…' : ' · salvo ✓'} · {P.completude || 0}% preenchido
          </p>
        </div>
      </header>

      {/* navegação por etapas */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {PASSOS.map((p, i) => (
          <button key={p} onClick={() => irPasso(i)}
            className={`text-xs px-2.5 py-1 rounded-full border ${i === step ? 'text-white' : 'text-gray-600 bg-white hover:bg-gray-50'}`}
            style={i === step ? { background: GREEN, borderColor: GREEN } : {}}>
            {(P.etapas_concluidas || {})[i] ? '✓ ' : ''}{i + 1}. {p}
          </button>
        ))}
      </div>
      <div className="h-1 bg-gray-100 rounded-full mb-6 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${((step + 1) / PASSOS.length) * 100}%`, background: GOLD }} />
      </div>

      {/* ── Passo 1: Projeto + validação ───────────────────────────────────── */}
      {step === 0 && (
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className={lbl}>Denominação do imóvel</label>
            <input className={inp} value={P.denominacao_imovel || ''} onChange={(e) => upd({ denominacao_imovel: e.target.value })} />
          </div>
          <div>
            <label className={lbl}>Modalidade</label>
            <select className={inp} value={P.modalidade_usucapiao || 'extraordinaria'} onChange={(e) => upd({ modalidade_usucapiao: e.target.value })}>
              {MODALIDADES.map((m) => <option key={m.v} value={m.v}>{m.l}</option>)}
            </select>
          </div>
          <div>
            <label className={lbl}>Situação registral</label>
            <select className={inp} value={P.situacao_registral || 'nao_matriculado'} onChange={(e) => upd({ situacao_registral: e.target.value })}>
              {SITUACOES.map((s) => <option key={s.v} value={s.v}>{s.l}</option>)}
            </select>
          </div>
          {P.modalidade_usucapiao === 'outra' && (
            <div className="sm:col-span-2">
              <label className={lbl}>Fundamento legal (texto livre)</label>
              <input className={inp} value={P.fundamento_legal || ''} onChange={(e) => upd({ fundamento_legal: e.target.value })}
                placeholder="Ex.: art. X da Lei Y" />
            </div>
          )}
          <div>
            <label className={lbl}>Endereço do imóvel</label>
            <input className={inp} value={P.endereco || ''} onChange={(e) => upd({ endereco: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div><label className={lbl}>Município</label><input className={inp} value={P.municipio || ''} onChange={(e) => upd({ municipio: e.target.value })} /></div>
            <div><label className={lbl}>UF</label><input className={inp} value={P.uf || ''} onChange={(e) => upd({ uf: e.target.value })} /></div>
          </div>
          <div><label className={lbl}>Área (m²)</label><input type="number" className={inp} value={P.area_declarada_m2 ?? ''} onChange={(e) => upd({ area_declarada_m2: e.target.value === '' ? null : Number(e.target.value) })} /></div>
          <div><label className={lbl}>Valor atribuído (R$)</label><input type="number" className={inp} value={P.valor_atribuido ?? ''} onChange={(e) => upd({ valor_atribuido: e.target.value === '' ? null : Number(e.target.value) })} /></div>
          <div>
            <label className={lbl}>Tema do PDF</label>
            <select className={inp} value={P.tema || 'prime_i'} onChange={(e) => upd({ tema: e.target.value })}>
              <option value="prime_i">Prime I — Elegante</option>
              <option value="prime_ii">Prime II — Editorial</option>
              <option value="tradicional">Tradicional</option>
            </select>
          </div>

          {/* painel de validação ao vivo */}
          {valid && (
            <div className="sm:col-span-2 rounded-xl border p-4 bg-gray-50">
              <h3 className="text-sm font-semibold mb-2" style={{ color: GREEN }}>Aferição (NBR 14.653 · Prov. CNJ 149/2023)</h3>
              <div className="grid sm:grid-cols-3 gap-3 text-xs">
                <div className={`rounded-lg p-2 border ${valid.prazo_ok ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'}`}>
                  <div className="font-semibold">Tempo de posse</div>
                  <div>{valid.anos_cobertos} ano(s) cobertos{valid.prazo_exigido ? ` / ${valid.prazo_exigido} exigidos` : ''}</div>
                  <div className={valid.prazo_ok ? 'text-emerald-700' : 'text-amber-700'}>
                    {valid.prazo_ok ? '✓ prazo atingido' : `faltam ${valid.faltam_anos} ano(s)`}
                  </div>
                </div>
                <div className={`rounded-lg p-2 border ${valid.area_ok ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'}`}>
                  <div className="font-semibold">Área</div>
                  <div>{valid.area_m2 != null ? `${Number(valid.area_m2).toLocaleString('pt-BR')} m²` : '—'}{valid.area_max ? ` / máx ${valid.area_max} m²` : (valid.area_max_ha ? ` / máx ${valid.area_max_ha} ha` : ' · sem limite')}</div>
                  <div className={valid.area_ok ? 'text-emerald-700' : 'text-amber-700'}>{valid.area_ok ? '✓ dentro do limite' : '⚠ excede o limite'}</div>
                </div>
                <div className={`rounded-lg p-2 border ${valid.justo_titulo_ok ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'}`}>
                  <div className="font-semibold">Justo título</div>
                  <div>{valid.exige_justo_titulo ? 'exigido (ordinária)' : 'dispensado'}</div>
                  <div className={valid.justo_titulo_ok ? 'text-emerald-700' : 'text-amber-700'}>{valid.justo_titulo_ok ? '✓ ok' : '⚠ informar na etapa Posse'}</div>
                </div>
              </div>
              {(valid.avisos || []).map((a, i) => (
                <p key={i} className="text-[11px] text-gray-500 mt-2">• {a}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Passo 2: Posse & Soma de posses ────────────────────────────────── */}
      {step === 1 && (
        <div className="space-y-5">
          <div className="grid sm:grid-cols-2 gap-4">
            <div><label className={lbl}>Início da posse (ano ou data)</label><input className={inp} value={posse.inicio || ''} onChange={(e) => updPosse({ inicio: e.target.value })} placeholder="Ex.: 2008" /></div>
            <div><label className={lbl}>Origem da posse</label><input className={inp} value={posse.origem || ''} onChange={(e) => updPosse({ origem: e.target.value })} placeholder="ocupação / cessão / compra verbal" /></div>
            <div className="sm:col-span-2"><label className={lbl}>Natureza da posse</label><input className={inp} value={posse.natureza || ''} onChange={(e) => updPosse({ natureza: e.target.value })} placeholder="mansa, pacífica, ininterrupta, com animus domini" /></div>
            <div><label className={lbl}>Benfeitorias</label><input className={inp} value={posse.benfeitorias || ''} onChange={(e) => updPosse({ benfeitorias: e.target.value })} placeholder="casa de alvenaria…" /></div>
            <div><label className={lbl}>Benfeitorias desde</label><input className={inp} value={posse.benfeitorias_data || ''} onChange={(e) => updPosse({ benfeitorias_data: e.target.value })} placeholder="Ex.: 2009" /></div>
            {exigeJustoTitulo && (
              <div className="sm:col-span-2"><label className={lbl}>Justo título (exigido na ordinária)</label><input className={inp} value={posse.justo_titulo || ''} onChange={(e) => updPosse({ justo_titulo: e.target.value })} placeholder="Cessão de direitos hereditários, fls. 12…" /></div>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Soma de posses (art. 1.243 CC)</h3>
              <button onClick={() => addItem('soma_posses', { possuidor_nome: '', vinculo: 'proprio', inicio: '', fim: '' })}
                className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar possuidor</button>
            </div>
            {(P.soma_posses || []).length === 0 && <p className="text-xs text-gray-400">Sem períodos. Use o início da posse acima, ou some os antecessores (caso herdeiro).</p>}
            <div className="space-y-2">
              {(P.soma_posses || []).map((sp, i) => (
                <div key={i} className="grid sm:grid-cols-12 gap-2 items-end border rounded-lg p-2">
                  <div className="sm:col-span-4"><label className={lbl}>Possuidor</label><input className={inp} value={sp.possuidor_nome || ''} onChange={(e) => updItem('soma_posses', i, { possuidor_nome: e.target.value })} /></div>
                  <div className="sm:col-span-3"><label className={lbl}>Vínculo</label><select className={inp} value={sp.vinculo || 'proprio'} onChange={(e) => updItem('soma_posses', i, { vinculo: e.target.value })}>{VINCULOS.map((v) => <option key={v.v} value={v.v}>{v.l}</option>)}</select></div>
                  <div className="sm:col-span-2"><label className={lbl}>Início</label><input className={inp} value={sp.inicio || ''} onChange={(e) => updItem('soma_posses', i, { inicio: e.target.value })} placeholder="2008" /></div>
                  <div className="sm:col-span-2"><label className={lbl}>Fim</label><input className={inp} value={sp.fim || ''} onChange={(e) => updItem('soma_posses', i, { fim: e.target.value })} placeholder="2018 / atual" /></div>
                  <div className="sm:col-span-1 flex justify-end"><button onClick={() => rmItem('soma_posses', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
                </div>
              ))}
            </div>
            {valid && (
              <p className={`text-xs mt-2 ${valid.prazo_ok ? 'text-emerald-700' : 'text-amber-700'}`}>
                {valid.anos_cobertos} ano(s) cobertos{valid.prazo_exigido ? ` de ${valid.prazo_exigido} exigidos` : ''} — {valid.prazo_ok ? 'prazo atingido ✓' : `faltam ${valid.faltam_anos}`}
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Passo 3: Provas (linha do tempo) ───────────────────────────────── */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Provas de posse (linha do tempo)</h3>
            <button onClick={() => addItem('provas_posse', { tipo: 'iptu', ano: '', descricao: '' })}
              className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar prova</button>
          </div>
          {(P.provas_posse || []).slice().sort((a, b) => String(a.ano).localeCompare(String(b.ano))).map((pv) => pv).length === 0 &&
            <p className="text-xs text-gray-400">Sem provas. Adicione contas de água/luz/IPTU, declarações e fotos por ano.</p>}
          <div className="space-y-2">
            {(P.provas_posse || []).map((pv, i) => (
              <div key={i} className="grid sm:grid-cols-12 gap-2 items-end border rounded-lg p-2">
                <div className="sm:col-span-3"><label className={lbl}>Tipo</label><select className={inp} value={pv.tipo || 'outro'} onChange={(e) => updItem('provas_posse', i, { tipo: e.target.value })}>{TIPOS_PROVA.map((t) => <option key={t} value={t}>{fmtTipoProva(t)}</option>)}</select></div>
                <div className="sm:col-span-2"><label className={lbl}>Ano</label><input className={inp} value={pv.ano || ''} onChange={(e) => updItem('provas_posse', i, { ano: e.target.value })} placeholder="2014" /></div>
                <div className="sm:col-span-6"><label className={lbl}>Descrição</label><input className={inp} value={pv.descricao || ''} onChange={(e) => updItem('provas_posse', i, { descricao: e.target.value })} /></div>
                <div className="sm:col-span-1 flex justify-end"><button onClick={() => rmItem('provas_posse', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
              </div>
            ))}
          </div>
          <div className="border-t pt-3">
            <label className={lbl}>Anexar arquivos de prova (PDF/imagem — vão ao dossiê)</label>
            <input type="file" multiple accept="application/pdf,image/*"
              onChange={(e) => { Array.from(e.target.files || []).forEach((f) => enviarUpload('prova_posse', f)); e.target.value = ''; }} />
            <p className="text-[11px] text-gray-400 mt-1">{(P.uploads?.prova_posse || []).length} arquivo(s) de prova anexado(s).</p>
          </div>
        </div>
      )}

      {/* ── Passo 4: Partes ────────────────────────────────────────────────── */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Partes (requerente, cônjuge, advogado, herdeiros, testemunhas)</h3>
            <button onClick={() => addItem('partes', { papel: 'requerente', tipo_pessoa: 'fisica', nome: '' })}
              className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar parte</button>
          </div>
          <div className="space-y-3">
            {(P.partes || []).map((pt, i) => (
              <div key={i} className="border rounded-lg p-3">
                <div className="grid sm:grid-cols-12 gap-2 items-end">
                  <div className="sm:col-span-3"><label className={lbl}>Papel</label><select className={inp} value={pt.papel || 'requerente'} onChange={(e) => updItem('partes', i, { papel: e.target.value })}>{PAPEIS_PARTE.map((p) => <option key={p.v} value={p.v}>{p.l}</option>)}</select></div>
                  <div className="sm:col-span-7"><label className={lbl}>Nome</label><input className={inp} value={pt.nome || pt.razao_social || ''} onChange={(e) => updItem('partes', i, { nome: e.target.value })} /></div>
                  <div className="sm:col-span-2 flex justify-end"><button onClick={() => rmItem('partes', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
                  <div className="sm:col-span-3"><label className={lbl}>CPF</label><input className={inp} value={pt.cpf || ''} onChange={(e) => updItem('partes', i, { cpf: e.target.value })} /></div>
                  <div className="sm:col-span-3"><label className={lbl}>RG</label><input className={inp} value={pt.rg || ''} onChange={(e) => updItem('partes', i, { rg: e.target.value })} /></div>
                  <div className="sm:col-span-3"><label className={lbl}>Estado civil</label><input className={inp} value={pt.estado_civil || ''} onChange={(e) => updItem('partes', i, { estado_civil: e.target.value })} /></div>
                  <div className="sm:col-span-3"><label className={lbl}>Profissão</label><input className={inp} value={pt.profissao || ''} onChange={(e) => updItem('partes', i, { profissao: e.target.value })} /></div>
                  {pt.papel === 'advogado' && (
                    <>
                      <div className="sm:col-span-3"><label className={lbl}>OAB</label><input className={inp} value={pt.oab || ''} onChange={(e) => updItem('partes', i, { oab: e.target.value })} placeholder="12345" /></div>
                      <div className="sm:col-span-2"><label className={lbl}>UF OAB</label><input className={inp} value={pt.uf_oab || ''} onChange={(e) => updItem('partes', i, { uf_oab: e.target.value })} placeholder="MA" /></div>
                    </>
                  )}
                  <div className="sm:col-span-6"><label className={lbl}>Endereço</label><input className={inp} value={pt.endereco || ''} onChange={(e) => updItem('partes', i, { endereco: e.target.value })} /></div>
                </div>
              </div>
            ))}
          </div>
          {(P.modalidade_usucapiao !== 'outra') && !(P.partes || []).some((x) => x.papel === 'advogado') && (
            <p className="text-xs text-amber-700">⚠ O usucapião extrajudicial exige advogado (art. 216-A). Adicione a parte "Advogado(a)".</p>
          )}
        </div>
      )}

      {/* ── Passo 5: Confrontantes & Anuências ─────────────────────────────── */}
      {step === 4 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Confrontantes & Anuências</h3>
            <button onClick={() => addItem('confrontantes', { lado: 'frente', confrontante: '', tipo: 'particular', medida_m: null, anuencia: { status: 'pendente' } })}
              className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar confrontante</button>
          </div>
          <p className="text-[11px] text-gray-500">Confrontantes particulares e o titular tabular anuem à planta/memorial. O silêncio do notificado vale como concordância (Lei 13.465/2017).</p>
          <div className="space-y-2">
            {(P.confrontantes || []).map((cf, i) => (
              <div key={i} className="grid sm:grid-cols-12 gap-2 items-end border rounded-lg p-2">
                <div className="sm:col-span-2"><label className={lbl}>Lado</label><input className={inp} value={cf.lado || ''} onChange={(e) => updItem('confrontantes', i, { lado: e.target.value })} placeholder="frente / fundo" /></div>
                <div className="sm:col-span-3"><label className={lbl}>Confrontante</label><input className={inp} value={cf.confrontante || ''} onChange={(e) => updItem('confrontantes', i, { confrontante: e.target.value })} /></div>
                <div className="sm:col-span-2"><label className={lbl}>Tipo</label><select className={inp} value={cf.tipo || 'particular'} onChange={(e) => updItem('confrontantes', i, { tipo: e.target.value })}>{TIPOS_CONFR.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}</select></div>
                <div className="sm:col-span-2"><label className={lbl}>Medida (m)</label><input type="number" className={inp} value={cf.medida_m ?? ''} onChange={(e) => updItem('confrontantes', i, { medida_m: e.target.value === '' ? null : Number(e.target.value) })} /></div>
                <div className="sm:col-span-2"><label className={lbl}>Anuência</label><select className={inp} value={cf.anuencia?.status || 'pendente'} onChange={(e) => updItem('confrontantes', i, { anuencia: { ...(cf.anuencia || {}), status: e.target.value } })}>{STATUS_ANUENCIA.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
                <div className="sm:col-span-1 flex justify-end"><button onClick={() => rmItem('confrontantes', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
                <div className="sm:col-span-12 flex flex-wrap gap-2">
                  <button onClick={() => verBlob(geoUrbanoAPI.usucapiaoAnuenciaPdf(id, cf.confrontante, 'declaracao', P.tema), 'Declaração de anuência')}
                    disabled={!cf.confrontante} className="text-[11px] inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50 disabled:opacity-40"><FileText className="w-3 h-3" /> Declaração de anuência</button>
                  <button onClick={() => verBlob(geoUrbanoAPI.usucapiaoAnuenciaPdf(id, cf.confrontante, 'notificacao', P.tema), 'Notificação')}
                    disabled={!cf.confrontante} className="text-[11px] inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50 disabled:opacity-40"><FileText className="w-3 h-3" /> Notificação</button>
                </div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-amber-700">A coleta por WhatsApp (assinatura desenhada) chega na próxima fase; por ora, baixe a declaração e registre a anuência presencial.</p>
        </div>
      )}

      {/* ── Passo 6: Checklist A-G ─────────────────────────────────────────── */}
      {step === 5 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Checklist de documentos (Prov. CNJ 149/2023)</h3>
            <button onClick={recarregarChecklist} className="text-xs px-2 py-1 rounded border hover:bg-gray-50">Recarregar</button>
          </div>
          {checklist.length === 0 && <p className="text-xs text-gray-400">Carregando checklist… (ajusta-se à modalidade {ehHerdeiro ? '· caso herdeiro' : ''})</p>}
          {['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((bloco) => {
            const itens = checklist.filter((c) => c.bloco === bloco);
            if (!itens.length) return null;
            return (
              <div key={bloco} className="border rounded-lg p-3">
                <div className="text-xs font-bold text-gray-500 mb-2">Bloco {bloco}</div>
                <div className="space-y-1.5">
                  {itens.map((it) => {
                    const cur = (P.checklist || []).find((x) => x.chave === it.chave) || it;
                    const tipoUp = CHK_UPLOAD[it.chave];
                    const setStatus = (status) => {
                      const lista = [...(P.checklist || [])];
                      const j = lista.findIndex((x) => x.chave === it.chave);
                      if (j >= 0) lista[j] = { ...lista[j], status }; else lista.push({ ...it, status });
                      upd({ checklist: lista });
                    };
                    return (
                      <div key={it.chave} className="flex items-center gap-2 text-sm">
                        <span className={`w-2 h-2 rounded-full ${cur.status === 'anexado' ? 'bg-emerald-500' : cur.status === 'dispensado' ? 'bg-gray-300' : 'bg-amber-400'}`} />
                        <span className="flex-1">{it.label}{it.obrigatorio ? '' : ' (opcional)'}</span>
                        {tipoUp && (
                          <label className="text-[11px] px-2 py-0.5 rounded border hover:bg-gray-50 cursor-pointer">
                            anexar
                            <input type="file" className="hidden" accept="application/pdf,image/*"
                              onChange={(e) => { const f = e.target.files?.[0]; if (f) enviarUpload(tipoUp, f, () => setStatus('anexado')); e.target.value = ''; }} />
                          </label>
                        )}
                        <select className="text-[11px] border rounded px-1 py-0.5" value={cur.status || 'pendente'} onChange={(e) => setStatus(e.target.value)}>
                          {STATUS_CHK.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Passo 7: Geração (preview) ─────────────────────────────────────── */}
      {step === 6 && (
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="space-y-2">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Peças geradas</h3>
            {PECAS.map(([tipo, label]) => (
              <div key={tipo} className="flex items-center justify-between border rounded-lg px-3 py-2">
                <span className="text-sm">{label}</span>
                <div className="flex gap-1">
                  <button onClick={() => carregarPreview(tipo)} className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Eye className="w-3 h-3" /> Prévia</button>
                  <button onClick={() => verBlob(geoUrbanoAPI.documento(id, tipo, P.tema), label)} className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><FileText className="w-3 h-3" /> Abrir</button>
                </div>
              </div>
            ))}
          </div>
          <div className="border rounded-lg overflow-hidden bg-gray-50 min-h-[420px]">
            {previewBusy ? <div className="py-24"><BrandSpinner label="Gerando…" /></div>
              : previewUrl ? <iframe title="preview" src={`${previewUrl}#toolbar=1`} className="w-full h-[560px]" />
                : <div className="flex items-center justify-center h-[420px] text-sm text-gray-400">Clique em "Prévia" para ver a peça aqui.</div>}
          </div>
        </div>
      )}

      {/* ── Passo 8: Entrega ───────────────────────────────────────────────── */}
      {step === 7 && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Entrega — Dossiê consolidado</h3>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => verBlob(geoUrbanoAPI.documento(id, 'dossie', P.tema), 'Dossiê')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white" style={{ background: GREEN }}><Eye className="w-4 h-4" /> Ver Dossiê</button>
            <button onClick={() => baixarBlob(geoUrbanoAPI.documento(id, 'dossie', P.tema), `dossie_${P.numero || id}.pdf`)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border hover:bg-gray-50"><Download className="w-4 h-4" /> Baixar Dossiê</button>
          </div>
          <EnviarWhatsapp id={id} nome={P.denominacao_imovel} toast={toast} />
          <p className="text-[11px] text-gray-500">O dossiê sai na ordem de protocolo do art. 216-A (Requerimento → Ata → Planta/Memorial → certidões → anuências → provas → herdeiro → edital). A assinatura ICP do RT e as anuências por WhatsApp chegam na próxima fase.</p>
        </div>
      )}

      <EtapaConcluidaBox stepIndex={step} label={PASSOS[step]} form={P} onToggle={toggleEtapa} entidade="projeto" />

      <div className="flex items-center justify-between mt-6">
        <button onClick={() => irPasso(Math.max(0, step - 1))} disabled={step === 0}
          className="px-4 py-2 rounded-lg text-sm border disabled:opacity-40">Voltar</button>
        {step < PASSOS.length - 1 && (
          <button onClick={() => irPasso(step + 1)}
            className="inline-flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-semibold text-white" style={{ background: GREEN }}>
            Avançar <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

// Bloco de envio do dossiê por WhatsApp (reusa geoUrbanoAPI.enviarWhatsapp)
function EnviarWhatsapp({ id, nome, toast }) {
  const [peca, setPeca] = useState('dossie');
  const [fone, setFone] = useState('');
  const [busy, setBusy] = useState(false);
  const enviar = async () => {
    const f = fone.replace(/\D/g, '');
    if (f.length < 10) { toast({ title: 'Informe um WhatsApp válido (55 + DDD + número)', variant: 'destructive' }); return; }
    setBusy(true);
    try {
      await geoUrbanoAPI.enviarWhatsapp(id, { peca, telefone: f });
      toast({ title: 'Enviado pelo WhatsApp ✓', description: f });
    } catch (e) { toast({ title: 'Erro ao enviar', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div className="rounded-lg border p-3 bg-gray-50">
      <div className="text-xs font-semibold mb-2" style={{ color: GREEN }}>Enviar por WhatsApp</div>
      <div className="flex flex-wrap items-end gap-2">
        <div><label className={lbl}>Peça</label>
          <select className="border rounded-lg px-2.5 py-2 text-sm" value={peca} onChange={(e) => setPeca(e.target.value)}>
            {PECAS.filter(([t]) => t !== 'capa').map(([t, l]) => <option key={t} value={t}>{l}</option>)}
          </select>
        </div>
        <div className="flex-1 min-w-[180px]"><label className={lbl}>WhatsApp</label>
          <input className="w-full border rounded-lg px-2.5 py-2 text-sm" placeholder="55 + DDD + número" value={fone} onChange={(e) => setFone(e.target.value)} />
        </div>
        <button onClick={enviar} disabled={busy}
          className="inline-flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-semibold text-white" style={{ background: GREEN }}>
          <Send className="w-4 h-4" /> {busy ? 'Enviando…' : 'Enviar'}
        </button>
      </div>
    </div>
  );
}
