// NFS-e — Configuração & Teste (emissão). Rota: /dashboard/admin/nfse-emissao (admin).
// Configura o município/emitente/certificado, testa o certificado e gera/valida a DPS (XML).
// A TRANSMISSÃO real é travada (sefin.transmissao_habilitada) até a homologação.
import React, { useEffect, useState } from 'react';
import { ShieldCheck, FileCode2, Loader2, Save } from 'lucide-react';
import { adminAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { Input } from '../../components/ui/input';

const VERDE = '#0C3320';

const CFG0 = {
  id: null, municipio_nome: 'Açailândia', municipio_uf: 'MA', codigo_ibge: '2100055',
  provider: 'sefin_nacional', ambiente: 'homologacao', ativo: true, template_danfse: 'prime1',
  emitente: { razao_social: 'J R P BEZERRA LTDA', nome_fantasia: 'ROMATEC CONSULTORIA TOTAL', cnpj: '17261987000109', inscricao_municipal: '26800', inscricao_estadual: '0', optante_simples: false, telefone: '9991811246', endereco: { logradouro: 'RUA MANOEL ELZEBRIO', numero: '14', complemento: 'QUADRA 104', bairro: 'NOVA AÇAILÂNDIA', cep: '65930000', codigo_ibge: '2100055' } },
  sefin: { base_url_sefin: '', base_url_adn: '', certificado_ref: '', certificado_senha_ref: 'ROMATEC_CERT_SENHA', serie_dps: '1', transmissao_habilitada: false, rota_emissao: '/sefin/dps', rota_consulta: '/sefin/nfse' },
  fiscal_defaults: { item_lista_servico: '17.01', codigo_tributacao_municipal: '821130001', codigo_tributacao_nacional: '', codigo_nbs: '114039000', aliquota_iss: 0.02, regime_especial_tributacao: '0' },
};

const Field = ({ label, children }) => (
  <div className="space-y-1"><label className="text-[11px] font-medium text-gray-500">{label}</label>{children}</div>
);

export default function NfseEmissao() {
  const { toast } = useToast();
  const [cfg, setCfg] = useState(CFG0);
  const [saving, setSaving] = useState(false);
  const [certResult, setCertResult] = useState(null);
  const [testando, setTestando] = useState(false);
  const [teste, setTeste] = useState({ valor: '17500,00', aliquota: '2,0000', cnpj: '57123389000180', nome: 'RODO RANCHO COMBUSTIVEIS LTDA', discriminacao: '4ª parcela do contrato — obra Posto Chapadão (Itinga/MA).' });
  const [dps, setDps] = useState(null);
  const [gerando, setGerando] = useState(false);

  useEffect(() => {
    adminAPI.nfseConfigList().then((lst) => { if (lst && lst[0]) setCfg({ ...CFG0, ...lst[0] }); }).catch(() => {});
  }, []);

  const setE = (k, v) => setCfg((c) => ({ ...c, emitente: { ...c.emitente, [k]: v } }));
  const setS = (k, v) => setCfg((c) => ({ ...c, sefin: { ...c.sefin, [k]: v } }));
  const setF = (k, v) => setCfg((c) => ({ ...c, fiscal_defaults: { ...c.fiscal_defaults, [k]: v } }));

  const salvar = async () => {
    setSaving(true);
    try {
      const r = cfg.id ? await adminAPI.nfseConfigUpdate(cfg.id, cfg) : await adminAPI.nfseConfigCreate(cfg);
      setCfg((c) => ({ ...c, id: r.id || c.id }));
      toast({ title: 'Configuração salva' });
    } catch (e) { toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setSaving(false); }
  };

  const testarCert = async () => {
    if (!cfg.id) { toast({ title: 'Salve a configuração primeiro' }); return; }
    setTestando(true); setCertResult(null);
    try { setCertResult(await adminAPI.nfseTestarCert(cfg.id)); }
    catch (e) { setCertResult({ ok: false, erro: e.response?.data?.detail || 'Falha' }); }
    finally { setTestando(false); }
  };

  const gerarDps = async () => {
    if (!cfg.id) { toast({ title: 'Salve a configuração primeiro' }); return; }
    setGerando(true); setDps(null);
    const num = (s) => Number(String(s).replace(/\./g, '').replace(',', '.')) || 0;
    try {
      const r = await adminAPI.nfseDpsPreview({
        config_id: cfg.id,
        tomador: { tipo_documento: 'cnpj', documento: teste.cnpj, razao_nome: teste.nome },
        servico: { discriminacao: teste.discriminacao, item_lista_servico: cfg.fiscal_defaults.item_lista_servico, codigo_tributacao_municipal: cfg.fiscal_defaults.codigo_tributacao_municipal, cnbs: cfg.fiscal_defaults.codigo_nbs, local_prestacao_ibge: cfg.codigo_ibge, valor_servico: num(teste.valor), aliquota_iss: num(teste.aliquota) },
        origem: { tipo: 'servico_avulso' },
      });
      setDps(r);
    } catch (e) { toast({ title: 'Erro ao gerar DPS', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setGerando(false); }
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-1 font-display" style={{ color: VERDE }}>NFS-e — Configuração & Teste</h1>
      <p className="text-sm text-gray-500 mb-4">Configure o município/certificado, teste o certificado e gere/valide a DPS. A emissão real fica <b>travada</b> até a homologação.</p>

      <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-[13px] text-amber-800">
        🔒 Transmissão <b>{cfg.sefin?.transmissao_habilitada ? 'HABILITADA' : 'DESABILITADA'}</b> (segurança).
        Certificado: defina <code>ROMATEC_CERT_PFX_B64</code> + <code>ROMATEC_CERT_SENHA</code> nas Variables do Railway.
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Configuração */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Emitente / Município</div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Município"><Input value={cfg.municipio_nome} onChange={(e) => setCfg({ ...cfg, municipio_nome: e.target.value })} /></Field>
            <Field label="Cód. IBGE"><Input value={cfg.codigo_ibge} onChange={(e) => setCfg({ ...cfg, codigo_ibge: e.target.value })} /></Field>
            <Field label="Razão Social"><Input value={cfg.emitente.razao_social} onChange={(e) => setE('razao_social', e.target.value)} /></Field>
            <Field label="Nome Fantasia"><Input value={cfg.emitente.nome_fantasia} onChange={(e) => setE('nome_fantasia', e.target.value)} /></Field>
            <Field label="CNPJ"><Input value={cfg.emitente.cnpj} onChange={(e) => setE('cnpj', e.target.value)} /></Field>
            <Field label="Insc. Municipal"><Input value={cfg.emitente.inscricao_municipal} onChange={(e) => setE('inscricao_municipal', e.target.value)} /></Field>
          </div>

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Sefin / Certificado</div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Ambiente">
              <select value={cfg.ambiente} onChange={(e) => setCfg({ ...cfg, ambiente: e.target.value })} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm">
                <option value="homologacao">Homologação</option><option value="producao">Produção</option>
              </select>
            </Field>
            <Field label="Série DPS"><Input value={cfg.sefin.serie_dps} onChange={(e) => setS('serie_dps', e.target.value)} /></Field>
            <Field label="Base URL Sefin (homologação)"><Input value={cfg.sefin.base_url_sefin} onChange={(e) => setS('base_url_sefin', e.target.value)} placeholder="https://..." /></Field>
            <Field label="Caminho do .pfx (opcional)"><Input value={cfg.sefin.certificado_ref} onChange={(e) => setS('certificado_ref', e.target.value)} placeholder="usa ROMATEC_CERT_PFX_B64 se vazio" /></Field>
          </div>

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Defaults Fiscais</div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Item LC 116"><Input value={cfg.fiscal_defaults.item_lista_servico} onChange={(e) => setF('item_lista_servico', e.target.value)} /></Field>
            <Field label="Alíquota ISS (fração)"><Input value={cfg.fiscal_defaults.aliquota_iss} onChange={(e) => setF('aliquota_iss', Number(e.target.value) || 0)} /></Field>
            <Field label="Cód. Trib. Municipal"><Input value={cfg.fiscal_defaults.codigo_tributacao_municipal} onChange={(e) => setF('codigo_tributacao_municipal', e.target.value)} /></Field>
            <Field label="cNBS (9 díg.)"><Input value={cfg.fiscal_defaults.codigo_nbs} onChange={(e) => setF('codigo_nbs', e.target.value)} /></Field>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <button onClick={salvar} disabled={saving} className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: VERDE }}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvar config
            </button>
            <button onClick={testarCert} disabled={testando} className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold border border-emerald-300 text-emerald-800 disabled:opacity-50">
              {testando ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />} Testar certificado
            </button>
          </div>
          {certResult && (
            <div className={`rounded-lg px-3 py-2 text-sm ${certResult.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-700'}`}>
              {certResult.ok ? `✓ Certificado OK — ${certResult.titular}` : `✗ ${certResult.erro}`}
            </div>
          )}
        </div>

        {/* Teste da DPS */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Gerar DPS de teste (XML)</div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Valor do serviço"><Input value={teste.valor} onChange={(e) => setTeste({ ...teste, valor: e.target.value })} /></Field>
            <Field label="Alíquota ISS %"><Input value={teste.aliquota} onChange={(e) => setTeste({ ...teste, aliquota: e.target.value })} /></Field>
            <Field label="Tomador CNPJ"><Input value={teste.cnpj} onChange={(e) => setTeste({ ...teste, cnpj: e.target.value })} /></Field>
            <Field label="Tomador Nome"><Input value={teste.nome} onChange={(e) => setTeste({ ...teste, nome: e.target.value })} /></Field>
          </div>
          <Field label="Discriminação"><textarea value={teste.discriminacao} onChange={(e) => setTeste({ ...teste, discriminacao: e.target.value })} rows={2} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm" /></Field>
          <button onClick={gerarDps} disabled={gerando} className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: VERDE }}>
            {gerando ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCode2 className="w-4 h-4" />} Gerar DPS (XML)
          </button>
          {dps && (
            <div className="space-y-2">
              <div className={`rounded-lg px-3 py-1.5 text-sm ${dps.valido == null ? 'bg-gray-100 text-gray-600' : dps.valido ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-700'}`}>
                {dps.valido == null ? 'XML gerado (defina NFSE_DPS_XSD p/ validar contra o schema)' : dps.valido ? '✓ Válido contra o XSD' : `✗ Inválido: ${(dps.erros || []).join(' · ')}`}
              </div>
              <pre className="text-[10px] bg-gray-900 text-emerald-200 rounded-lg p-3 overflow-auto max-h-[360px]">{dps.xml}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
