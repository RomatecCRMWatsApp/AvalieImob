// @module dashboard/conformidade/PainelConformidade — Painel COFECI/CNAI (Feature 05).
// Alertas de vencimento de credenciais, PTAM sem ART e metas. 3 abas.
import React, { useCallback, useEffect, useState } from 'react';
import {
  ShieldCheck, RefreshCw, Bell, CreditCard, Settings as Cog,
  Plus, Loader2, CheckCircle2, Trash2,
} from 'lucide-react';
import { conformidadeAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const STATUS_CONFIG = {
  ok: { color: 'text-emerald-600', bg: 'bg-emerald-50', dot: '🟢', label: 'Em dia' },
  aviso: { color: 'text-yellow-600', bg: 'bg-yellow-50', dot: '🟡', label: 'Atenção' },
  urgente: { color: 'text-orange-600', bg: 'bg-orange-50', dot: '🟠', label: 'Urgente' },
  vencida: { color: 'text-red-600', bg: 'bg-red-50', dot: '🔴', label: 'Vencida' },
};

const SEV_CONFIG = {
  info: { border: 'border-blue-200', bg: 'bg-blue-50', icon: 'ℹ️' },
  aviso: { border: 'border-yellow-200', bg: 'bg-yellow-50', icon: '⚠️' },
  urgente: { border: 'border-red-200', bg: 'bg-red-50', icon: '🔴' },
};

const TIPO_LABELS = {
  cnai: 'CNAI', creci: 'CRECI', cft: 'CFT', crea: 'CREA',
  ecpf_icpbrasil: 'e-CPF ICP-Brasil', art_cft: 'ART/CFT', outro: 'Outro',
};

const INPUT = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none';

export default function PainelConformidade() {
  const { toast } = useToast();
  const [dashboard, setDashboard] = useState(null);
  const [alertas, setAlertas] = useState([]);
  const [tab, setTab] = useState('alertas');
  const [verificando, setVerificando] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [dash, als] = await Promise.all([
        conformidadeAPI.dashboard(),
        conformidadeAPI.listarAlertas(),
      ]);
      setDashboard(dash);
      setAlertas(als || []);
    } catch (e) {
      toast({ title: 'Erro ao carregar conformidade', description: e.response?.data?.detail, variant: 'destructive' });
    }
  }, [toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const verificarAgora = async () => {
    setVerificando(true);
    try {
      const r = await conformidadeAPI.verificarAgora();
      await carregar();
      toast({ title: `Verificação concluída`, description: `${r.alertas_gerados} novo(s) alerta(s).` });
    } catch (e) {
      toast({ title: 'Erro na verificação', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setVerificando(false);
    }
  };

  const marcarLido = async (id) => {
    setAlertas((a) => a.map((al) => (al.id === id ? { ...al, lido: true } : al)));
    try { await conformidadeAPI.marcarLido(id); } catch { /* otimista */ }
  };

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-700" /> Conformidade
          </h2>
          <p className="text-sm text-gray-500">COFECI · CNAI · CFT · CREA · ICP-Brasil</p>
        </div>
        <button onClick={verificarAgora} disabled={verificando}
          className="flex items-center gap-2 text-sm bg-emerald-700 text-white px-4 py-2 rounded-xl font-semibold disabled:opacity-60">
          {verificando ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {verificando ? 'Verificando...' : 'Verificar agora'}
        </button>
      </div>

      {dashboard && (
        <div className="grid grid-cols-2 gap-3">
          <div className={`rounded-xl p-4 ${dashboard.alertas_urgentes > 0 ? 'bg-red-50 border border-red-200' : 'bg-gray-50'}`}>
            <p className="text-2xl font-bold text-red-600">{dashboard.alertas_urgentes}</p>
            <p className="text-xs text-gray-500 mt-0.5">Alertas urgentes</p>
          </div>
          <div className={`rounded-xl p-4 ${dashboard.alertas_avisos > 0 ? 'bg-yellow-50 border border-yellow-200' : 'bg-gray-50'}`}>
            <p className="text-2xl font-bold text-yellow-600">{dashboard.alertas_avisos}</p>
            <p className="text-xs text-gray-500 mt-0.5">Avisos pendentes</p>
          </div>
        </div>
      )}

      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
        {[['alertas', Bell, 'Alertas'], ['credenciais', CreditCard, 'Credenciais'], ['config', Cog, 'Config']].map(([t, Icon, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 flex items-center justify-center gap-1.5 text-xs py-2 rounded-lg font-medium transition-colors ${tab === t ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500'}`}>
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      {tab === 'alertas' && (
        <div className="space-y-2">
          {alertas.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <CheckCircle2 className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Nenhum alerta pendente</p>
            </div>
          )}
          {alertas.map((al) => {
            const sev = SEV_CONFIG[al.severidade] || SEV_CONFIG.info;
            return (
              <div key={al.id} className={`rounded-xl border p-4 space-y-1 ${al.lido ? 'opacity-50' : ''} ${sev.bg} ${sev.border}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span>{sev.icon}</span>
                    <p className="text-sm font-semibold text-gray-800">{al.titulo}</p>
                  </div>
                  {!al.lido && (
                    <button onClick={() => marcarLido(al.id)} className="text-xs text-gray-400 hover:text-gray-600 whitespace-nowrap">Lido</button>
                  )}
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">{al.descricao}</p>
                <p className="text-xs text-gray-400">{al.created_at ? new Date(al.created_at).toLocaleDateString('pt-BR') : ''}</p>
              </div>
            );
          })}
        </div>
      )}

      {tab === 'credenciais' && <AbaCredenciais dashboard={dashboard} onMudou={carregar} />}
      {tab === 'config' && <ConfigForm />}
    </div>
  );
}

function AbaCredenciais({ dashboard, onMudou }) {
  const { toast } = useToast();
  const [showAdd, setShowAdd] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [nova, setNova] = useState({ tipo: 'cnai', numero: '', orgao_emissor: '', titular: '', validade: '', alerta_dias: 60 });

  const salvar = async () => {
    if (!nova.numero || !nova.validade) { toast({ title: 'Preencha número e validade', variant: 'destructive' }); return; }
    setSalvando(true);
    try {
      await conformidadeAPI.criarCredencial(nova);
      setShowAdd(false);
      setNova({ tipo: 'cnai', numero: '', orgao_emissor: '', titular: '', validade: '', alerta_dias: 60 });
      await onMudou();
      toast({ title: 'Credencial cadastrada' });
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSalvando(false); }
  };

  const creds = dashboard?.credenciais || [];

  return (
    <div className="space-y-3">
      {creds.length === 0 && !showAdd && (
        <div className="text-center py-8 text-gray-400">
          <CreditCard className="w-10 h-10 mx-auto mb-2 opacity-40" />
          <p className="text-sm">Nenhuma credencial cadastrada</p>
        </div>
      )}
      {creds.map((cred) => {
        const cfg = STATUS_CONFIG[cred.status] || STATUS_CONFIG.ok;
        return (
          <div key={cred.tipo + cred.numero} className={`rounded-xl border p-4 flex items-center justify-between ${cfg.bg}`}>
            <div>
              <div className="flex items-center gap-2">
                <span>{cfg.dot}</span>
                <span className="font-semibold text-gray-800">{TIPO_LABELS[cred.tipo] || cred.tipo}</span>
                <span className="text-xs text-gray-500">{cred.numero}</span>
              </div>
              <p className="text-xs text-gray-500 mt-0.5 ml-6">
                Válido até {cred.validade}
                {cred.dias_restantes >= 0 ? ` · ${cred.dias_restantes} dias restantes` : ` · VENCIDA há ${Math.abs(cred.dias_restantes)} dias`}
              </p>
            </div>
            <span className={`text-xs font-semibold ${cfg.color}`}>{cfg.label}</span>
          </div>
        );
      })}

      {!showAdd ? (
        <button onClick={() => setShowAdd(true)}
          className="w-full flex items-center justify-center gap-2 border-2 border-dashed border-emerald-300 text-emerald-700 text-sm py-3 rounded-xl font-semibold hover:bg-emerald-50 transition-colors">
          <Plus className="w-4 h-4" /> Adicionar credencial
        </button>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <h4 className="font-semibold text-gray-800 text-sm">Nova credencial</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500">Tipo</label>
              <select className={INPUT} value={nova.tipo} onChange={(e) => setNova((n) => ({ ...n, tipo: e.target.value }))}>
                {Object.entries(TIPO_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Número</label>
              <input className={INPUT} value={nova.numero} onChange={(e) => setNova((n) => ({ ...n, numero: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Órgão emissor</label>
              <input className={INPUT} value={nova.orgao_emissor} placeholder="ex: COFECI, CFT/MA" onChange={(e) => setNova((n) => ({ ...n, orgao_emissor: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Validade</label>
              <input className={INPUT} type="date" value={nova.validade} onChange={(e) => setNova((n) => ({ ...n, validade: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500">Titular</label>
              <input className={INPUT} value={nova.titular} onChange={(e) => setNova((n) => ({ ...n, titular: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Alertar com (dias)</label>
              <input className={INPUT} type="number" value={nova.alerta_dias} onChange={(e) => setNova((n) => ({ ...n, alerta_dias: parseInt(e.target.value) || 60 }))} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={salvar} disabled={salvando} className="flex-1 bg-emerald-700 text-white text-sm py-2 rounded-xl font-semibold disabled:opacity-60">
              {salvando ? 'Salvando...' : 'Salvar'}
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 border border-gray-200 text-gray-500 text-sm py-2 rounded-xl">Cancelar</button>
          </div>
        </div>
      )}
    </div>
  );
}

function ConfigForm() {
  const { toast } = useToast();
  const [config, setConfig] = useState({
    meta_ptams_mes: 0, alerta_credencial: true, alerta_ptam_sem_art: true,
    alerta_normas: true, alerta_metas: true, prazo_art_dias: 30, notificar_telegram: true,
  });
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    conformidadeAPI.obterConfig().then((d) => { if (d) setConfig((c) => ({ ...c, ...d })); }).catch(() => {});
  }, []);

  const set = (k, v) => setConfig((c) => ({ ...c, [k]: v }));

  const salvar = async () => {
    setSalvando(true);
    try {
      await conformidadeAPI.salvarConfig(config);
      toast({ title: 'Configurações salvas' });
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSalvando(false); }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4 space-y-4">
      <div>
        <label className="text-xs text-gray-500 font-medium">Meta de PTAMs por mês</label>
        <input className={INPUT} type="number" value={config.meta_ptams_mes} onChange={(e) => set('meta_ptams_mes', parseInt(e.target.value) || 0)} />
        <p className="text-xs text-gray-400 mt-1">0 = sem meta definida</p>
      </div>
      <div>
        <label className="text-xs text-gray-500 font-medium">Prazo para alertar PTAM sem ART (dias)</label>
        <input className={INPUT} type="number" value={config.prazo_art_dias} onChange={(e) => set('prazo_art_dias', parseInt(e.target.value) || 30)} />
      </div>
      <div className="space-y-2">
        {[
          ['alerta_credencial', 'Alertar credenciais vencendo'],
          ['alerta_ptam_sem_art', 'Alertar PTAMs sem ART'],
          ['alerta_normas', 'Alertar atualizações de norma'],
          ['alerta_metas', 'Alertar progresso de meta'],
          ['notificar_telegram', 'Enviar alertas pelo Telegram'],
        ].map(([k, label]) => (
          <label key={k} className="flex items-center gap-3 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" checked={!!config[k]} onChange={(e) => set(k, e.target.checked)} className="w-4 h-4 accent-emerald-700" />
            {label}
          </label>
        ))}
      </div>
      <button onClick={salvar} disabled={salvando} className="w-full bg-emerald-700 text-white font-semibold py-3 rounded-xl disabled:opacity-60">
        {salvando ? 'Salvando...' : 'Salvar configurações'}
      </button>
    </div>
  );
}
