// @module topografia/GeorrefUrbanoWizard — Fase 6: Georreferenciamento de lote
// urbano (localização e situação). Wizard PRÓPRIO de 6 etapas (o de 8+ etapas dos
// demais serviços não se aplica): serviço de campo puro, composição do dossiê
// montada pelo usuário. Isolado do GeoUrbanoWizard.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ChevronLeft, ChevronRight, Upload, Trash2, FileText, Eye,
  MapPin, CheckCircle2, AlertTriangle, Plus, Image as ImageIcon, Link2, Sparkles,
} from 'lucide-react';
import { geoUrbanoAPI, perfilAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const PASSOS = ['Identificação', 'Composição', 'Uploads', 'Coordenadas', 'Situação & Quadra', 'ART & Geração'];

const abrirBlob = async (apiPromise, toast, tipoMime = 'application/pdf') => {
  const win = window.open('', '_blank');
  try {
    const blob = await apiPromise;
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: tipoMime }));
    if (win) win.location.href = url; else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    if (win) win.close();
    const d = e?.response?.data;
    toast({ title: 'Não foi possível gerar', description: (d?.detail?.msg || d?.detail || '').toString().slice(0, 140), variant: 'destructive' });
  }
};

const Field = ({ label, children, span }) => (
  <div className={span ? 'sm:col-span-2' : ''}>
    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
    {children}
  </div>
);
const inp = 'w-full border rounded-lg px-2.5 py-1.5 text-sm bg-white';

