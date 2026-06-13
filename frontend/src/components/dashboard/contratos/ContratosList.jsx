import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Loader2, Trash2, Calendar, DollarSign, Filter,
  FileSignature, FileText, Share2, PenSquare, Download, ChevronDown,
  Eye, FileDown, Lock, MapPin, RefreshCw, Copy, MessageCircle, Link2,
  History, ShieldCheck, X, Send,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { contratosAPI } from '../../../lib/api';
import AssinaturaPosicionadaModal from '../assinatura/AssinaturaPosicionadaModal';
import AssinaturaDigital from '../ptam/AssinaturaDigital';
import TypeCardGrid from '../shared/TypeCardGrid';
import { CONTRATO_TIPOS, CONTRATO_CATEGORIAS } from '../../../constants/contratoTipos';
import { getWizardConfig } from '../../../constants/contratoWizardConfig';

/* ── Ciclo de vida do card (status_card vindo do backend) ─────────────────────
   Espelha o círculo de status do PTAM (spec PR-4 §2). */
const STATUS_CARD = {
  rascunho:   { cor: '#9ca3af', fundo: '#9ca3af22', texto: 'RASCUNHO',  label: 'Minuta' },
  concluido:  { cor: '#3b82f6', fundo: '#3b82f622', texto: 'CONCLUÍDO', label: 'Definitivo' },
  assinado:   { cor: '#0C3320', fundo: '#0C332022', texto: 'ASSINADO',  label: 'Assinado' },
  ativo:      { cor: '#0C3320', fundo: '#0C332022', texto: 'ATIVO',     label: 'Vigente' },
  denunciado: { cor: '#f59e0b', fundo: '#f59e0b22', texto: 'DENÚNCIA',  label: 'Denunciado' },
  encerrado:  { cor: '#374151', fundo: '#37415122', texto: 'ENCERRADO', label: 'Encerrado' },
  rescindido: { cor: '#dc2626', fundo: '#dc262622', texto: 'RESCINDIDO',label: 'Rescindido' },
};

const statusCardOf = (c) => STATUS_CARD[c?.status_card] || STATUS_CARD.rascunho;

/* % de etapas concluídas (auditoria) — alimenta o badge de andamento no card */
const andamentoPct = (c) => {
  const ec = c?.etapas_concluidas || {};
  const total = getWizardConfig(c?.tipo_contrato)?.etapas?.length || 1;
  const feitas = Object.values(ec).filter(Boolean).length;
  return Math.min(100, Math.round((feitas / total) * 100));
};

/* ── Círculo de status (SVG) — mesmo conceito do PTAM, cores do ciclo do contrato */
const ContratoStatusCircle = ({ status, data }) => {
  const cfg = STATUS_CARD[status] || STATUS_CARD.rascunho;
  const r = 30;
  const c = 2 * Math.PI * r;
  const pct = status === 'rascunho' ? 0.35 : 1;
  const dataFmt = data
    ? new Date(data).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
    : '';
  return (
    <svg width="76" height="76" viewBox="0 0 76 76" className="flex-shrink-0">
      <circle cx="38" cy="38" r={r} fill="none" stroke={cfg.fundo} strokeWidth="6" />
      <circle
        cx="38" cy="38" r={r} fill="none" stroke={cfg.cor} strokeWidth="6"
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
        transform="rotate(-90 38 38)"
      />
      <text x="38" y="34" textAnchor="middle" fontSize="8" fontWeight="700" fill={cfg.cor}>
        {cfg.texto}
      </text>
      {dataFmt && (
        <text x="38" y="46" textAnchor="middle" fontSize="8" fill="#9ca3af">{dataFmt}</text>
      )}
    </svg>
  );
};

/* ── Tipo config ─────────────────────────────────────────── */
const TIPO_CONFIG = {
  compra_venda:          { label: 'Compra e Venda' },
  promessa_compra_venda: { label: 'Promessa C&V' },
  permuta:               { label: 'Permuta' },
  doacao:                { label: 'Doação' },
  locacao_residencial:   { label: 'Locação Residencial' },
  locacao_comercial:     { label: 'Locação Comercial' },
  comodato:              { label: 'Comodato' },
  arras:                 { label: 'Arras / Sinal' },
  intermediacao:         { label: 'Intermediação' },
  exclusividade:         { label: 'Exclusividade' },
  cessao_direitos:       { label: 'Cessão de Direitos' },
  usufruto:              { label: 'Usufruto' },
  parceria_rural:        { label: 'Parceria Rural' },
  arrendamento_rural:    { label: 'Arrendamento Rural' },
  compra_venda_veiculo:  { label: 'C&V Veículo' },
  distrato:              { label: 'Distrato' },
};

