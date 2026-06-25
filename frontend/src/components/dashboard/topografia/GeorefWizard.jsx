// @module topografia/GeorefWizard — Wizard de Georreferenciamento (5 etapas).
// Projeto → Upload → Conferência → Geração → Entrega. Autosave (PATCH) + extração
// SIGEF + downloads (PDF/DOCX/Shapefile/Dossiê).
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, UploadCloud, FileCheck2, Wand2, FileDown, Eye,
  CheckCircle2, AlertTriangle, MapPin, Loader2, Map as MapIcon, Plus, Trash2, Search, PenLine,
} from 'lucide-react';
import { georefAPI, assinaturaPosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import PoligonalPreview from './PoligonalPreview';
import { TIPOS_SERVICO } from './GeorefList';
import AssinaturaPosicionadaModal from '../assinatura/AssinaturaPosicionadaModal';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const STEPS = ['Projeto', 'Upload', 'Conferência', 'Geração', 'Entrega'];

// DRL só é gerada/listada quando o tipo de serviço EXIGE (desmembramento/remembramento dispensam).
const DRL_DISPENSA = ['desmembramento', 'remembramento'];
const requerDrlTipo = (tipo) => !DRL_DISPENSA.includes(tipo);

// Tipos que podem ter MÚLTIPLAS parcelas (Parte I, II, III...).
const MULTIPARCELA_TIPOS = ['desmembramento', 'remembramento'];

const normLista = (v) => (Array.isArray(v) ? v : (v ? [v] : []));
const anoDoArquivo = (nome) => { const m = (nome || '').match(/(19|20)\d{2}/); return m ? parseInt(m[0], 10) : 0; };
const ordenarPorExercicio = (itens) =>
  [...itens].sort((a, b) => (anoDoArquivo(a.filename) - anoDoArquivo(b.filename))
    || String(a.filename || '').localeCompare(String(b.filename || '')));

const UPLOADS = [
  { tipo: 'memorial', label: 'Memorial Descritivo (SIGEF)', accept: '.pdf', req: true },
  { tipo: 'mapa', label: 'Mapa / Planta (SIGEF)', accept: '.pdf,image/*' },
  { tipo: 'ccir', label: 'CCIR', accept: '.pdf' },
  { tipo: 'car', label: 'CAR (Cadastro Ambiental Rural)', accept: '.pdf,image/*' },
  { tipo: 'itr', label: 'ITR (Imposto Territorial Rural)', accept: '.pdf,image/*' },
  { tipo: 'certidao', label: 'Certidão de Matrícula', accept: '.pdf' },
  { tipo: 'art_trt', label: 'ART / TRT / RRT', accept: '.pdf,image/*' },
  { tipo: 'doc_cliente', label: 'Documento do Cliente', accept: '.pdf,image/*' },
];

const IMOVEL_CAMPOS = [
  ['denominacao', 'Denominação', 2], ['proprietario_nome', 'Proprietário', 2],
  ['proprietario_cpf_cnpj', 'CPF/CNPJ', 1], ['proprietario_estado_civil', 'Estado civil', 1],
  ['proprietario_profissao', 'Profissão', 1], ['proprietario_nacionalidade', 'Nacionalidade', 1],
  ['proprietario_endereco', 'Endereço do proprietário', 2],
  ['matricula', 'Matrícula', 1], ['livro', 'Livro', 1],
  ['cod_incra', 'Código INCRA/SNCR', 1], ['natureza_area', 'Natureza da área', 1],
  ['municipio', 'Município', 1], ['uf', 'UF', 1],
  ['cartorio_nome', 'Cartório / Serventia', 2], ['cartorio_cns', 'CNS do cartório', 1],
  ['cartorio_municipio', 'Comarca/Município do cartório', 1],
  ['area_ha', 'Área (ha)', 1], ['perimetro_m', 'Perímetro (m)', 1],
  ['sistema_geodesico', 'Sistema geodésico', 1], ['certificacao_sigef', 'Certificação SIGEF', 1],
  ['certidao_numero', 'Nº da certidão', 1],
];
const RT_CAMPOS = [
  ['nome', 'Nome do RT', 2], ['formacao', 'Formação', 2],
  ['conselho', 'Conselho', 1], ['credenciamento_incra', 'Cód. INCRA', 1],
  ['art_trt', 'ART/TRT', 1], ['cnai', 'CNAI', 1], ['creci', 'CRECI', 1],
];

// ── helpers de download ──────────────────────────────────────────────────────
function salvarBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}
async function verBlob(promise) {
  const win = window.open('', '_blank'); // abre síncrono p/ não bloquear popup
  try {
    const blob = await promise;
    const url = URL.createObjectURL(blob);
    if (win) win.location.href = url; else window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    if (win) win.close();
    throw e;
  }
}

