import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ChevronLeft, ChevronRight, Save, Loader2, Check,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { garantiasAPI, perfilAPI } from '../../../lib/api';

// ── Shared ──────────────────────────────────────────────────────────────────
import {
  EMPTY, isBancario,
  STEPS_BANCARIO, STEPS_RURAL,
} from './steps/shared.js';

// ── Bancário steps ────────────────────────────────────────────────────────
import StepModalidade      from './steps/StepModalidade.jsx';
import StepMutuario        from './steps/StepMutuario.jsx';
import StepImovelDocs      from './steps/StepImovelDocs.jsx';
import StepVistoria        from './steps/StepVistoria.jsx';
import StepMetodologia     from './steps/StepMetodologia.jsx';
import StepResultadoBancario from './steps/StepResultadoBancario.jsx';
import StepDeclaracoes     from './steps/StepDeclaracoes.jsx';

// ── Rural steps ────────────────────────────────────────────────────────────
import StepTipo            from './steps/StepTipo.jsx';
import StepSolicitante     from './steps/StepSolicitante.jsx';
import StepBem             from './steps/StepBem.jsx';
import StepLocalizacao     from './steps/StepLocalizacao.jsx';
import StepAvaliacao       from './steps/StepAvaliacao.jsx';
import StepResultadoRural  from './steps/StepResultadoRural.jsx';
import StepConclusao       from './steps/StepConclusao.jsx';

