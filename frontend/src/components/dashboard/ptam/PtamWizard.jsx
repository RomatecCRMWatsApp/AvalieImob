import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as LucideIcons from 'lucide-react';
import { ChevronLeft, ChevronRight, Save, Download, ArrowLeft, Loader2, Check } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { ptamAPI, aiAPI, perfilAPI } from '../../../lib/api';
import { EMPTY_PTAM, PTAM_STEPS, computeImpactTotals, sumIndemnity } from './ptamHelpers';
import { StepSolicitante } from './steps/StepSolicitante';
import { StepObjetivo } from './steps/StepObjetivo';
import { StepImovelId } from './steps/StepImovelId';
import { StepRegiao } from './steps/StepRegiao';
import { StepCaracterizacao } from './steps/StepCaracterizacao';
import { StepAmostras } from './steps/StepAmostras';
import { StepMetodologia } from './steps/StepMetodologia';
import { StepCalculos } from './steps/StepCalculos';
import { StepPonderancia } from './steps/StepPonderancia';
import { StepMetodoAvaliacao } from './steps/StepMetodoAvaliacao';
import { StepResultado } from './steps/StepResultado';
import { StepConclusao } from './steps/StepConclusao';

const getStepClasses = (active, done) => {
  if (active) return 'bg-emerald-900 text-white';
  if (done) return 'bg-emerald-50 text-emerald-900 hover:bg-emerald-100';
  return 'text-gray-500 hover:bg-gray-50';
};
const getStepIconClasses = (active, done) => {
  if (active) return 'bg-white/20';
  if (done) return 'bg-emerald-200';
  return 'bg-gray-100';
};

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
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar PTAM', variant: 'destructive' });
      nav('/dashboard/ptam');
    } finally {
      setLoading(false);
    }
  }, [ptamId, nav, toast]);

  useEffect(() => { load(); }, [load]);

  // Pre-fill technician fields from profile when creating a new PTAM
  useEffect(() => {
    if (ptamId) return; // only for new ones
    perfilAPI.get().then((p) => {
      if (!p) return;
      // Find the most relevant registro: CRECI first, then CNAI, then others
      const creci = (p.registros || []).find(r => r.tipo === 'CRECI' && r.status === 'ativo');
      const cnai  = (p.registros || []).find(r => r.tipo === 'CNAI'  && r.status === 'ativo');
      const crea  = (p.registros || []).find(r => r.tipo === 'CREA'  && r.status === 'ativo');
      const cau   = (p.registros || []).find(r => r.tipo === 'CAU'   && r.status === 'ativo');
      const cft   = (p.registros || []).find(r => r.tipo === 'CFT'   && r.status === 'ativo');

      const registroNum = crea
        ? `CREA ${crea.uf ? crea.uf + ' ' : ''}${crea.numero}`
        : cau
        ? `CAU ${cau.uf ? cau.uf + ' ' : ''}${cau.numero}`
        : cft
        ? `CFT ${cft.numero}`
        : '';

      setForm(f => ({
        ...f,
        responsavel_nome:      p.nome_completo  || f.responsavel_nome,
        responsavel_creci:     creci ? `CRECI${creci.uf ? '/' + creci.uf : ''} ${creci.numero}` : f.responsavel_creci,
        responsavel_cnai:      cnai  ? `CNAI ${cnai.numero}` : f.responsavel_cnai,
        registro_profissional: registroNum || f.registro_profissional,
        conclusion_city:       p.cidade || f.conclusion_city,
      }));
    }).catch(() => {/* silencioso - perfil nao obrigatorio */});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useCallback(async (silent = false) => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        // keep legacy totals synced
        impact_areas: computeImpactTotals(form.impact_areas),
        total_indemnity: form.total_indemnity || form.resultado_valor_total || sumIndemnity(form.impact_areas),
      };
      if (ptamId) {
        await ptamAPI.update(ptamId, payload);
      } else {
        const created = await ptamAPI.create(payload);
        setPtamId(created.id);
        setForm((f) => ({ ...f, number: created.number, numero_ptam: created.numero_ptam || '' }));
        nav(`/dashboard/ptam/${created.id}`, { replace: true });
      }
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      console.warn(err);
      if (!silent) toast({ title: 'Erro ao salvar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [form, ptamId, nav, toast]);

  // Auto-save every 30s when there's an id
  useEffect(() => {
    if (!ptamId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [form, ptamId, save]);

  const handleAi = async (fieldKey) => {
    const currentValue = form[fieldKey] || '';
    const prompt = `Aperfeiçoe tecnicamente este texto para um PTAM (Parecer Técnico de Avaliação Mercadológica) conforme NBR 14.653. Mantenha tom formal, técnico, profissional em português-BR. Retorne APENAS o texto aperfeiçoado, sem explicações.\n\nCampo: ${fieldKey}\nTexto atual:\n${currentValue || '(vazio - gere um texto inicial técnico e padronizado adequado a este campo)'}`;
    setAiLoading(fieldKey);
    try {
      const session_id = `ptam_${ptamId || 'draft'}_${fieldKey}_${Date.now()}`;
      const res = await aiAPI.chat(session_id, prompt);
      setForm((f) => ({ ...f, [fieldKey]: res.reply }));
      toast({ title: 'Texto aperfeiçoado com IA' });
    } catch (err) {
      toast({ title: 'Erro na IA', description: err.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
    } finally {
      setAiLoading(null);
    }
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
    } catch (err) {
      toast({ title: 'Erro ao baixar', variant: 'destructive' });
      console.warn(err);
    }
  };

  const handleDownloadPdf = async () => {
    if (!ptamId) { toast({ title: 'Salve o PTAM primeiro', variant: 'destructive' }); return; }
    try {
      const blob = await ptamAPI.downloadPdf(ptamId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PTAM_${(form.number || 'sem-numero').replace(/\//g, '-')}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast({ title: 'Download PDF iniciado' });
    } catch (err) {
      toast({ title: 'Erro ao baixar PDF', description: err.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
      console.warn(err);
    }
  };

  if (loading) return (
    <div className="py-20 flex justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-800" />
    </div>
  );

  const stepProps = { form, setForm, onAi: handleAi, aiLoading };

  const renderStep = () => {
    switch (step) {
      case 0:  return <StepSolicitante {...stepProps} />;
      case 1:  return <StepObjetivo {...stepProps} />;
      case 2:  return <StepImovelId {...stepProps} />;
      case 3:  return <StepRegiao {...stepProps} />;
      case 4:  return <StepCaracterizacao {...stepProps} />;
      case 5:  return <StepAmostras {...stepProps} />;
      case 6:  return <StepMetodologia {...stepProps} />;
      case 7:  return <StepCalculos {...stepProps} />;
      case 8:  return <StepPonderancia {...stepProps} />;
      case 9:  return <StepMetodoAvaliacao {...stepProps} />;
      case 10: return <StepResultado {...stepProps} />;
      case 11: return <StepConclusao {...stepProps} />;
      default: return null;
    }
  };

  const totalSteps = PTAM_STEPS.length;

  return (
    <div className="max-w-5xl mx-auto pb-20">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={() => nav('/dashboard/ptam')}>
          <ArrowLeft className="w-4 h-4 mr-1" />Voltar
        </Button>
        <div className="flex items-center gap-2">
          {lastSaved && (
            <span className="text-xs text-gray-500">Salvo {lastSaved.toLocaleTimeString('pt-BR')}</span>
          )}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar rascunho'}
          </Button>
          <Button variant="outline" className="border-red-300 text-red-700 hover:bg-red-50" onClick={handleDownloadPdf}>
            <Download className="w-4 h-4 mr-1" />Baixar PDF
          </Button>
          <Button className="bg-emerald-900 hover:bg-emerald-800 text-white" onClick={handleDownload}>
            <Download className="w-4 h-4 mr-1" />Baixar DOCX
          </Button>
        </div>
      </div>

      {/* Progress indicator */}
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
          {PTAM_STEPS.map((s, i) => {
            const Icon = LucideIcons[s.icon] || LucideIcons.Circle;
            const active = i === step;
            const done = i < step;
            return (
              <button
                key={s.id}
                onClick={() => setStep(i)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs font-medium transition ${getStepClasses(active, done)}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${getStepIconClasses(active, done)}`}>
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
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="border-red-300 text-red-700 hover:bg-red-50"
                onClick={handleDownloadPdf}
              >
                <Download className="w-4 h-4 mr-1" />Baixar PDF Final
              </Button>
              <Button
                className="bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold"
                onClick={handleDownload}
              >
                <Download className="w-4 h-4 mr-1" />Baixar DOCX Final
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PtamWizard;