/* ── Filter options ─────────────────────────────────────── */
const TIPO_OPTIONS = [
  { value: '', label: 'Todos os tipos' },
  ...Object.entries(TIPO_CONFIG).map(([value, { label }]) => ({ value, label })),
];

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'concluido', label: 'Concluído' },
  { value: 'assinado', label: 'Assinado' },
  { value: 'ativo', label: 'Ativo' },
  { value: 'denunciado', label: 'Denunciado' },
  { value: 'encerrado', label: 'Encerrado' },
  { value: 'rescindido', label: 'Rescindido' },
];

const fmtCurrency = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtDate = (s) => (s ? new Date(s).toLocaleDateString('pt-BR') : '—');
const fmtDateTime = (s) =>
  s ? new Date(s).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';

const getContratoId = (contrato) => contrato?.id || contrato?._id || null;

const getParteNome = (parte) => {
  if (!parte) return '';
  return (
    parte.nome ||
    parte.razao_social ||
    parte.pf?.nome ||
    parte.pj?.razao_social ||
    parte.pj?.nome_fantasia ||
    parte.pj?.representante_nome ||
    ''
  );
};

const numeroDisplay = (c) =>
  c.numero_display || c.numero_contrato || c.numero || 'Sem número';

const isAssinado = (c) => c?.icp_status === 'assinado' || c?.d4sign_status === 'assinado';

/* ── Download helpers (as novas APIs retornam o Blob direto) ─────────────────── */
const saveBlob = (blob, filename) => {
  const real = blob instanceof Blob ? blob : new Blob([blob]);
  const url = URL.createObjectURL(real);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
};

const downloadVia = async (apiFn, id, filename, toast) => {
  try {
    saveBlob(await apiFn(id), filename);
  } catch {
    toast({ title: `Erro ao baixar ${filename}`, variant: 'destructive' });
  }
};