// ── Main Wizard ───────────────────────────────────────────────────────────
const GarantiaWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();

  const isNew = !id || id === 'nova';
  const [form, setForm] = useState({ ...EMPTY });
  const [garantiaId, setGarantiaId] = useState(isNew ? null : id);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const debounceRef = useRef(null);

  const load = useCallback(async () => {
    if (!garantiaId) return;
    setLoading(true);
    try {
      const data = await garantiasAPI.get(garantiaId);
      setForm({ ...EMPTY, ...data });
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar avaliação', variant: 'destructive' });
      nav('/dashboard/garantias');
    } finally {
      setLoading(false);
    }
  }, [garantiaId, nav, toast]);

  useEffect(() => { load(); }, [load]);

  // Pre-fill technician fields from profile when creating a new Garantia
  useEffect(() => {
    if (!isNew) return;
    perfilAPI.get().then((p) => {
      if (!p) return;
      const creci = (p.registros || []).find(r => r.tipo === 'CRECI' && r.status === 'ativo');
      const cnai  = (p.registros || []).find(r => r.tipo === 'CNAI'  && r.status === 'ativo');
      const crea  = (p.registros || []).find(r => r.tipo === 'CREA'  && r.status === 'ativo');
      const cau   = (p.registros || []).find(r => r.tipo === 'CAU'   && r.status === 'ativo');

      const registroCreaOuCau = crea ? `${crea.numero}` : cau ? `${cau.numero}` : '';
      const ufRegistro = crea?.uf || cau?.uf || '';
      const tipoProf = crea ? 'engenheiro' : cau ? 'arquiteto' : '';

      setForm(f => ({
        ...f,
        responsavel: {
          ...f.responsavel,
          nome:     p.nome_completo || f.responsavel?.nome || '',
          creci:    creci ? `CRECI${creci.uf ? '/' + creci.uf : ''} ${creci.numero}` : f.responsavel?.creci || '',
          cnai:     cnai  ? `CNAI ${cnai.numero}` : f.responsavel?.cnai || '',
          registro: registroCreaOuCau || f.responsavel?.registro || '',
        },
        responsavel_crea_cau:      registroCreaOuCau || f.responsavel_crea_cau,
        responsavel_uf:            ufRegistro        || f.responsavel_uf,
        responsavel_tipo:          tipoProf           || f.responsavel_tipo,
        responsavel_empresa_cpf:   p.empresa_cnpj || p.empresa_nome || f.responsavel_empresa_cpf,
        vistoria_responsavel_nome: p.nome_completo || f.vistoria_responsavel_nome,
        municipio: f.municipio || p.cidade || '',
        uf:        f.uf        || p.uf     || '',
      }));
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useCallback(async (silent = false) => {
    setSaving(true);
    try {
      if (garantiaId) {
        await garantiasAPI.update(garantiaId, form);
      } else {
        const created = await garantiasAPI.create(form);
        setGarantiaId(created.id);
        setForm((f) => ({ ...f, numero: created.numero }));
        nav(`/dashboard/garantias/${created.id}`, { replace: true });
      }
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      console.warn(err);
      if (!silent) toast({ title: 'Erro ao salvar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [form, garantiaId, nav, toast]);

  useEffect(() => {
    if (!garantiaId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [form, garantiaId, save]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const setNested = (obj, key, value) =>
    setForm((f) => ({ ...f, [obj]: { ...(f[obj] || {}), [key]: value } }));

  const isBancarioMode = isBancario(form);
  const STEPS = isBancarioMode ? STEPS_BANCARIO : STEPS_RURAL;

  if (loading) return (
    <div className="py-20 flex justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-800" />
    </div>
  );

  const totalSteps = STEPS.length;

  const renderStep = () => {
    if (isBancarioMode) {
      switch (step) {
        case 0: return <StepModalidade form={form} set={set} />;
        case 1: return <StepMutuario form={form} set={set} />;
        case 2: return <StepImovelDocs form={form} set={set} />;
        case 3: return <StepVistoria form={form} set={set} />;
        case 4: return <StepMetodologia form={form} set={set} />;
        case 5: return <StepResultadoBancario form={form} set={set} />;
        case 6: return <StepDeclaracoes form={form} set={set} />;
        default: return null;
      }
    }
    switch (step) {
      case 0: return <StepTipo form={form} set={set} />;
      case 1: return <StepSolicitante form={form} setNested={setNested} />;
      case 2: return <StepBem form={form} set={set} />;
      case 3: return <StepLocalizacao form={form} set={set} />;
      case 4: return <StepAvaliacao form={form} set={set} />;
      case 5: return <StepResultadoRural form={form} set={set} />;
      case 6: return <StepConclusao form={form} set={set} setNested={setNested} />;
      default: return null;
    }
  };

  const getStepClasses = (i) => {
    if (i === step) return 'bg-emerald-900 text-white';
    if (i < step) return 'bg-emerald-50 text-emerald-900 hover:bg-emerald-100';
    return 'text-gray-500 hover:bg-gray-50';
  };
  const getIconClasses = (i) => {
    if (i === step) return 'bg-white/20';
    if (i < step) return 'bg-emerald-200';
    return 'bg-gray-100';
  };

  return (
    <div className="max-w-5xl mx-auto pb-20">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={() => nav('/dashboard/garantias')}>
          <ArrowLeft className="w-4 h-4 mr-1" />Voltar
        </Button>
        <div className="flex items-center gap-2">
          {isBancarioMode && (
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full font-medium">
              Res. CMN 4.676/2018
            </span>
          )}
          {lastSaved && (
            <span className="text-xs text-gray-500">Salvo {lastSaved.toLocaleTimeString('pt-BR')}</span>
          )}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar rascunho'}
          </Button>
        </div>
      </div>

      {/* Progress */}
      <div className="mb-2 flex items-center justify-between text-xs text-gray-500 px-1">
        <span>Passo {step + 1} de {totalSteps}</span>
        <span>{Math.round(((step + 1) / totalSteps) * 100)}% concluído</span>
      </div>
      <div className="mb-4 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-700 rounded-full transition-all duration-300"
          style={{ width: `${((step + 1) / totalSteps) * 100}%` }}
        />
      </div>

      {/* Stepper tabs */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 mb-6">
        <div className="flex items-center gap-1 overflow-x-auto">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => setStep(i)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs font-medium transition ${getStepClasses(i)}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${getIconClasses(i)}`}>
                  {i < step ? <Check className="w-3 h-3" /> : <Icon className="w-3 h-3" />}
                </div>
                <span className="whitespace-nowrap">{i + 1}. {s.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step content */}
      <div className="bg-white rounded-xl border border-gray-200 p-8">
        {renderStep()}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <Button variant="outline" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
          <ChevronLeft className="w-4 h-4 mr-1" />Anterior
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar'}
          </Button>
          {step < totalSteps - 1 ? (
            <Button
              className="bg-emerald-900 hover:bg-emerald-800 text-white"
              onClick={() => { save(true); setStep(step + 1); }}
            >
              Próximo<ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          ) : (
            <Button
              className="bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold"
              onClick={() => { set('status', 'concluido'); save(false); }}
              disabled={saving}
            >
              <Check className="w-4 h-4 mr-1" />Concluir Avaliação
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default GarantiaWizard;