export default function GeorrefUrbanoWizard() {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const [proj, setProj] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(0);
  const [opcoes, setOpcoes] = useState(null);
  const [comp, setComp] = useState(null);        // resolver_composicao
  const [valid, setValid] = useState(null);      // validar
  const [capaUrl, setCapaUrl] = useState(null);
  const projRef = useRef(null);
  const saveT = useRef(null);

  const carregar = useCallback(async () => {
    try {
      const [p, o] = await Promise.all([geoUrbanoAPI.obter(id), geoUrbanoAPI.georrefOpcoes()]);
      setProj(p); projRef.current = p; setOpcoes(o);
      geoUrbanoAPI.georrefComposicaoPreview(id).then(setComp).catch(() => {});
    } catch (e) {
      toast({ title: 'Erro ao carregar projeto', variant: 'destructive' });
    } finally { setLoading(false); }
  }, [id, toast]);
  useEffect(() => { carregar(); }, [carregar]);

  // patch imediato (selects/toggles) — atualiza estado local + servidor
  const patch = useCallback(async (campos) => {
    setProj((p) => { const np = { ...p, ...campos }; projRef.current = np; return np; });
    try { await geoUrbanoAPI.atualizar(id, campos); } catch { /* best-effort */ }
  }, [id]);
  // patch debounced (texto)
  const patchLento = useCallback((campos) => {
    setProj((p) => { const np = { ...p, ...campos }; projRef.current = np; return np; });
    clearTimeout(saveT.current);
    saveT.current = setTimeout(() => { geoUrbanoAPI.atualizar(id, campos).catch(() => {}); }, 900);
  }, [id]);

  const recomporPreview = useCallback(() => {
    geoUrbanoAPI.georrefComposicaoPreview(id).then(setComp).catch(() => {});
  }, [id]);

  if (loading) return <div className="py-24"><BrandSpinner label="Carregando projeto…" /></div>;
  if (!proj) return null;
  const passo = PASSOS[step];

  // ── handlers de composição ──
  const setPreset = (preset) => geoUrbanoAPI.georrefComposicao(id, { preset }).then((r) => { setComp(r); patch({ composicao: { ...(proj.composicao || {}), preset, pecas: undefined } }); });
  const togglePeca = (chave, ligada) => {
    const pecas = {}; (comp?.pecas || []).forEach((p) => { pecas[p.chave] = p.ligada; });
    pecas[chave] = ligada;
    geoUrbanoAPI.georrefComposicao(id, { pecas }).then(setComp);
  };
  const setDefinicaoCapa = (definicao_capa) => geoUrbanoAPI.georrefComposicao(id, { definicao_capa }).then(setComp);
  const toggleMemorial = (cod) => {
    const sel = new Set(proj.memoriais_selecionados || []);
    sel.has(cod) ? sel.delete(cod) : sel.add(cod);
    patch({ memoriais_selecionados: [...sel] }).then(recomporPreview);
  };
  // requerente (proprietário) — vive em partes[]; a extração do ART preenche isto
  const pj = proj.proprietario_natureza === 'pj';
  const requerente = (proj.partes || []).find((p) => p && p.papel === 'requerente') || {};
  const setRequerente = (campos) => {
    const partes = [...(proj.partes || [])];
    const i = partes.findIndex((p) => p.papel === 'requerente');
    const base = i >= 0 ? partes[i] : { id: `req-${Date.now()}`, papel: 'requerente' };
    const novo = { ...base, tipo_pessoa: pj ? 'juridica' : 'fisica', ...campos };
    if (i >= 0) partes[i] = novo; else partes.push(novo);
    patchLento({ partes });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <button onClick={() => nav('/dashboard/topografia/geo-urbano')} className="text-sm text-gray-500 hover:text-gray-700 mb-3 inline-flex items-center gap-1">
        <ChevronLeft className="w-4 h-4" /> Projetos
      </button>
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: GREEN }}>
          <MapPin className="w-5 h-5" style={{ color: GOLD }} />
        </div>
        <div>
          <h1 className="text-lg font-bold" style={{ color: GREEN }}>{proj.denominacao_imovel || 'Sem denominação'}</h1>
          <p className="text-xs text-gray-500">{proj.numero} · Georref. de lote urbano · Etapa {step + 1} de {PASSOS.length}</p>
        </div>
      </div>

      {/* chips de etapas */}
      <div className="flex flex-wrap gap-1.5 my-3">
        {PASSOS.map((p, i) => (
          <button key={p} onClick={() => setStep(i)}
            className={`text-xs px-2.5 py-1 rounded-full border ${i === step ? 'text-white' : 'text-gray-600 bg-white'}`}
            style={i === step ? { background: GREEN, borderColor: GREEN } : {}}>{i + 1}. {p}</button>
        ))}
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden mb-5">
        <div className="h-full rounded-full" style={{ width: `${((step + 1) / PASSOS.length) * 100}%`, background: GOLD }} />
      </div>

      {passo === 'Identificação' && (
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Denominação do imóvel" span>
            <input className={inp} value={proj.denominacao_imovel || ''} onChange={(e) => patchLento({ denominacao_imovel: e.target.value })} />
          </Field>
          <Field label="Finalidade">
            <select className={inp} value={proj.finalidade || ''} onChange={(e) => patch({ finalidade: e.target.value })}>
              {(opcoes?.finalidades || []).map((o) => <option key={o.codigo} value={o.codigo}>{o.label}</option>)}
            </select>
          </Field>
          {proj.finalidade === 'financiamento_bancario' && (
            <Field label="Instituição financeira">
              <input list="bancos" className={inp} value={proj.instituicao_financeira || ''} onChange={(e) => patchLento({ instituicao_financeira: e.target.value })} />
              <datalist id="bancos">{(opcoes?.instituicoes || []).map((b) => <option key={b} value={b} />)}</datalist>
            </Field>
          )}
          <Field label="Natureza do proprietário">
            <select className={inp} value={proj.proprietario_natureza || 'pf'} onChange={(e) => patch({ proprietario_natureza: e.target.value })}>
              <option value="pf">Pessoa Física</option>
              <option value="pj">Pessoa Jurídica</option>
              <option value="ambos">Ambos</option>
            </select>
          </Field>
          <Field label={pj ? 'Razão social (requerente)' : 'Nome do requerente'}>
            <input className={inp} value={requerente.razao_social || requerente.nome || ''}
              onChange={(e) => setRequerente(pj ? { razao_social: e.target.value } : { nome: e.target.value })} />
          </Field>
          <Field label={pj ? 'CNPJ do requerente' : 'CPF do requerente'}>
            <input className={inp} value={requerente.cnpj || requerente.cpf || ''}
              onChange={(e) => setRequerente(pj ? { cnpj: e.target.value } : { cpf: e.target.value })} />
          </Field>
          <Field label="Endereço do requerente" span>
            <input className={inp} value={requerente.endereco || ''} placeholder="Rua, nº, bairro, cidade - UF, CEP"
              onChange={(e) => setRequerente({ endereco: e.target.value })} />
          </Field>
          <Field label="Telefone / WhatsApp do requerente">
            <input className={inp} value={requerente.telefone || ''}
              onChange={(e) => setRequerente({ telefone: e.target.value })} />
          </Field>
          <Field label="E-mail do requerente">
            <input className={inp} value={requerente.email || ''}
              onChange={(e) => setRequerente({ email: e.target.value })} />
          </Field>
          <Field label="Bairro / Loteamento"><input className={inp} value={proj.loteamento || ''} onChange={(e) => patchLento({ loteamento: e.target.value, bairro: e.target.value })} /></Field>
          <Field label="Logradouro (Rua)"><input className={inp} value={proj.endereco || ''} onChange={(e) => patchLento({ endereco: e.target.value })} /></Field>
          <Field label="Quadra"><input className={inp} value={proj.quadra || ''} onChange={(e) => patchLento({ quadra: e.target.value })} /></Field>
          <Field label="Lote"><input className={inp} value={proj.lote_resultante || ''} onChange={(e) => patchLento({ lote_resultante: e.target.value })} /></Field>
          <Field label="Município"><input className={inp} value={proj.municipio || ''} onChange={(e) => patchLento({ municipio: e.target.value })} /></Field>
          <Field label="UF"><input className={inp} maxLength={2} value={proj.uf || ''} onChange={(e) => patchLento({ uf: e.target.value.toUpperCase() })} /></Field>
          <Field label="CIM (base)"><input className={inp} value={proj.cmi_resultante || ''} onChange={(e) => patchLento({ cmi_resultante: e.target.value })} placeholder="046.0004.0020.0001" /></Field>
          <Field label="Controle CIM"><input className={inp} value={proj.cmi_controle || ''} onChange={(e) => patchLento({ cmi_controle: e.target.value })} placeholder="201" /></Field>
          <Field label="Matrícula (opcional)"><input className={inp} value={proj.matricula_numero || ''} onChange={(e) => patchLento({ matricula_numero: e.target.value })} /></Field>
          <Field label="Área declarada — matrícula/IPTU (m²)"><input type="number" className={inp} value={proj.area_declarada || ''} onChange={(e) => patchLento({ area_declarada: parseFloat(e.target.value) || null })} /></Field>
          <div className="sm:col-span-2 rounded-lg border bg-gray-50 p-3">
            <div className="text-xs font-semibold mb-2" style={{ color: GREEN }}>Levantamento (metodologia)</div>
            <div className="grid sm:grid-cols-3 gap-2">
              {[['equipamento', 'Equipamento'], ['metodo', 'Método (RTK/PPP/…)'], ['data_levantamento', 'Data (AAAA-MM-DD)']].map(([k, lb]) => (
                <input key={k} className={inp} placeholder={lb} value={(proj.levantamento || {})[k] || ''}
                  onChange={(e) => patchLento({ levantamento: { ...(proj.levantamento || {}), [k]: e.target.value } })} />
              ))}
            </div>
          </div>
        </div>
      )}

      {passo === 'Composição' && comp && (
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-3">
            <Field label="Modelo (preset)">
              <select className={inp} value={comp.preset || 'PERSONALIZADO'} onChange={(e) => setPreset(e.target.value)}>
                {(opcoes?.presets || []).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="Definição da capa (editável)">
              <input list="defcapa" className={inp} value={comp.definicao_capa || ''} onChange={(e) => setComp({ ...comp, definicao_capa: e.target.value })} onBlur={(e) => setDefinicaoCapa(e.target.value)} />
              <datalist id="defcapa">{(opcoes?.definicoes_capa || []).map((d) => <option key={d} value={d} />)}</datalist>
            </Field>
          </div>
          <div>
            <div className="text-xs font-semibold mb-2" style={{ color: GREEN }}>Memoriais (multi-seleção)</div>
            <div className="grid sm:grid-cols-2 gap-2">
              {(opcoes?.memoriais || []).map((m) => {
                const on = (proj.memoriais_selecionados || []).includes(m.codigo);
                const disabled = m.codigo === 'MD-CON' && !proj.possui_benfeitoria;
                return (
                  <label key={m.codigo} className={`flex items-start gap-2 p-2 rounded-lg border text-sm cursor-pointer ${on ? 'border-emerald-300 bg-emerald-50' : ''} ${disabled ? 'opacity-50' : ''}`}>
                    <input type="checkbox" checked={on} disabled={disabled} onChange={() => toggleMemorial(m.codigo)} className="mt-1" />
                    <span><strong>{m.codigo}</strong> — {m.nome}<br /><span className="text-[11px] text-gray-500">{m.descricao}</span></span>
                  </label>
                );
              })}
            </div>
            <label className="flex items-center gap-2 mt-2 text-sm">
              <input type="checkbox" checked={!!proj.possui_benfeitoria} onChange={(e) => patch({ possui_benfeitoria: e.target.checked }).then(recomporPreview)} />
              Possui benfeitoria (habilita MD-CON — área construída)
            </label>
          </div>
          <div>
            <div className="text-xs font-semibold mb-2" style={{ color: GREEN }}>Peças do dossiê ({comp.paginas_estimadas} págs. estimadas)</div>
            <div className="grid sm:grid-cols-2 gap-1.5">
              {(comp.pecas || []).map((p) => (
                <label key={p.chave} title={p.motivo || ''}
                  className={`flex items-center gap-2 p-1.5 rounded-lg border text-sm ${!p.habilitada ? 'opacity-45' : ''} ${p.no_pdf ? 'border-emerald-200 bg-emerald-50/50' : ''}`}>
                  <input type="checkbox" checked={p.ligada} disabled={!p.habilitada} onChange={(e) => togglePeca(p.chave, e.target.checked)} />
                  <span>{p.label}{!p.habilitada && <span className="text-[10px] text-amber-600"> · {p.motivo}</span>}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {passo === 'Uploads' && <UploadsStep proj={proj} id={id} opcoes={opcoes} onChange={carregar} recomporPreview={recomporPreview} />}

      {passo === 'Coordenadas' && <CoordsStep proj={proj} id={id} patch={patch} onImported={carregar} toast={toast} recomporPreview={recomporPreview} />}

      {passo === 'Situação & Quadra' && <QuadraStep key={JSON.stringify(proj.quadra_dados || {})} proj={proj} id={id} recomporPreview={recomporPreview} />}

      {passo === 'ART & Geração' && (
        <GeracaoStep proj={proj} id={id} patch={patchLento} comp={comp} valid={valid} setValid={setValid} capaUrl={capaUrl} setCapaUrl={setCapaUrl} toast={toast} />
      )}

      {/* navegação */}
      <div className="flex justify-between mt-8">
        <button onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}
          className="px-4 py-2 rounded-lg text-sm border inline-flex items-center gap-1 disabled:opacity-40">
          <ChevronLeft className="w-4 h-4" /> Voltar
        </button>
        {step < PASSOS.length - 1 ? (
          <button onClick={() => setStep((s) => s + 1)} className="px-4 py-2 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-1" style={{ background: GREEN }}>
            Avançar <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button onClick={() => nav('/dashboard/topografia/geo-urbano')} className="px-4 py-2 rounded-lg text-sm font-semibold text-white" style={{ background: GREEN }}>Concluir</button>
        )}
      </div>
    </div>
  );
}

// ── Uploads (§3 — quase tudo opcional) ──
function UploadsStep({ proj, id, opcoes, onChange, recomporPreview }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(null);
  const [extraindo, setExtraindo] = useState(false);
  const uploads = proj.uploads || {};
  const temMemorial = (uploads.memorial_coordenadas || []).length || (uploads.memorial_situacao || []).length;
  const enviar = async (tipo, file) => {
    if (!file) return;
    setBusy(tipo);
    try { await geoUrbanoAPI.upload(id, tipo, file); await onChange(); recomporPreview(); }
    catch { toast({ title: 'Erro no upload', variant: 'destructive' }); }
    finally { setBusy(null); }
  };
  const remover = async (tipo, itemId) => {
    try { await geoUrbanoAPI.removerUpload(id, tipo, itemId); await onChange(); recomporPreview(); } catch { /* */ }
  };
  const extrair = async () => {
    setExtraindo(true);
    try {
      const r = await geoUrbanoAPI.georrefExtrair(id);
      await onChange();
      recomporPreview();
      toast({ title: `Dados extraídos ✓ (${r.vertices || 0} vértices)`, description: 'Confira e edite nas etapas seguintes — nada trava.' });
    } catch (e) {
      toast({ title: 'Erro ao extrair', description: (e?.response?.data?.detail || '').toString().slice(0, 140), variant: 'destructive' });
    } finally { setExtraindo(false); }
  };
  return (
    <>
    <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 mb-3 flex items-center justify-between gap-3">
      <div className="text-sm text-gray-700">
        Anexe o <strong>Memorial de Coordenadas</strong> (e o de Situação) e clique em <strong>Extrair</strong> —
        o sistema preenche identificação, vértices e a quadra automaticamente. Tudo fica <strong>editável</strong> depois.
      </div>
      <button onClick={extrair} disabled={extraindo || !temMemorial}
        className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-40" style={{ background: GREEN }}>
        <Sparkles className="w-4 h-4" /> {extraindo ? 'Extraindo…' : 'Extrair dos documentos'}
      </button>
    </div>
    <div className="grid sm:grid-cols-2 gap-3">
      {(opcoes?.uploads || []).map((u) => {
        const itens = uploads[u.chave] || [];
        return (
          <div key={u.chave} className={`rounded-lg border p-3 ${u.obrigatorio ? 'border-emerald-300' : ''}`}>
            <div className="text-sm font-medium flex items-center gap-1.5" style={{ color: GREEN }}>
              <Upload className="w-3.5 h-3.5" /> {u.label}
              {u.obrigatorio ? <span className="text-[10px] text-emerald-700">obrigatório</span> : <span className="text-[10px] text-gray-400">opcional</span>}
            </div>
            {itens.map((it) => (
              <div key={it.id} className="flex items-center justify-between text-xs mt-1.5 bg-gray-50 rounded px-2 py-1">
                <span className="truncate">{it.nome || 'arquivo'}</span>
                <button onClick={() => remover(u.chave, it.id)} className="text-red-500"><Trash2 className="w-3 h-3" /></button>
              </div>
            ))}
            <label className="mt-2 inline-flex items-center gap-1.5 text-xs cursor-pointer text-emerald-700">
              <Plus className="w-3.5 h-3.5" /> {busy === u.chave ? 'Enviando…' : 'Anexar arquivo'}
              <input type="file" className="hidden" onChange={(e) => { enviar(u.chave, e.target.files?.[0]); e.target.value = ''; }} />
            </label>
          </div>
        );
      })}
    </div>
    </>
  );
}

// ── Coordenadas & vértices ──
function CoordsStep({ proj, id, patch, onImported, toast, recomporPreview }) {
  const [imp, setImp] = useState(false);
  const verts = proj.vertices || [];
  const importar = async (file) => {
    if (!file) return;
    setImp(true);
    try {
      const r = await geoUrbanoAPI.georrefImportCoordenadas(id, file);
      await onImported();
      recomporPreview();
      toast({ title: `${r.total} vértice(s) importado(s) (${r.sistema})`, description: (r.avisos || []).join(' · ').slice(0, 120) });
    } catch (e) {
      toast({ title: 'Erro ao importar', description: (e?.response?.data?.detail || '').toString().slice(0, 120), variant: 'destructive' });
    } finally { setImp(false); }
  };
  const setV = (i, campo, val) => {
    const nv = verts.map((v, j) => (j === i ? { ...v, [campo]: campo === 'coord_n' || campo === 'coord_e' || campo === 'distancia_m' ? (parseFloat(val) || null) : val } : v));
    patch({ vertices: nv });
  };
  const addV = () => patch({ vertices: [...verts, { ordem: verts.length + 1, de: `P${verts.length + 1}` }] });
  const rmV = (i) => patch({ vertices: verts.filter((_, j) => j !== i).map((v, k) => ({ ...v, ordem: k + 1 })) });
  return (
    <div>
      <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 mb-4 flex items-center justify-between">
        <div className="text-sm text-gray-700">Importe as coordenadas (CSV/TXT/KML/KMZ) — colunas <code>vertice,E,N</code> ou <code>vertice,lat,long</code>. UTM/geográficas detectadas automaticamente.</div>
        <label className="inline-flex items-center gap-1.5 text-xs cursor-pointer px-3 py-1.5 rounded-lg text-white font-medium" style={{ background: GREEN }}>
          <Upload className="w-3.5 h-3.5" /> {imp ? 'Importando…' : 'Importar arquivo'}
          <input type="file" accept=".csv,.txt,.kml,.kmz" className="hidden" onChange={(e) => { importar(e.target.files?.[0]); e.target.value = ''; }} />
        </label>
      </div>
      <div className="flex gap-4 text-sm mb-3">
        <span>Área calculada: <strong>{proj.area_calculada_m2 ? `${Number(proj.area_calculada_m2).toLocaleString('pt-BR', { minimumFractionDigits: 2 })} m²` : '—'}</strong></span>
        <span>Perímetro: <strong>{proj.perimetro_m ? `${Number(proj.perimetro_m).toLocaleString('pt-BR', { minimumFractionDigits: 2 })} m` : '—'}</strong></span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[720px] w-full text-xs">
          <thead><tr className="bg-gray-100 text-gray-600">
            {['Vértice', 'Coord. N (Y)', 'Coord. E (X)', 'Azimute', 'Dist. (m)', 'Confrontante', ''].map((h) => <th key={h} className="px-2 py-1.5 text-left font-medium">{h}</th>)}
          </tr></thead>
          <tbody>
            {verts.map((v, i) => (
              <tr key={i} className="border-b">
                <td className="px-1 py-1"><input className="w-16 border rounded px-1 py-0.5" value={v.de || ''} onChange={(e) => setV(i, 'de', e.target.value)} /></td>
                <td className="px-1"><input className="w-28 border rounded px-1 py-0.5 font-mono" value={v.coord_n ?? ''} onChange={(e) => setV(i, 'coord_n', e.target.value)} /></td>
                <td className="px-1"><input className="w-28 border rounded px-1 py-0.5 font-mono" value={v.coord_e ?? ''} onChange={(e) => setV(i, 'coord_e', e.target.value)} /></td>
                <td className="px-1"><input className="w-24 border rounded px-1 py-0.5" value={v.azimute || ''} onChange={(e) => setV(i, 'azimute', e.target.value)} /></td>
                <td className="px-1"><input className="w-16 border rounded px-1 py-0.5" value={v.distancia_m ?? ''} onChange={(e) => setV(i, 'distancia_m', e.target.value)} /></td>
                <td className="px-1"><input className="w-40 border rounded px-1 py-0.5" value={v.confrontante_lado || ''} onChange={(e) => setV(i, 'confrontante_lado', e.target.value)} /></td>
                <td className="px-1"><button onClick={() => rmV(i)} className="text-red-500"><Trash2 className="w-3.5 h-3.5" /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button onClick={addV} className="mt-2 text-xs text-emerald-700 inline-flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Adicionar vértice</button>
    </div>
  );
}

// ── Situação & Quadra ──
function QuadraStep({ proj, id, recomporPreview }) {
  const q = proj.quadra_dados || {};
  const [local, setLocal] = useState(q);
  const salvar = (patch) => {
    const nq = { ...local, ...patch };
    setLocal(nq);
    geoUrbanoAPI.georrefQuadra(id, nq).then(recomporPreview).catch(() => {});
  };
  const vias = local.vias || [];
  const lotes = local.lotes || [];
  const esq = local.esquina || {};
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label="Formato do lote"><input className={inp} value={local.formato || ''} placeholder="retangular" onChange={(e) => salvar({ formato: e.target.value })} /></Field>
        <Field label="Modo da planta de quadra">
          <select className={inp} value={local.modo_planta || 'gerada'} onChange={(e) => salvar({ modo_planta: e.target.value })}>
            <option value="gerada">Gerada (desenho)</option><option value="anexada">Anexada (upload)</option><option value="nenhuma">Nenhuma</option>
          </select>
        </Field>
      </div>
      <div>
        <div className="text-xs font-semibold mb-1" style={{ color: GREEN }}>Vias que formam a quadra</div>
        {vias.map((v, i) => (
          <div key={i} className="flex gap-2 mb-1">
            <input className={inp} value={v.nome || ''} placeholder="Logradouro" onChange={(e) => salvar({ vias: vias.map((x, j) => j === i ? { ...x, nome: e.target.value } : x) })} />
            <select className="border rounded-lg px-2 text-sm" value={v.posicao || ''} onChange={(e) => salvar({ vias: vias.map((x, j) => j === i ? { ...x, posicao: e.target.value } : x) })}>
              <option value="">—</option>{['N', 'S', 'L', 'O'].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={() => salvar({ vias: vias.filter((_, j) => j !== i) })} className="text-red-500"><Trash2 className="w-4 h-4" /></button>
          </div>
        ))}
        <button onClick={() => salvar({ vias: [...vias, { nome: '', posicao: '' }] })} className="text-xs text-emerald-700 inline-flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Adicionar via</button>
      </div>
      <div className="grid sm:grid-cols-3 gap-3">
        <Field label="Esquina — logradouro"><input className={inp} value={esq.logradouro || ''} onChange={(e) => salvar({ esquina: { ...esq, logradouro: e.target.value } })} /></Field>
        <Field label="Distância até a esquina (m)"><input type="number" className={inp} value={esq.distancia_m ?? ''} onChange={(e) => salvar({ esquina: { ...esq, distancia_m: parseFloat(e.target.value) || null } })} /></Field>
        <Field label="É esquina?"><label className="flex items-center gap-2 text-sm mt-2"><input type="checkbox" checked={!!esq.is_esquina} onChange={(e) => salvar({ esquina: { ...esq, is_esquina: e.target.checked } })} /> Lote de esquina</label></Field>
      </div>
      <div>
        <div className="text-xs font-semibold mb-1" style={{ color: GREEN }}>Lotes vizinhos (planta de quadra)</div>
        {lotes.map((l, i) => (
          <div key={i} className="flex gap-2 mb-1">
            <input className={inp} value={l.lote || ''} placeholder="Lote" onChange={(e) => salvar({ lotes: lotes.map((x, j) => j === i ? { ...x, lote: e.target.value } : x) })} />
            <input className={inp} value={l.confrontacao || ''} placeholder="Posição" onChange={(e) => salvar({ lotes: lotes.map((x, j) => j === i ? { ...x, confrontacao: e.target.value } : x) })} />
            <button onClick={() => salvar({ lotes: lotes.filter((_, j) => j !== i) })} className="text-red-500"><Trash2 className="w-4 h-4" /></button>
          </div>
        ))}
        <button onClick={() => salvar({ lotes: [...lotes, { lote: '', confrontacao: '' }] })} className="text-xs text-emerald-700 inline-flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Adicionar lote</button>
      </div>
    </div>
  );
}

// ── ART/TRT & Geração ──
function GeracaoStep({ proj, id, patch, comp, valid, setValid, capaUrl, setCapaUrl, toast }) {
  const art = proj.art_trt || {};
  const [validando, setValidando] = useState(false);
  const validar = async () => { setValidando(true); try { setValid(await geoUrbanoAPI.georrefValidar(id)); } finally { setValidando(false); } };
  const verCapa = async () => {
    try { const b = await geoUrbanoAPI.georrefCapaPreview(id, proj.tema); setCapaUrl(URL.createObjectURL(b)); } catch { toast({ title: 'Erro na prévia da capa', variant: 'destructive' }); }
  };
  const pecasGeraveis = (comp?.pecas || []).filter((p) => p.no_pdf && !['capa', 'sumario', 'imagem_localizacao', 'relatorio_fotografico', 'matricula_anexa', 'docs_proprietario', 'anexos_diversos'].includes(p.chave));
  return (
    <div className="space-y-5">
      <TimbreToggle toast={toast} />
      <div>
        <div className="text-sm font-semibold mb-2" style={{ color: GREEN }}>ART / TRT</div>
        <div className="grid sm:grid-cols-3 gap-3">
          <Field label="Tipo"><select className={inp} value={art.tipo || 'TRT'} onChange={(e) => patch({ art_trt: { ...art, tipo: e.target.value } })}><option>TRT</option><option>ART</option></select></Field>
          <Field label="Número"><input className={inp} value={art.numero || ''} onChange={(e) => patch({ art_trt: { ...art, numero: e.target.value } })} /></Field>
          <Field label="Data"><input className={inp} value={art.data || ''} onChange={(e) => patch({ art_trt: { ...art, data: e.target.value } })} /></Field>
        </div>
      </div>

      <div className="rounded-lg border p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-semibold" style={{ color: GREEN }}>Validação</div>
          <button onClick={validar} className="text-xs px-3 py-1.5 rounded-lg border" style={{ borderColor: GOLD, color: GREEN }}>{validando ? 'Validando…' : 'Validar dossiê'}</button>
        </div>
        {valid && (
          <div className="space-y-1 text-xs">
            {valid.bloqueios.map((b, i) => <div key={i} className="text-red-600 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {b.msg}</div>)}
            {valid.avisos.map((a, i) => <div key={i} className="text-amber-600 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {a.msg}</div>)}
            {valid.ok && !valid.avisos.length && <div className="text-emerald-600 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Pronto para gerar.</div>}
            {valid.ok && valid.avisos.length > 0 && <div className="text-emerald-600 mt-1">Sem bloqueios — pode gerar (avisos acima não impedem).</div>}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <button onClick={verCapa} className="px-3 py-2 rounded-lg text-sm border inline-flex items-center gap-1.5"><ImageIcon className="w-4 h-4" /> Prévia da capa</button>
        <button onClick={() => abrirBlob(geoUrbanoAPI.georrefDossie(id, proj.tema), toast)} className="px-4 py-2 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-1.5" style={{ background: GREEN }}>
          <FileText className="w-4 h-4" /> Ver Dossiê
        </button>
        <button onClick={async () => {
          try {
            const r = await geoUrbanoAPI.gerarLink(id);
            try { await navigator.clipboard.writeText(r.url); } catch { /* */ }
            toast({ title: 'Link do dossiê copiado ✓', description: r.url });
          } catch { toast({ title: 'Erro ao gerar link', variant: 'destructive' }); }
        }} className="px-3 py-2 rounded-lg text-sm border inline-flex items-center gap-1.5 text-sky-700 border-sky-300">
          <Link2 className="w-4 h-4" /> Gerar link do dossiê
        </button>
      </div>
      {capaUrl && <img src={capaUrl} alt="Prévia da capa" className="max-w-xs rounded-lg border shadow-sm" />}

      <div>
        <div className="text-sm font-semibold mb-2" style={{ color: GREEN }}>Baixar peças individuais</div>
        <div className="grid sm:grid-cols-2 gap-1.5">
          {pecasGeraveis.map((p) => (
            <div key={p.chave} className="flex items-center justify-between text-sm border rounded-lg px-2.5 py-1.5">
              <span>{p.label}</span>
              <div className="flex gap-2">
                <button onClick={() => abrirBlob(geoUrbanoAPI.georrefDocumento(id, p.chave, proj.tema), toast)} className="text-emerald-700 inline-flex items-center gap-1"><Eye className="w-3.5 h-3.5" /> Ver</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Timbre (letterhead) — usa os dados JÁ cadastrados no Perfil; só liga/desliga aqui.
function TimbreToggle({ toast }) {
  const [perfil, setPerfil] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { perfilAPI.get().then(setPerfil).catch(() => {}); }, []);
  if (!perfil) return null;
  const toggle = async (ativo) => {
    setSaving(true);
    try { const p = await perfilAPI.update({ ...perfil, timbre_ativo: ativo }); setPerfil(p); }
    catch { toast({ title: 'Erro ao salvar o timbre', variant: 'destructive' }); }
    finally { setSaving(false); }
  };
  return (
    <label className="flex items-start gap-2 text-sm rounded-lg border bg-gray-50 p-3 cursor-pointer">
      <input type="checkbox" checked={!!perfil.timbre_ativo} disabled={saving} onChange={(e) => toggle(e.target.checked)} className="mt-0.5" />
      <span>
        <strong style={{ color: GREEN }}>Usar meu timbre no cabeçalho das peças</strong>
        <br /><span className="text-[11px] text-gray-500">
          Usa contato/endereço/empresa e o RT já cadastrados no seu Perfil. Sem timbre, o cabeçalho é a marca AvalieImob.
        </span>
      </span>
    </label>
  );
}
