import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ChevronLeft, ChevronRight, Save, Loader2, Check,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { semoventesAPI, perfilAPI } from '../../../lib/api';

// ── Shared ──────────────────────────────────────────────────────────────────
import { EMPTY, STEPS } from './steps/shared.js';

// ── Steps ──────────────────────────────────────────────────────────────────
import Step1Tipo           from './steps/Step1Tipo.jsx';
import Step2Devedor        from './steps/Step2Devedor.jsx';
import Step3Rebanho        from './steps/Step3Rebanho.jsx';
import Step4Rastreabilidade from './steps/Step4Rastreabilidade.jsx';
import Step5Sanitaria      from './steps/Step5Sanitaria.jsx';
import Step6Infraestrutura from './steps/Step6Infraestrutura.jsx';
import Step7Vistoria       from './steps/Step7Vistoria.jsx';
import Step8Mercado        from './steps/Step8Mercado.jsx';
import Step9Resultado      from './steps/Step9Resultado.jsx';
import Step10Declaracoes   from './steps/Step10Declaracoes.jsx';

// ── Main Wizard ───────────────────────────────────────────────────────────
const SemoventeWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();

  const isNew = !id || id === 'nova';
  const [form, setForm] = useState({ ...EMPTY });
  const [semoventeId, setSemoventeId] = useState(isNew ? null : id);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const debounceRef = useRef(null);

  const load = useCallback(async () => {
    if (!semoventeId) return;
    setLoading(true);
    try {
      const data = await semoventesAPI.get(semoventeId);
      setForm({ ...EMPTY, ...data });
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar laudo', variant: 'destructive' });
      nav('/dashboard/semoventes');
    } finally {
      setLoading(false);
    }
  }, [semoventeId, nav, toast]);

  useEffect(() => { load(); }, [load]);

  // Pre-fill veterinarian fields from profile when creating a new Semovente
  useEffect(() => {
    if (!isNew) return;
    perfilAPI.get().then((p) => {
      if (!p) return;
      const crmv = (p.registros || []).find(r => r.tipo === 'CRMV' && r.status === 'ativo');
      setForm(f => ({
        ...f,
        responsavel_nome:      p.nome_completo || f.responsavel_nome,
        crmv_numero:           crmv?.numero    || f.crmv_numero,
        crmv_uf:               crmv?.uf        || f.crmv_uf,
        especialidade:         (p.especializacoes || []).join(', ') || f.especialidade,
        propriedade_municipio: f.propriedade_municipio || p.cidade || '',
        propriedade_uf:        f.propriedade_uf        || p.uf     || '',
      }));
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useCallback(async (silent = false) => {
    setSaving(true);
    try {
      if (semoventeId) {
        await semoventesAPI.update(semoventeId, form);
      } else {
        const created = await semoventesAPI.create(form);
        setSemoventeId(created.id);
        setForm((f) => ({ ...f, numero_laudo: created.numero_laudo }));
        nav(`/dashboard/semoventes/${created.id}`, { replace: true });
      }
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      console.warn(err);
      if (!silent) toast({ title: 'Erro ao salvar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [form, semoventeId, nav, toast]);

  // Auto-save every 30s when editing existing record
  useEffect(() => {
    if (!semoventeId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [form, semoventeId, save]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  if (loading) return (
    <div className="py-20 flex justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-800" />
    </div>
  );

  const totalSteps = STEPS.length;

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

  const renderStep = () => {
    switch (step) {
      case 0: return <Step1Tipo form={form} set={set} />;
      case 1: return <Step2Devedor form={form} set={set} />;
      case 2: return <Step3Rebanho form={form} set={set} />;
      case 3: return <Step4Rastreabilidade form={form} set={set} />;
      case 4: return <Step5Sanitaria form={form} set={set} />;
      case 5: return <Step6Infraestrutura form={form} set={set} />;
      case 6: return <Step7Vistoria form={form} set={set} />;
      case 7: return <Step8Mercado form={form} set={set} />;
      case 8: return <Step9Resultado form={form} set={set} />;
      case 9: return <Step10Declaracoes form={form} set={set} />;
      default: return null;
    }
  };

  return (
    <div className="max-w-5xl mx-auto pb-20">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => nav('/dashboard/semoventes')}>
            <ArrowLeft className="w-4 h-4 mr-1" />Voltar
          </Button>
          {form.numero_laudo && (
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              {form.numero_laudo}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {lastSaved && (
            <span className="text-xs text-gray-500">Salvo {lastSaved.toLocaleTimeString('pt-BR')}</span>
          )}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar rascunho'}
          </Button>
        </div>
      </div>

      {/* Progress bar */}
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
            const done = i < step;
            return (
              <button
                key={s.id}
                onClick={() => setStep(i)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs font-medium transition ${getStepClasses(i)}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${getIconClasses(i)}`}>
                  {done ? <Check className="w-3 h-3" /> : <Icon className="w-3 h-3" />}
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
        <Button
          variant="outline"
          onClick={() => setStep(Math.max(0, step - 1))}
          disabled={step === 0}
        >
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
              <Check className="w-4 h-4 mr-1" />Concluir Laudo
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SemoventeWizard;
