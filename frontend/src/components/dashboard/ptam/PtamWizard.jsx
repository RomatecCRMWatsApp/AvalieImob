import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as LucideIcons from 'lucide-react';
import { ChevronLeft, ChevronRight, Save, Download, ArrowLeft, Loader2, Check } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { ptamAPI, aiAPI } from '../../../lib/api';
import { EMPTY_PTAM, PTAM_STEPS, computeImpactTotals, sumIndemnity } from './ptamHelpers';
import { StepIdentification, StepProperty, StepVistoria, StepMethodology, StepImpactAreas, StepConclusion } from './PtamSteps';

const PtamWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const [form, setForm] = useState(EMPTY_PTAM);
  const [ptamId, setPtamId] = useState(id && id !== 'novo' ? id : null);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!!ptamId);
  const [saving, setSaving] = useState(false);
  const [aiLoading, setAiLoading] = useState(null);
  const [lastSaved, setLastSaved] = useState(null);
  const debounceRef = useRef(null);

  const load = useCallback(async () => {
    if (!ptamId) return;
    setLoading(true);
    try {
      const data = await ptamAPI.get(ptamId);
      setForm({ ...EMPTY_PTAM, ...data });
    } catch (err) { console.warn(err); toast({ title: 'Erro ao carregar PTAM', variant: 'destructive' }); nav('/dashboard/ptam'); }
    finally { setLoading(false); }
  }, [ptamId, nav, toast]);

  useEffect(() => { load(); }, [load]);

  const save = useCallback(async (silent = false) => {
    setSaving(true);
    try {
      const payload = { ...form, impact_areas: computeImpactTotals(form.impact_areas), total_indemnity: form.total_indemnity || sumIndemnity(form.impact_areas) };
      if (ptamId) {
        await ptamAPI.update(ptamId, payload);
      } else {
        const created = await ptamAPI.create(payload);
        setPtamId(created.id);
        setForm((f) => ({ ...f, number: created.number }));
        nav(`/dashboard/ptam/${created.id}`, { replace: true });
      }
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      console.warn(err);
      if (!silent) toast({ title: 'Erro ao salvar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally { setSaving(false); }
  }, [form, ptamId, nav, toast]);

  // Auto-save draft every 30s if there are changes
  useEffect(() => {
    if (!ptamId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [form, ptamId, save]);

  const handleAi = async (fieldKey) => {
    const isImpact = fieldKey.startsWith('impact_');
    let currentValue;
    if (isImpact) {
      const [, idx] = fieldKey.split('_');
      currentValue = form.impact_areas?.[Number(idx)]?.notes || '';
    } else {
      currentValue = form[fieldKey] || '';
    }
    const prompt = `Aperfeiçoe tecnicamente este texto para um PTAM (Parecer Técnico de Avaliação Mercadológica) conforme NBR 14.653. Mantenha tom formal, técnico, profissional em português-BR. Retorne APENAS o texto aperfeiçoado, sem explicações.\n\nCampo: ${fieldKey}\nTexto atual:\n${currentValue || '(vazio - gere um texto inicial técnico e padronizado adequado a este campo)'}`;
    setAiLoading(fieldKey);
    try {
      const session_id = `ptam_${ptamId || 'draft'}_${fieldKey}_${Date.now()}`;
      const res = await aiAPI.chat(session_id, prompt);
      if (isImpact) {
        const [, idx] = fieldKey.split('_');
        const areas = form.impact_areas.map((a, i) => i === Number(idx) ? { ...a, notes: res.reply } : a);
        setForm({ ...form, impact_areas: areas });
      } else {
        setForm({ ...form, [fieldKey]: res.reply });
      }
      toast({ title: 'Texto aperfeiçoado com IA' });
    } catch (err) { toast({ title: 'Erro na IA', description: err.response?.data?.detail || 'Tente novamente', variant: 'destructive' }); }
    finally { setAiLoading(null); }
  };

  const handleDownload = async () => {
    if (!ptamId) { toast({ title: 'Salve o PTAM primeiro', variant: 'destructive' }); return; }
    try {
      const blob = await ptamAPI.downloadDocx(ptamId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PTAM_${(form.number || 'sem-numero').replace(/\//g, '-')}.docx`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast({ title: 'Download iniciado' });
    } catch (err) { toast({ title: 'Erro ao baixar', variant: 'destructive' }); console.warn(err); }
  };

  if (loading) return <div className="py-20 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-emerald-800" /></div>;

  const stepProps = { form, setForm, onAi: handleAi, aiLoading };
  const renderStep = () => {
    if (step === 0) return <StepIdentification {...stepProps} />;
    if (step === 1) return <StepProperty {...stepProps} />;
    if (step === 2) return <StepVistoria {...stepProps} />;
    if (step === 3) return <StepMethodology {...stepProps} />;
    if (step === 4) return <StepImpactAreas {...stepProps} />;
    if (step === 5) return <StepConclusion {...stepProps} />;
    return null;
  };

  return (
    <div className="max-w-5xl mx-auto pb-20">
      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={() => nav('/dashboard/ptam')}><ArrowLeft className="w-4 h-4 mr-1" />Voltar</Button>
        <div className="flex items-center gap-2">
          {lastSaved && <span className="text-xs text-gray-500">Salvo {lastSaved.toLocaleTimeString('pt-BR')}</span>}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}><Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar rascunho'}</Button>
          <Button className="bg-emerald-900 hover:bg-emerald-800 text-white" onClick={handleDownload}><Download className="w-4 h-4 mr-1" />Baixar DOCX</Button>
        </div>
      </div>

      {/* Stepper */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex items-center gap-1 overflow-x-auto">
          {PTAM_STEPS.map((s, i) => {
            const Icon = LucideIcons[s.icon] || LucideIcons.Circle;
            const active = i === step;
            const done = i < step;
            return (
              <button key={s.id} onClick={() => setStep(i)} className={`flex-1 min-w-[120px] flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${active ? 'bg-emerald-900 text-white' : done ? 'bg-emerald-50 text-emerald-900 hover:bg-emerald-100' : 'text-gray-500 hover:bg-gray-50'}`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${active ? 'bg-white/20' : done ? 'bg-emerald-200' : 'bg-gray-100'}`}>{done ? <Check className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}</div>
                <span className="whitespace-nowrap font-medium">{i + 1}. {s.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-8">{renderStep()}</div>

      <div className="flex items-center justify-between mt-6">
        <Button variant="outline" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}><ChevronLeft className="w-4 h-4 mr-1" />Anterior</Button>
        {step < PTAM_STEPS.length - 1 ? (
          <Button className="bg-emerald-900 hover:bg-emerald-800 text-white" onClick={() => { save(true); setStep(step + 1); }}>Próximo<ChevronRight className="w-4 h-4 ml-1" /></Button>
        ) : (
          <Button className="bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold" onClick={handleDownload}><Download className="w-4 h-4 mr-1" />Baixar DOCX Final</Button>
        )}
      </div>
    </div>
  );
};

export default PtamWizard;
