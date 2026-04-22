import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Loader2, ClipboardCheck, Camera, PenLine } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { tviAPI } from '../../../lib/api';
import FieldRenderer from './components/FieldRenderer';
import AmbienteBlock from './components/AmbienteBlock';
import SignaturePad from './components/SignaturePad';
import ExportBar from './components/ExportBar';
import { useExport } from './hooks/useExport';

const TABS = [
  { id: 'dados', label: 'Dados Gerais', icon: ClipboardCheck },
  { id: 'ambientes', label: 'Ambientes', icon: Camera },
  { id: 'assinatura', label: 'Assinatura', icon: PenLine },
];

const TVIForm = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const { loading: exportLoading, exportPdf, exportDocx, shareWhatsApp, shareEmail } = useExport();

  const [vistoria, setVistoria] = useState(null);
  const [model, setModel] = useState(null);
  const [fields, setFields] = useState({});
  const [ambientes, setAmbientes] = useState([]);
  const [signature, setSignature] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [activeTab, setActiveTab] = useState('dados');
  const debounceRef = useRef(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await tviAPI.get(id);
      setVistoria(data);
      setFields(data.campos_extras || data.campos || {});
      setAmbientes(data.ambientes || []);
      setSignature(data.assinatura || null);
      if (data.model_id || data.modelo_id) {
        const m = await tviAPI.getModel(data.model_id || data.modelo_id);
        setModel(m);
      }
    } catch {
      toast({ title: 'Erro ao carregar vistoria', variant: 'destructive' });
      nav('/dashboard/tvi');
    } finally {
      setLoading(false);
    }
  }, [id, nav, toast]);

  useEffect(() => { load(); }, [load]);

  const save = useCallback(async (silent = false) => {
    if (!id) return;
    setSaving(true);
    try {
      await tviAPI.update(id, { campos_extras: fields, ambientes, assinatura: signature });
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Vistoria salva' });
    } catch {
      if (!silent) toast({ title: 'Erro ao salvar', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [id, fields, ambientes, signature, toast]);

  useEffect(() => {
    if (!id || loading) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [fields, ambientes, signature, id, loading, save]);

  const handleSignatureSave = async (b64) => {
    setSignature(b64);
    if (id && b64) {
      try {
        await tviAPI.saveSignature(id, b64);
        toast({ title: 'Assinatura salva' });
      } catch {
        toast({ title: 'Erro ao salvar assinatura', variant: 'destructive' });
      }
    }
  };

  if (loading) return (
    <div className="py-20 flex justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-700" />
    </div>
  );

  const modelFields = model?.campos || [];
  const specificFields = model?.campos_especificos || [];

  return (
    <div className="max-w-4xl mx-auto pb-20 space-y-6">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => nav('/dashboard/tvi')}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Voltar
        </Button>
        <div className="flex items-center gap-2">
          {lastSaved && (
            <span className="text-xs text-gray-400">Salvo {lastSaved.toLocaleTimeString('pt-BR')}</span>
          )}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar'}
          </Button>
        </div>
      </div>

      {/* Header info */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center">
            <ClipboardCheck className="w-5 h-5 text-emerald-900" />
          </div>
          <div>
            <div className="font-semibold text-gray-900">{vistoria?.modelo_nome || 'TVI'}</div>
            <div className="text-sm text-gray-500">{vistoria?.categoria || ''}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-200 p-2 flex gap-1">
        {TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition
                ${activeTab === tab.id ? 'bg-emerald-900 text-white' : 'text-gray-600 hover:bg-gray-50'}`}>
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {activeTab === 'dados' && (
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-600">Título / Endereço</label>
              <input
                type="text"
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                value={vistoria?.titulo || ''}
                onChange={e => setVistoria(v => ({ ...v, titulo: e.target.value }))}
                placeholder="Ex.: Rua das Flores, 123 — Apto 45"
              />
            </div>

            {modelFields.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {modelFields.map(f => (
                  <FieldRenderer
                    key={f.key}
                    field={f}
                    value={fields[f.key]}
                    onChange={(key, val) => setFields(prev => ({ ...prev, [key]: val }))}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">
                Nenhum campo dinâmico para este modelo.
              </p>
            )}

            {specificFields.length > 0 && (
              <>
                <div className="border-t border-gray-200 pt-4 mt-4">
                  <h3 className="text-sm font-semibold text-emerald-800 mb-3">
                    Campos Específicos — {model?.nome || 'Modelo'}
                  </h3>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {specificFields.map(f => (
                    <FieldRenderer
                      key={f.key}
                      field={f}
                      value={fields[f.key]}
                      onChange={(key, val) => setFields(prev => ({ ...prev, [key]: val }))}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'ambientes' && (
          <AmbienteBlock
            vistoriaId={id}
            ambientes={ambientes}
            onChange={setAmbientes}
          />
        )}

        {activeTab === 'assinatura' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Assine digitalmente abaixo para validar o Termo de Vistoria.
            </p>
            <SignaturePad value={signature} onChange={handleSignatureSave} />
            {signature && (
              <div className="mt-3 p-3 bg-emerald-50 rounded-xl text-sm text-emerald-800">
                Assinatura registrada com sucesso.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Export bar */}
      {vistoria && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 mb-3 font-medium">Exportar / Compartilhar</p>
          <ExportBar
            vistoria={vistoria}
            loading={exportLoading}
            onPdf={exportPdf}
            onDocx={exportDocx}
            onWhatsApp={shareWhatsApp}
            onEmail={shareEmail}
          />
        </div>
      )}
    </div>
  );
};

export default TVIForm;