/* ── Modal de histórico do link público ─────────────────────────────────────── */
const HistoricoModal = ({ contrato, onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const id = getContratoId(contrato);

  useEffect(() => {
    let alive = true;
    contratosAPI.linkEventos(id)
      .then((r) => { if (alive) setData(r); })
      .catch(() => { if (alive) setData({ eventos: [], resumo: {} }); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [id]);

  const ev = data?.eventos || [];
  const resumo = data?.resumo || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-700" />
            <h3 className="font-semibold text-gray-900">Histórico — {numeroDisplay(contrato)}</h3>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-400 hover:text-gray-700" /></button>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="rounded-xl bg-blue-50 p-3">
              <div className="flex items-center gap-1.5 text-blue-700 text-xs"><Eye className="w-3.5 h-3.5" /> Visualizações</div>
              <div className="text-2xl font-bold text-blue-800">{resumo.views || 0}</div>
            </div>
            <div className="rounded-xl bg-emerald-50 p-3">
              <div className="flex items-center gap-1.5 text-emerald-700 text-xs"><Send className="w-3.5 h-3.5" /> Envios</div>
              <div className="text-2xl font-bold text-emerald-800">{resumo.sends || 0}</div>
            </div>
          </div>
          {loading ? (
            <div className="py-8 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-emerald-700" /></div>
          ) : ev.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-6">Nenhum evento registrado ainda.</p>
          ) : (
            <ul className="space-y-2">
              {ev.map((e, i) => (
                <li key={e.id || i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
                  <div>
                    <span className="font-medium text-gray-800 capitalize">{e.tipo}</span>
                    {e.canal && <span className="text-gray-500"> · {e.canal}</span>}
                    {e.destinatario && <span className="text-gray-500"> · {e.destinatario}</span>}
                    <div className="text-xs text-gray-400">{fmtDateTime(e.created_at)}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

/* ── Menu de overflow (ações secundárias) ───────────────────────────────────── */
const CardActions = ({ contrato, onEdit, onDelete, onClonar, toast }) => {
  const [open, setOpen] = useState(false);
  const id = getContratoId(contrato);
  const ativo = contrato?.status_card === 'ativo';

  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-2 py-1 hover:bg-gray-50 transition"
      >
        Ações <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          className="absolute right-0 bottom-full mb-1 w-44 bg-white border border-gray-200 rounded-xl shadow-xl py-1 z-50"
          onMouseLeave={() => setOpen(false)}
        >
          <button onClick={() => { setOpen(false); onEdit(); }} className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
            <PenSquare className="w-3.5 h-3.5 text-gray-400" /> Editar
          </button>
          <button disabled={!id} onClick={() => { setOpen(false); downloadVia(contratosAPI.docx, id, `contrato-${id}.docx`, toast); }} className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
            <Download className="w-3.5 h-3.5 text-blue-500" /> Baixar DOCX
          </button>
          <button disabled={!id} onClick={() => { setOpen(false); downloadVia(contratosAPI.reciboArrasDocx, id, `recibo-arras-${id}.docx`, toast); }} className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
            <FileText className="w-3.5 h-3.5 text-amber-500" /> Recibo de Arras
          </button>
          <button disabled={!id} onClick={() => { setOpen(false); onClonar(); }} className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
            <Copy className="w-3.5 h-3.5 text-emerald-600" /> Clonar
          </button>
          <div className="border-t border-gray-100 mt-0.5 pt-0.5">
            <button
              onClick={() => { setOpen(false); onDelete(); }}
              disabled={ativo}
              title={ativo ? 'Rescinda o contrato antes de excluir' : ''}
              className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-3.5 h-3.5" /> Excluir
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

/* ── Botão de ação compacto ─────────────────────────────────────────────────── */
const ActBtn = ({ icon: Icon, label, onClick, className = '', disabled = false, title }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    title={title || label}
    className={`flex items-center justify-center gap-1 text-[11px] font-medium rounded-lg px-2 py-1.5 border transition disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
  >
    <Icon className="w-3.5 h-3.5" /> {label}
  </button>
);

/* ── Main component ──────────────────────────────────────── */
const ContratosList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterTipo, setFilterTipo] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [search, setSearch] = useState('');
  const [assinarDoc, setAssinarDoc] = useState(null);
  const [posicionarDoc, setPosicionarDoc] = useState(null);
  const [historicoDoc, setHistoricoDoc] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterTipo) params.tipo_contrato = filterTipo;
      // status é do ciclo PR-4 (status_card, derivado) → filtra no cliente
      setItems(await contratosAPI.listar(params));
    } catch (err) {
      if (process.env.NODE_ENV === 'development') console.warn(err);
      toast({ title: 'Erro ao carregar contratos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast, filterTipo]);

  useEffect(() => { load(); }, [load]);

  const criarDoTipo = async (tipo) => {
    if (!tipo || tipo.status === 'em_breve') return;
    try {
      const novo = await contratosAPI.criar({ tipo_contrato: tipo.id });
      // abre o wizard já na etapa 2 (Partes), pulando a etapa Tipo
      nav(`/dashboard/contratos/${getContratoId(novo)}`, { state: { startStep: 1 } });
    } catch {
      toast({ title: 'Erro ao criar contrato', variant: 'destructive' });
    }
  };

  const remove = async (id, c) => {
    if (!id) { toast({ title: 'Contrato sem ID válido', variant: 'destructive' }); return; }
    if (c?.status_card === 'ativo') {
      toast({ title: 'Contrato ativo', description: 'Rescinda o contrato antes de excluir.', variant: 'destructive' });
      return;
    }
    if (!window.confirm('Excluir este contrato? Esta ação não pode ser desfeita.')) return;
    try {
      await contratosAPI.excluir(id);
      setItems(items.filter((x) => getContratoId(x) !== id));
      toast({ title: 'Contrato excluído' });
    } catch {
      toast({ title: 'Erro ao excluir', variant: 'destructive' });
    }
  };

  const clonar = async (id) => {
    try {
      const novo = await contratosAPI.clonar(id);
      toast({ title: 'Contrato clonado', description: `Novo: ${numeroDisplay(novo)}` });
      load();
    } catch {
      toast({ title: 'Erro ao clonar', variant: 'destructive' });
    }
  };

  const visualizarPdf = async (id) => {
    try {
      const blob = await contratosAPI.pdf(id);
      const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' }));
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      let detalhe = '';
      try {
        const data = e?.response?.data;
        detalhe = data instanceof Blob ? (JSON.parse(await data.text())?.detail || '') : (data?.detail || '');
      } catch { /* ignore */ }
      toast({ title: 'Erro ao gerar PDF', description: detalhe || undefined, variant: 'destructive' });
    }
  };

  const zerarAssinatura = async (id) => {
    if (!window.confirm('Remover a assinatura deste contrato? O PDF assinado será apagado e o status volta para Minuta.')) return;
    try {
      await contratosAPI.zerarAssinatura(id);
      toast({ title: 'Assinatura removida' });
      load();
    } catch {
      toast({ title: 'Erro ao zerar assinatura', variant: 'destructive' });
    }
  };

  const compartilhar = async (id) => {
    try {
      const r = await contratosAPI.compartilhar(id);
      const url = `${window.location.origin}${r.url || `/contrato/public/${r.token}`}`;
      await navigator.clipboard?.writeText(url);
      toast({ title: 'Link copiado!', description: 'Compartilhamento público ativado.' });
      return url;
    } catch {
      toast({ title: 'Erro ao compartilhar', variant: 'destructive' });
      return null;
    }
  };

  const enviarWhatsApp = async (c) => {
    const id = getContratoId(c);
    const url = await compartilhar(id);
    if (!url) return;
    const msg = `Olá! Segue o contrato ${numeroDisplay(c)} para visualização: ${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank');
  };

  /* filtros client-side: status (ciclo PR-4) + busca por partes */
  const filtered = items.filter((c) => {
    if (filterStatus && (c.status_card || 'rascunho') !== filterStatus) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const partes = [
        c.vendedores?.map(getParteNome)?.join(' ') || '',
        c.compradores?.map(getParteNome)?.join(' ') || '',
        numeroDisplay(c),
        c.objeto?.endereco || '',
      ].join(' ').toLowerCase();
      if (!partes.includes(q)) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileSignature className="w-6 h-6 text-[#C9A84C]" />
            <h1 className="font-display text-[34px] font-bold leading-tight text-[#C9A84C]">Contratos</h1>
          </div>
          <p className="text-sm mt-1 text-[#5B7466] dark:text-[#9FB5A6]">
            Compra e venda, locação, arras, permuta, intermediação e mais — com IA jurídica e assinatura ICP-Brasil.
          </p>
        </div>
        <Button onClick={() => nav('/dashboard/contratos/novo')} className="bg-emerald-900 hover:bg-emerald-800 text-white">
          <Plus className="w-4 h-4 mr-2" /> Novo Contrato
        </Button>
      </div>

      {/* Novo contrato — escolha o tipo */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-[#F2EFE6]">Novo contrato — escolha o tipo</h2>
        <TypeCardGrid tipos={CONTRATO_TIPOS} categorias={CONTRATO_CATEGORIAS} onPick={criarDoTipo} />
      </div>

      {/* Contratos existentes */}
      <h2 className="text-sm font-semibold text-gray-700 dark:text-[#F2EFE6] pt-2">
        Contratos existentes {items.length > 0 && <span className="text-gray-400 font-normal">· {items.length}</span>}
      </h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center bg-white border border-gray-200 rounded-xl p-4">
        <Filter className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nome das partes..."
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 min-w-[200px]"
        />
        <select value={filterTipo} onChange={(e) => setFilterTipo(e.target.value)} className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
          {TIPO_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {(filterTipo || filterStatus || search) && (
          <button onClick={() => { setFilterTipo(''); setFilterStatus(''); setSearch(''); }} className="text-xs text-red-500 hover:text-red-700 underline">
            Limpar filtros
          </button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-200">
          <FileSignature className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhum contrato encontrado</div>
          <p className="text-sm text-gray-500 mt-1">
            {filterTipo || filterStatus || search ? 'Tente outros filtros ou limpe a busca.' : 'Clique em "Novo Contrato" para começar.'}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((c, idx) => {
            const contratoId = getContratoId(c);
            const cfg = statusCardOf(c);
            const tipoContrato = c.tipo_contrato || c.tipo;
            const tipoCfg = TIPO_CONFIG[tipoContrato] || { label: tipoContrato || 'Contrato' };
            const assinado = isAssinado(c);
            const partesPrinc = [
              ...(c.vendedores || []).map(getParteNome).filter(Boolean),
              ...(c.compradores || []).map(getParteNome).filter(Boolean),
            ].filter(Boolean);

            return (
              <div
                key={contratoId || c.numero_contrato || c.numero || `contrato-${idx}`}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition flex flex-col"
              >
                {/* Header: ícone + número/tipo + círculo de status */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="w-9 h-9 rounded-lg bg-emerald-900/10 flex items-center justify-center flex-shrink-0">
                        <FileSignature className="w-4 h-4 text-emerald-900" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-emerald-700 tracking-wider">{numeroDisplay(c)}</div>
                        <Badge className="bg-gray-100 text-gray-700 text-[10px] mt-0.5">{tipoCfg.label}</Badge>
                      </div>
                    </div>
                  </div>
                  <ContratoStatusCircle status={c.status_card} data={c.updated_at} />
                </div>

                <div className="font-semibold text-gray-900 mt-3 line-clamp-1">
                  {partesPrinc.length > 0 ? partesPrinc.join(' / ') : '(partes não informadas)'}
                </div>
                <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                  {c.objeto?.endereco || c.objeto?.descricao || '—'}
                </div>
                {c.tipo_contrato === 'exclusividade' && c.status_card === 'rascunho' && (
                  <div className="mt-1.5">
                    <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {andamentoPct(c)}% preenchido
                    </span>
                  </div>
                )}

                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs text-gray-600">
                    <DollarSign className="w-3 h-3" /> {fmtCurrency(c.pagamento?.valor_total)}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Calendar className="w-3 h-3" /> {fmtDate(c.updated_at)}
                  </div>
                </div>

                {/* Linha 1 — abrir / visualizar / pdf */}
                <div className="grid grid-cols-3 gap-1.5 mt-3" onClick={(e) => e.stopPropagation()}>
                  <ActBtn icon={PenSquare} label="Abrir" onClick={() => contratoId && nav(`/dashboard/contratos/${contratoId}`)} className="border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100" />
                  <ActBtn icon={Eye} label="Ver" onClick={() => visualizarPdf(contratoId)} className="border-gray-200 text-gray-700 hover:bg-gray-50" />
                  <ActBtn icon={FileDown} label="PDF" onClick={() => downloadVia(contratosAPI.pdf, contratoId, `contrato-${contratoId}.pdf`, toast)} className="border-gray-200 text-gray-700 hover:bg-gray-50" />
                </div>

                {/* Linha 2 — assinatura */}
                <div className="grid grid-cols-2 gap-1.5 mt-1.5" onClick={(e) => e.stopPropagation()}>
                  <ActBtn icon={Lock} label="Assinar" onClick={() => setAssinarDoc(c)} className="border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100" />
                  <ActBtn icon={MapPin} label="Posicionar" onClick={() => setPosicionarDoc(c)} className="border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100" />
                  {assinado && (
                    <>
                      <ActBtn icon={ShieldCheck} label="PDF Assinado" onClick={() => downloadVia(contratosAPI.pdfAssinado, contratoId, `contrato-${contratoId}-assinado.pdf`, toast)} className="border-emerald-300 bg-emerald-600 text-white hover:bg-emerald-700 col-span-1" />
                      <ActBtn icon={RefreshCw} label="Zerar assin." onClick={() => zerarAssinatura(contratoId)} className="border-red-200 bg-red-50 text-red-700 hover:bg-red-100" />
                    </>
                  )}
                </div>

                {/* Linha 3 — distribuição */}
                <div className="grid grid-cols-3 gap-1.5 mt-1.5" onClick={(e) => e.stopPropagation()}>
                  <ActBtn icon={MessageCircle} label="WhatsApp" onClick={() => enviarWhatsApp(c)} className="border-green-200 bg-green-50 text-green-700 hover:bg-green-100" />
                  <ActBtn icon={Link2} label="Link" onClick={() => compartilhar(contratoId)} className="border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100" />
                  <ActBtn icon={History} label="Histórico" onClick={() => setHistoricoDoc(c)} className="border-gray-200 text-gray-600 hover:bg-gray-50" />
                </div>

                {/* Footer — contadores + recibo + overflow */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><Eye className="w-3.5 h-3.5 text-blue-500" /> {c.link_views || 0}</span>
                    <span className="flex items-center gap-1"><Send className="w-3.5 h-3.5 text-emerald-600" /> {c.link_sends || 0}</span>
                    {c.recibo_assinado ? (
                      <span className="text-emerald-700 font-medium">✓ Recibo assinado</span>
                    ) : c.recibo_emitido ? (
                      <span className="text-emerald-600">✓ Recibo emitido</span>
                    ) : null}
                  </div>
                  <CardActions
                    contrato={c}
                    onEdit={() => contratoId && nav(`/dashboard/contratos/${contratoId}`)}
                    onDelete={() => remove(contratoId, c)}
                    onClonar={() => clonar(contratoId)}
                    toast={toast}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modais (reuso 1:1 do motor de assinatura do PTAM) */}
      {assinarDoc && (
        <AssinaturaDigital
          tipo="contrato"
          docId={getContratoId(assinarDoc)}
          docData={assinarDoc}
          onClose={() => setAssinarDoc(null)}
          onUpdate={() => { setAssinarDoc(null); load(); }}
        />
      )}
      {posicionarDoc && (
        <AssinaturaPosicionadaModal
          tipo="contrato"
          documentId={getContratoId(posicionarDoc)}
          onAssinado={() => { setPosicionarDoc(null); toast({ title: 'Contrato assinado!' }); load(); }}
          onFechar={() => setPosicionarDoc(null)}
        />
      )}
      {historicoDoc && (
        <HistoricoModal contrato={historicoDoc} onClose={() => setHistoricoDoc(null)} />
      )}
    </div>
  );
};

export default ContratosList;