export default function GeorefWizard() {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();

  const [proj, setProj] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(0);
  const [extraindo, setExtraindo] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [validacao, setValidacao] = useState(null);
  const [docsSel, setDocsSel] = useState(
    ['requerimento', 'laudo_tecnico', 'memorial', 'drl', 'shapefile', 'dossie']);

  const projRef = useRef(proj);
  useEffect(() => { projRef.current = proj; }, [proj]);
  const debounceRef = useRef(null);
  const dirtyRef = useRef(false);

  // ── load ──
  useEffect(() => {
    (async () => {
      try {
        const d = await georefAPI.obter(id);
        setProj(d);
      } catch (e) {
        toast({ title: 'Projeto não encontrado', variant: 'destructive' });
        nav('/dashboard/topografia/georef');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, nav, toast]);

  // ── save (PATCH) ──
  const salvar = useCallback(async (silent = true) => {
    const p = projRef.current;
    if (!p || !dirtyRef.current) return;
    try {
      const payload = {
        nome_projeto: p.nome_projeto, tipo_servico: p.tipo_servico, tema_pdf: p.tema_pdf,
        imovel: p.imovel, responsavel_tecnico: p.responsavel_tecnico,
      };
      const upd = await georefAPI.atualizar(p.id, payload);
      dirtyRef.current = false;
      if (upd?.completude != null) setProj((x) => ({ ...x, completude: upd.completude }));
      if (!silent) toast({ title: 'Salvo' });
    } catch (e) {
      if (!silent) toast({ title: 'Erro ao salvar', variant: 'destructive' });
    }
  }, [toast]);

  const mark = () => {
    dirtyRef.current = true;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => salvar(true), 1200);
  };
  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current); }, []);

  const upd = (patch) => { setProj((p) => ({ ...p, ...patch })); mark(); };
  const updImovel = (k, v) => { setProj((p) => ({ ...p, imovel: { ...p.imovel, [k]: v } })); mark(); };
  const updRT = (k, v) => {
    setProj((p) => ({ ...p, responsavel_tecnico: { ...p.responsavel_tecnico, [k]: v } })); mark();
  };

  const irPara = async (s) => { await salvar(true); setStep(s); };

  // ── upload ──
  const onUpload = async (tipo, file) => {
    if (!file) return;
    try {
      await georefAPI.upload(proj.id, tipo, file);
      const d = await georefAPI.obter(proj.id);
      setProj(d);
      toast({ title: `${tipo} enviado` });
    } catch (e) {
      toast({ title: 'Falha no upload', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };

  // ── upload multi (ITR — últimos 5 exercícios) ──
  const onUploadMultiplos = async (tipo, files) => {
    const lista = Array.from(files || []).slice(0, 5);
    if (!lista.length) return;
    try {
      for (const f of lista) { await georefAPI.upload(proj.id, tipo, f); }
      await recarregar();
      toast({ title: `${lista.length} arquivo(s) enviado(s)` });
    } catch (e) {
      toast({ title: 'Falha no upload', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };
  const removerItem = async (tipo, itemId) => {
    try {
      await georefAPI.removerUploadItem(proj.id, tipo, itemId);
      await recarregar();
      toast({ title: 'Removido' });
    } catch (e) {
      toast({ title: 'Erro ao remover', description: e?.response?.data?.detail || e?.message || '', variant: 'destructive' });
    }
  };

  // ── parcelas (desmembramento) ──
  const recarregar = async () => { try { setProj(await georefAPI.obter(proj.id)); } catch { /* */ } };
  const addParcela = async () => {
    try { await georefAPI.adicionarParcela(proj.id); await recarregar(); }
    catch { toast({ title: 'Erro ao adicionar parcela', variant: 'destructive' }); }
  };
  const removeParcela = async (parcelaId) => {
    try { await georefAPI.removerParcela(proj.id, parcelaId); await recarregar(); }
    catch { toast({ title: 'Erro ao remover parcela', variant: 'destructive' }); }
  };
  const uploadParcelaFile = async (parcelaId, tipo, file) => {
    if (!file) return;
    try {
      const r = await georefAPI.uploadParcela(proj.id, parcelaId, tipo, file);
      await recarregar();
      toast({ title: (tipo === 'memorial' && r?.extraido) ? 'Memorial lido — parcela extraída ✓' : `${tipo} enviado` });
    } catch (e) {
      toast({ title: 'Falha no upload', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };

  // ── assinatura ICP (multi-página) ──
  const [assinId, setAssinId] = useState(null);
  const [preparandoAssin, setPreparandoAssin] = useState(null);
  const [assinaturas, setAssinaturas] = useState({});   // { `${doc}:${parcela||''}`: {assinado,id} }
  const recarregarAssinaturas = useCallback(async () => {
    if (!proj?.id) return;
    try {
      const lista = await georefAPI.listarAssinaturas(proj.id);
      const map = {};
      (lista || []).forEach((r) => { map[`${r.doc}:${r.parcela || ''}`] = r; });
      setAssinaturas(map);
    } catch { /* sem status */ }
  }, [proj?.id]);
  useEffect(() => { if (step === 4) recarregarAssinaturas(); }, [step, recarregarAssinaturas]);
  const statusAssin = (docTipo, parcela) => assinaturas[`${docTipo}:${parcela || ''}`] || null;
  const abrirAssinatura = async (docTipo, parcela) => {
    setPreparandoAssin(`${docTipo}:${parcela || ''}`);
    try {
      const r = await georefAPI.prepararAssinatura(proj.id, { doc: docTipo, parcela, tema: proj.tema_pdf });
      setAssinId(r.id);
    } catch (e) {
      toast({ title: 'Erro ao preparar assinatura', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setPreparandoAssin(null);
    }
  };

  // ── cartório pelo CNS ──
  const buscarServentia = async () => {
    const cns = proj.imovel?.cartorio_cns;
    if (!cns) { toast({ title: 'Informe o CNS do cartório primeiro', variant: 'destructive' }); return; }
    try {
      const s = await georefAPI.buscarServentia(cns);
      setProj((p) => ({ ...p, imovel: { ...p.imovel, cartorio_nome: s.denominacao, cartorio_municipio: s.cidade, cartorio_uf: s.uf } }));
      mark();
      toast({ title: 'Cartório encontrado', description: s.denominacao });
    } catch (e) {
      toast({ title: 'CNS não encontrado na tabela', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };

  const extrair = async () => {
    setExtraindo(true);
    try {
      const res = await georefAPI.extrair(proj.id);
      setProj(res.projeto);
      setValidacao(res.validacao);
      toast({
        title: 'Extração concluída',
        description: (res.avisos && res.avisos.length) ? `${res.avisos.length} aviso(s)` : 'Confira os dados.',
      });
      setStep(2);
    } catch (e) {
      toast({ title: 'Erro na extração', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setExtraindo(false);
    }
  };

  const gerar = async () => {
    setGerando(true);
    try {
      await salvar(true);
      const docs = requerDrl ? docsSel : docsSel.filter((d) => d !== 'drl');
      const res = await georefAPI.gerar(proj.id, { documentos: docs, tema: proj.tema_pdf });
      setValidacao(res.validacao);
      setProj((p) => ({ ...p, status: 'documentos_gerados' }));
      toast({ title: 'Documentos prontos' });
      setStep(4);
    } catch (e) {
      toast({ title: 'Erro ao gerar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setGerando(false);
    }
  };

  const baixar = (promise, filename) =>
    promise.then((b) => salvarBlob(b, filename)).catch(() =>
      toast({ title: 'Erro ao baixar', variant: 'destructive' }));

  if (loading || !proj) return <div className="py-24"><BrandSpinner label="Carregando…" /></div>;

  const requerDrl = requerDrlTipo(proj.tipo_servico);
  const confrontantesDrl = requerDrl
    ? (proj.confrontantes || []).filter((c) => c.tipo !== 'proprio')
    : [];
  const suportaParcelas = MULTIPARCELA_TIPOS.includes(proj.tipo_servico);
  const parcelas = proj.parcelas || [];
  const nb = (proj.imovel?.matricula || proj.numero || 'projeto');

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* header */}
      <div className="flex items-center gap-3 mb-5">
        <button onClick={() => nav('/dashboard/topografia/georef')} className="text-gray-400 hover:text-gray-700">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-lg font-bold" style={{ color: GREEN }}>{proj.nome_projeto || 'Projeto'}</h1>
          <p className="text-xs text-gray-500">
            {proj.numero} · {TIPOS_SERVICO.find((t) => t.value === proj.tipo_servico)?.label}
          </p>
        </div>
        <span className="text-xs text-gray-400">{proj.completude || 0}% preenchido</span>
      </div>

      {/* stepper */}
      <div className="flex items-center gap-1 mb-6 overflow-x-auto">
        {STEPS.map((s, i) => (
          <button key={s} onClick={() => irPara(i)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap
              ${i === step ? 'text-white' : 'text-gray-500 bg-gray-100 hover:bg-gray-200'}`}
            style={i === step ? { background: GREEN } : {}}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px]
              ${i === step ? '' : 'bg-white'}`} style={i === step ? { background: GOLD, color: GREEN } : {}}>
              {i + 1}
            </span>
            {s}
          </button>
        ))}
      </div>

      {/* ── Etapa 1: Projeto ── */}
      {step === 0 && (
        <Card>
          <H title="Dados do projeto" />
          <div className="grid sm:grid-cols-2 gap-4">
            <L label="Nome do projeto / imóvel" full>
              <Input value={proj.nome_projeto || ''} onChange={(e) => upd({ nome_projeto: e.target.value })} />
            </L>
            <L label="Tipo de serviço">
              <Select value={proj.tipo_servico} onChange={(e) => upd({ tipo_servico: e.target.value })}>
                {TIPOS_SERVICO.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </Select>
            </L>
            <L label="Tema do PDF">
              <Select value={proj.tema_pdf} onChange={(e) => upd({ tema_pdf: e.target.value })}>
                <option value="prime_i">Prime I</option>
                <option value="prime_ii">Prime II</option>
                <option value="tradicional">Tradicional</option>
              </Select>
            </L>
          </div>
        </Card>
      )}

      {/* ── Etapa 2: Upload ── */}
      {step === 1 && (
        <Card>
          <H title="Documentos-fonte"
            sub="Suba o Memorial SIGEF (obrigatório) e os demais. Depois clique em Extrair." />
          <div className="grid sm:grid-cols-2 gap-3">
            {UPLOADS.map((u) => (
              u.tipo === 'itr'
                ? <ItrBox key="itr" itens={normLista(proj.uploads?.itr)}
                    onAdd={(files) => onUploadMultiplos('itr', files)}
                    onRemove={(id) => removerItem('itr', id)} />
                : <UploadBox key={u.tipo} u={u} info={proj.uploads?.[u.tipo]} onPick={(f) => onUpload(u.tipo, f)} />
            ))}
          </div>
          <div className="mt-6 flex items-center gap-3">
            <button onClick={extrair} disabled={extraindo || !proj.uploads?.memorial}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
              style={{ background: GREEN }}>
              {extraindo ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
              {extraindo ? 'Extraindo…' : 'Extrair dados do SIGEF'}
            </button>
            {!proj.uploads?.memorial && <span className="text-xs text-amber-600">Envie o Memorial Descritivo primeiro.</span>}
          </div>

          {suportaParcelas && (
            <div className="mt-6 border-t pt-5">
              <H title="Parcelas resultantes (Parte II, III…)"
                sub="A Parte I é o Memorial principal acima. Suba o Memorial de cada parcela do desmembramento." />
              {parcelas.map((pc, i) => (
                <div key={pc.id} className="mb-3 rounded-lg border p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm" style={{ color: GREEN }}>
                      {pc.rotulo || `Parte ${i + 2}`}{pc.denominacao ? ` — ${pc.denominacao}` : ''}
                    </span>
                    <button onClick={() => removeParcela(pc.id)} className="text-gray-300 hover:text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2">
                    <UploadBox u={{ tipo: 'memorial', label: 'Memorial da parcela', accept: '.pdf', req: true }}
                      info={pc.uploads?.memorial} onPick={(f) => uploadParcelaFile(pc.id, 'memorial', f)} />
                    <UploadBox u={{ tipo: 'mapa', label: 'Mapa da parcela', accept: '.pdf,image/*' }}
                      info={pc.uploads?.mapa} onPick={(f) => uploadParcelaFile(pc.id, 'mapa', f)} />
                  </div>
                </div>
              ))}
              <button onClick={addParcela}
                className="inline-flex items-center gap-2 text-sm px-3 py-2 rounded-lg border hover:bg-gray-50"
                style={{ color: GREEN }}>
                <Plus className="w-4 h-4" /> Adicionar parcela
              </button>
              <p className="text-xs text-gray-400 mt-2">O Memorial de cada parcela é lido automaticamente ao subir (vértices, área e confrontantes).</p>
            </div>
          )}
        </Card>
      )}

      {/* ── Etapa 3: Conferência ── */}
      {step === 2 && (
        <div className="space-y-5">
          {validacao && <Validacao v={validacao} />}
          <Card>
            <H title="Imóvel" sub="Confira e complete os campos não preenchidos (destacados)." />
            <div className="grid sm:grid-cols-2 gap-3">
              {IMOVEL_CAMPOS.map(([k, lab, span]) => (
                <L key={k} label={lab} full={span === 2}>
                  <Input value={proj.imovel?.[k] ?? ''} faltando={!proj.imovel?.[k]}
                    onChange={(e) => updImovel(k, e.target.value)} />
                </L>
              ))}
            </div>
            <button onClick={buscarServentia}
              className="mt-3 inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg border hover:bg-gray-50"
              style={{ color: GREEN }}>
              <Search className="w-3.5 h-3.5" /> Buscar cartório pelo CNS
            </button>
            <span className="ml-2 text-xs text-gray-400">preenche serventia + comarca automaticamente</span>
          </Card>
          <Card>
            <H title="Responsável Técnico" />
            <div className="grid sm:grid-cols-2 gap-3">
              {RT_CAMPOS.map(([k, lab, span]) => (
                <L key={k} label={lab} full={span === 2}>
                  <Input value={proj.responsavel_tecnico?.[k] ?? ''} onChange={(e) => updRT(k, e.target.value)} />
                </L>
              ))}
            </div>
          </Card>
          <Card>
            <H title="Poligonal" sub={`${(proj.vertices || []).length} vértices · ${confrontantesDrl.length} confrontante(s) p/ DRL`} />
            <div className="grid md:grid-cols-2 gap-4">
              <PoligonalPreview vertices={proj.vertices || []} />
              <div className="text-sm">
                <div className="font-medium text-gray-700 mb-1">Confrontantes</div>
                <ul className="space-y-1">
                  {(proj.confrontantes || []).map((c, i) => (
                    <li key={i} className="flex items-center gap-2 text-xs text-gray-600">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        c.tipo === 'via_publica' ? 'bg-sky-100 text-sky-700'
                          : c.tipo === 'proprio' ? 'bg-gray-100 text-gray-500'
                            : 'bg-emerald-100 text-emerald-700'}`}>
                        {c.tipo === 'via_publica' ? 'via pública' : c.tipo === 'proprio' ? 'próprio' : 'particular'}
                      </span>
                      <span className="truncate">{c.nome || c.descricao || c.imovel || `Mat. ${c.matricula}`}</span>
                      <span className="text-gray-400">({(c.segmentos || []).length} seg.)</span>
                    </li>
                  ))}
                  {(proj.confrontantes || []).length === 0 && <li className="text-gray-400">Nenhum confrontante extraído.</li>}
                </ul>
              </div>
            </div>
          </Card>
          {suportaParcelas && parcelas.length > 0 && (
            <Card>
              <H title="Parcelas resultantes" sub="Dados extraídos do Memorial de cada parcela do desmembramento." />
              <div className="space-y-4">
                {parcelas.map((pc, i) => (
                  <div key={pc.id} className="grid md:grid-cols-2 gap-4 border rounded-lg p-3">
                    <div className="text-sm">
                      <div className="font-medium" style={{ color: GREEN }}>{pc.rotulo || `Parte ${i + 2}`}</div>
                      <div className="text-gray-600">{pc.denominacao || '— sem dados (extraia novamente) —'}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        Área {pc.area_ha ?? '—'} ha · Perímetro {pc.perimetro_m ?? '—'} m · {(pc.vertices || []).length} vértices
                      </div>
                      {(pc.confrontantes || []).length > 0 && (
                        <div className="mt-2">
                          <div className="text-xs font-medium text-gray-700 mb-1">Confrontantes</div>
                          <ul className="space-y-1">
                            {(pc.confrontantes || []).map((c, j) => (
                              <li key={j} className="flex items-center gap-2 text-xs text-gray-600">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                                  c.tipo === 'via_publica' ? 'bg-sky-100 text-sky-700'
                                    : c.tipo === 'proprio' ? 'bg-gray-100 text-gray-500'
                                      : 'bg-emerald-100 text-emerald-700'}`}>
                                  {c.tipo === 'via_publica' ? 'via pública' : c.tipo === 'proprio' ? 'próprio' : 'particular'}
                                </span>
                                <span className="truncate">{c.nome || c.descricao || c.imovel || `Mat. ${c.matricula}`}</span>
                                <span className="text-gray-400">({(c.segmentos || []).length} seg.)</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                    <PoligonalPreview vertices={pc.vertices || []} height={150} />
                  </div>
                ))}
              </div>
            </Card>
          )}
          {(proj.imovel?.cadeia_dominial?.length > 0) && (
            <Card>
              <H title="Cadeia dominial" sub="Edite tipo / data / partes de cada ato (revisão da certidão)." />
              <div className="space-y-2">
                {proj.imovel.cadeia_dominial.map((a, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-center">
                    <span className="col-span-2 text-xs font-medium text-gray-600">{a.ato}</span>
                    <Input className="col-span-3" value={a.tipo ?? ''} placeholder="tipo"
                      onChange={(e) => updCadeia(setProj, mark, i, 'tipo', e.target.value)} />
                    <Input className="col-span-2" value={a.data ?? ''} placeholder="data"
                      onChange={(e) => updCadeia(setProj, mark, i, 'data', e.target.value)} />
                    <Input className="col-span-5" value={a.partes ?? ''} placeholder="partes"
                      onChange={(e) => updCadeia(setProj, mark, i, 'partes', e.target.value)} />
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Etapa 4: Geração ── */}
      {step === 3 && (
        <Card>
          <H title="Gerar documentos" sub="Escolha o tema e os documentos. A geração roda no servidor." />
          {validacao && <div className="mb-4"><Validacao v={validacao} /></div>}
          <L label="Tema do PDF">
            <Select value={proj.tema_pdf} onChange={(e) => upd({ tema_pdf: e.target.value })}>
              <option value="prime_i">Prime I</option>
              <option value="prime_ii">Prime II</option>
              <option value="tradicional">Tradicional</option>
            </Select>
          </L>
          <div className="grid sm:grid-cols-2 gap-2 mt-4">
            {[
              ['requerimento', 'Requerimento ao Cartório'],
              ['laudo_tecnico', 'Laudo Técnico de Agrimensura'],
              ['memorial', 'Memorial Descritivo'],
              ...(requerDrl ? [['drl', `DRL — Reconhecimento de Limites (${confrontantesDrl.length})`]] : []),
              ['shapefile', 'Shapefile SIG-RI (.zip)'],
              ['dossie', 'Dossiê consolidado (PDF)'],
            ].map(([k, lab]) => (
              <label key={k} className="flex items-center gap-2 text-sm border rounded-lg px-3 py-2 cursor-pointer">
                <input type="checkbox" checked={docsSel.includes(k)}
                  onChange={(e) => setDocsSel((s) => e.target.checked ? [...s, k] : s.filter((x) => x !== k))} />
                {lab}
              </label>
            ))}
          </div>
          {!requerDrl && (
            <p className="mt-3 text-xs text-gray-500">
              ℹ️ DRL dispensada para <strong>{proj.tipo_servico}</strong> (desmembramento e remembramento
              atuam dentro de limites já reconhecidos).
            </p>
          )}
          <button onClick={gerar} disabled={gerando}
            className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
            style={{ background: GREEN }}>
            {gerando ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCheck2 className="w-4 h-4" />}
            {gerando ? 'Gerando…' : 'Gerar documentos'}
          </button>
        </Card>
      )}

      {/* ── Etapa 5: Entrega ── */}
      {step === 4 && (
        <div className="space-y-4">
          <Card>
            <H title="Documentos prontos" sub="Baixe em PDF/DOCX ou assine com ICP-Brasil (em quantas páginas quiser)." />
            <div className="space-y-3">
              {[
                ['requerimento', 'Requerimento ao Cartório', 'requerimento', undefined],
                ['laudo_tecnico', 'Laudo Técnico de Agrimensura', 'laudo', undefined],
                ...(parcelas.length > 0 ? [] : [['memorial', 'Memorial Descritivo', 'memorial', 'principal']]),
              ].map(([k, lab, adoc, aparc]) => {
                const a = statusAssin(adoc, aparc);
                return (
                  <DocRow key={k} label={lab}
                    assinado={a?.assinado} onVerAssinado={a?.assinado ? () => verBlob(assinaturaPosAPI.downloadIcp('georef', a.id)) : null}
                    onVer={() => verBlob(georefAPI.documento(proj.id, k, 'pdf', proj.tema_pdf))}
                    onPdf={() => baixar(georefAPI.documento(proj.id, k, 'pdf', proj.tema_pdf), `${k}_${nb}.pdf`)}
                    onDocx={() => baixar(georefAPI.documento(proj.id, k, 'docx'), `${k}_${nb}.docx`)}
                    onAssinar={() => abrirAssinatura(adoc, aparc)} />
                );
              })}
              {proj.uploads?.art_trt && (() => {
                const a = statusAssin('art_trt');
                return (
                  <DocRow label="ART / TRT (documento enviado)"
                    assinado={a?.assinado} onVerAssinado={a?.assinado ? () => verBlob(assinaturaPosAPI.downloadIcp('georef', a.id)) : null}
                    onAssinar={() => abrirAssinatura('art_trt')} />
                );
              })()}
              {proj.uploads?.mapa && (() => {
                const a = statusAssin('mapa');
                return (
                  <DocRow label="Mapa / Planta (SIGEF) — documento enviado"
                    assinado={a?.assinado} onVerAssinado={a?.assinado ? () => verBlob(assinaturaPosAPI.downloadIcp('georef', a.id)) : null}
                    onAssinar={() => abrirAssinatura('mapa')} />
                );
              })()}
            </div>
          </Card>

          {parcelas.length > 0 && (
            <Card>
              <H title="Memoriais por parcela" sub="Um Memorial Descritivo por parcela do desmembramento." />
              <div className="space-y-3">
                {(() => {
                  const a = statusAssin('memorial', 'principal');
                  return (
                    <DocRow label={`Parte I — ${proj.imovel?.denominacao || 'principal'}`}
                      assinado={a?.assinado} onVerAssinado={a?.assinado ? () => verBlob(assinaturaPosAPI.downloadIcp('georef', a.id)) : null}
                      onVer={() => verBlob(georefAPI.memorialParcela(proj.id, 'principal', 'pdf', proj.tema_pdf))}
                      onPdf={() => baixar(georefAPI.memorialParcela(proj.id, 'principal', 'pdf', proj.tema_pdf), `memorial_PI_${nb}.pdf`)}
                      onDocx={() => baixar(georefAPI.memorialParcela(proj.id, 'principal', 'docx'), `memorial_PI_${nb}.docx`)}
                      onAssinar={() => abrirAssinatura('memorial', 'principal')} />
                  );
                })()}
                {parcelas.map((pc, i) => {
                  const a = statusAssin('memorial', pc.id);
                  return (
                    <DocRow key={pc.id} label={`${pc.rotulo || `Parte ${i + 2}`}${pc.denominacao ? ` — ${pc.denominacao}` : ''}`}
                      assinado={a?.assinado} onVerAssinado={a?.assinado ? () => verBlob(assinaturaPosAPI.downloadIcp('georef', a.id)) : null}
                      onVer={() => verBlob(georefAPI.memorialParcela(proj.id, pc.id, 'pdf', proj.tema_pdf))}
                      onPdf={() => baixar(georefAPI.memorialParcela(proj.id, pc.id, 'pdf', proj.tema_pdf), `memorial_${nb}.pdf`)}
                      onDocx={() => baixar(georefAPI.memorialParcela(proj.id, pc.id, 'docx'), `memorial_${nb}.docx`)}
                      onAssinar={() => abrirAssinatura('memorial', pc.id)} />
                  );
                })}
              </div>
            </Card>
          )}

          {confrontantesDrl.length > 0 && (
            <Card>
              <H title="DRL — Declarações de Reconhecimento de Limites" sub="Uma por confrontante." />
              <div className="space-y-3">
                {confrontantesDrl.map((c) => (
                  <DocRow key={c.key} label={c.nome || c.descricao || `Mat. ${c.matricula}`}
                    badge={c.tipo === 'via_publica' ? 'via pública' : null}
                    onVer={() => verBlob(georefAPI.drl(proj.id, c.key, 'pdf', proj.tema_pdf))}
                    onPdf={() => baixar(georefAPI.drl(proj.id, c.key, 'pdf', proj.tema_pdf), `DRL_${nb}.pdf`)}
                    onDocx={() => baixar(georefAPI.drl(proj.id, c.key, 'docx'), `DRL_${nb}.docx`)} />
                ))}
              </div>
            </Card>
          )}

          {!requerDrl && (
            <Card>
              <div className="text-sm text-gray-600">
                <strong className="text-gray-800">DRL dispensada.</strong> O serviço de{' '}
                <strong>{proj.tipo_servico}</strong> atua dentro de limites já reconhecidos — não
                requer Declaração de Reconhecimento de Limites dos confrontantes.
              </div>
            </Card>
          )}

          <Card>
            <H title="Arquivos geoespaciais & Dossiê" />
            <div className="flex flex-wrap gap-2">
              <BtnDown icon={MapIcon} label="Shapefile SIG-RI (.zip)"
                onClick={() => baixar(georefAPI.shapefile(proj.id), `SIGRI_${nb}.zip`)} />
              <BtnDown icon={MapPin} label="KML (Google Earth)"
                onClick={() => baixar(georefAPI.kml(proj.id), `${nb}.kml`)} />
              <BtnDown icon={Eye} label="Ver Dossiê (PDF)"
                onClick={() => verBlob(georefAPI.documento(proj.id, 'dossie', 'pdf', proj.tema_pdf))} />
              <BtnDown icon={FileDown} label="Baixar Dossiê"
                onClick={() => baixar(georefAPI.documento(proj.id, 'dossie', 'download', proj.tema_pdf), `Dossie_${nb}.pdf`)} />
              {statusAssin('dossie')?.assinado && (
                <BtnDown icon={CheckCircle2} label="Ver Dossiê assinado"
                  onClick={() => verBlob(assinaturaPosAPI.downloadIcp('georef', statusAssin('dossie').id))} />
              )}
              <BtnDown icon={PenLine}
                label={preparandoAssin === 'dossie:' ? 'Preparando…'
                  : (statusAssin('dossie')?.assinado ? 'Reassinar Dossiê (ICP)' : 'Assinar Dossiê (ICP)')}
                onClick={() => abrirAssinatura('dossie')} />
            </div>
            {statusAssin('dossie')?.assinado && (
              <p className="text-xs text-emerald-700 mt-2 font-medium">
                ✓ Dossiê assinado com ICP-Brasil — inclui as peças já assinadas individualmente.
              </p>
            )}
            <p className="text-xs text-gray-400 mt-3">
              Envio ao <strong>mapa.onr.org.br</strong> é manual (login ICP-Brasil do profissional), vinculado à prenotação.
            </p>
          </Card>
        </div>
      )}

      {/* nav */}
      <div className="flex justify-between mt-6">
        <button onClick={() => irPara(Math.max(0, step - 1))} disabled={step === 0}
          className="inline-flex items-center gap-1 px-4 py-2 text-sm border rounded-lg disabled:opacity-40">
          <ArrowLeft className="w-4 h-4" /> Voltar
        </button>
        {step < 4 && (
          <button onClick={() => irPara(Math.min(4, step + 1))}
            className="inline-flex items-center gap-1 px-4 py-2 text-sm font-semibold text-white rounded-lg"
            style={{ background: GREEN }}>
            Avançar <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {assinId && (
        <AssinaturaPosicionadaModal
          tipo="georef"
          documentId={assinId}
          onAssinado={() => {
            const id = assinId;
            setAssinId(null);
            toast({ title: 'Assinado com ICP-Brasil ✓', description: 'Abrindo o documento assinado…' });
            recarregarAssinaturas();
            verBlob(assinaturaPosAPI.downloadIcp('georef', id)).catch(() => {});
          }}
          onFechar={() => setAssinId(null)}
        />
      )}
    </div>
  );
}

// ── helpers de cadeia ──
function updCadeia(setProj, mark, i, k, v) {
  setProj((p) => {
    const cad = [...(p.imovel.cadeia_dominial || [])];
    cad[i] = { ...cad[i], [k]: v };
    return { ...p, imovel: { ...p.imovel, cadeia_dominial: cad } };
  });
  mark();
}

// ── UI primitives ──
const Card = ({ children }) => <div className="rounded-xl border border-gray-200 bg-white p-5">{children}</div>;
const H = ({ title, sub }) => (
  <div className="mb-4">
    <h2 className="font-bold" style={{ color: GREEN }}>{title}</h2>
    {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
  </div>
);
const L = ({ label, children, full }) => (
  <div className={full ? 'sm:col-span-2' : ''}>
    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
    {children}
  </div>
);
const Input = ({ className = '', faltando, ...p }) => (
  <input {...p}
    className={`w-full border rounded-lg px-3 py-2 text-sm ${faltando ? 'border-amber-300 bg-amber-50/40' : ''} ${className}`} />
);
const Select = ({ children, className = '', ...p }) => (
  <select {...p} className={`w-full border rounded-lg px-3 py-2 text-sm bg-white ${className}`}>{children}</select>
);

function UploadBox({ u, info, onPick }) {
  const ref = useRef(null);
  return (
    <div className="border border-dashed rounded-lg p-3 flex items-center gap-3">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: info ? 'rgba(12,51,32,0.08)' : '#F3F4F6' }}>
        {info ? <FileCheck2 className="w-5 h-5" style={{ color: GREEN }} /> : <UploadCloud className="w-5 h-5 text-gray-400" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-700 flex items-center gap-1">
          {u.label}{u.req && <span className="text-red-500">*</span>}
        </div>
        <div className="text-xs text-gray-400 truncate">{info ? (info.filename || 'enviado') : 'Nenhum arquivo'}</div>
      </div>
      <input ref={ref} type="file" accept={u.accept} className="hidden"
        onChange={(e) => { onPick(e.target.files?.[0]); e.target.value = ''; }} />
      <button onClick={() => ref.current?.click()}
        className="text-xs font-semibold px-3 py-1.5 rounded-lg border hover:bg-gray-50" style={{ color: GREEN }}>
        {info ? 'Trocar' : 'Enviar'}
      </button>
    </div>
  );
}

function ItrBox({ itens, onAdd, onRemove }) {
  const ref = useRef(null);
  return (
    <div className="border border-dashed rounded-lg p-3 sm:col-span-2">
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-sm font-medium text-gray-700">
            ITR — Imposto Territorial Rural <span className="text-xs text-gray-400">(últimos 5 exercícios)</span>
          </div>
          <div className="text-xs text-gray-400">
            {itens.length ? `${itens.length}/5 exercício(s) enviado(s)` : 'Nenhum arquivo — suba quantos tiver (até 5)'}
          </div>
        </div>
        <input ref={ref} type="file" accept=".pdf,image/*" multiple className="hidden"
          onChange={(e) => { onAdd(e.target.files); e.target.value = ''; }} />
        <button onClick={() => ref.current?.click()} disabled={itens.length >= 5}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg border hover:bg-gray-50 disabled:opacity-40"
          style={{ color: GREEN }}>
          + Adicionar
        </button>
      </div>
      {itens.length > 0 && (
        <ul className="space-y-1">
          {ordenarPorExercicio(itens).map((it) => {
            const ano = anoDoArquivo(it.filename);
            return (
              <li key={it.id || it.key} className="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">
                <FileCheck2 className="w-3.5 h-3.5 shrink-0" style={{ color: GREEN }} />
                {ano > 0 && <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 shrink-0">{ano}</span>}
                <span className="truncate flex-1">{it.filename || 'arquivo'}</span>
                <button onClick={() => onRemove(it.id || it.key)} className="text-gray-300 hover:text-red-500" title="Remover exercício">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function Validacao({ v }) {
  const ok = v?.ok;
  return (
    <div className={`rounded-lg border p-3 text-sm ${ok ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}>
      <div className="flex items-center gap-2 font-medium" style={{ color: ok ? '#065f46' : '#92400e' }}>
        {ok ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
        {ok ? 'Poligonal válida' : 'Atenção à poligonal'}
        {v?.area_calc_ha != null && <span className="font-normal text-xs">· área aferida {v.area_calc_ha} ha
          {v.divergencia_pct != null ? ` (Δ ${v.divergencia_pct}%)` : ''}</span>}
      </div>
      {(v?.avisos || []).length > 0 && (
        <ul className="mt-1 list-disc pl-5 text-xs text-amber-800">
          {v.avisos.map((a, i) => <li key={i}>{a}</li>)}
        </ul>
      )}
    </div>
  );
}

function DocRow({ label, badge, onVer, onPdf, onDocx, onAssinar, assinado, onVerAssinado }) {
  return (
    <div className={`flex items-center justify-between gap-3 border rounded-lg px-4 py-2.5 ${assinado ? 'border-emerald-300 bg-emerald-50/40' : ''}`}>
      <div className="text-sm font-medium text-gray-700 truncate">
        {label}
        {badge && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-sky-100 text-sky-700">{badge}</span>}
        {assinado && (
          <span className="ml-2 inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-emerald-600 text-white font-semibold">
            <CheckCircle2 className="w-3 h-3" /> Assinado ICP
          </span>
        )}
      </div>
      <div className="flex gap-1.5 shrink-0">
        {assinado && onVerAssinado && <Mini icon={Eye} label="Ver assinado" onClick={onVerAssinado} green />}
        {onVer && <Mini icon={Eye} label="Ver" onClick={onVer} />}
        {onPdf && <Mini icon={FileDown} label="PDF" onClick={onPdf} />}
        {onDocx && <Mini icon={FileDown} label="DOCX" onClick={onDocx} />}
        {onAssinar && <Mini icon={PenLine} label={assinado ? 'Reassinar' : 'Assinar'} onClick={onAssinar} green />}
      </div>
    </div>
  );
}
const Mini = ({ icon: Icon, label, onClick, green }) => (
  <button onClick={onClick}
    className={`inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-md border ${green ? 'border-emerald-600 text-emerald-700 hover:bg-emerald-50' : 'hover:bg-gray-50'}`}>
    <Icon className="w-3.5 h-3.5" /> {label}
  </button>
);
const BtnDown = ({ icon: Icon, label, onClick }) => (
  <button onClick={onClick}
    className="inline-flex items-center gap-2 text-sm px-4 py-2 rounded-lg border hover:bg-gray-50" style={{ color: GREEN }}>
    <Icon className="w-4 h-4" /> {label}
  </button>
);
