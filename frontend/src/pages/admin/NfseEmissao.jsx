// NFS-e — Configuração & Teste (emissão). Rota: /dashboard/admin/nfse-emissao (admin).
// Configura o município/emitente/certificado, testa o certificado e gera/valida a DPS (XML).
// A TRANSMISSÃO real é travada (sefin.transmissao_habilitada) até a homologação.
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, FileCode2, Loader2, Save, UserPlus } from 'lucide-react';
import { adminAPI, certificadosAPI, clientsAPI, aiAPI } from '../../lib/api';
import RichTextEditor from '../../components/ui/RichTextEditor';
import { paraEditorHtml } from '../../components/ui/RichField';

// HTML do editor → texto puro (a NFS-e exige texto simples na Discriminação).
const stripHtml = (h) => {
  if (!h) return '';
  const d = document.createElement('div');
  d.innerHTML = String(h).replace(/<\/(p|div|li|br)>/gi, '\n').replace(/<br\s*\/?>(?!$)/gi, '\n');
  return (d.textContent || d.innerText || '').replace(/\n{3,}/g, '\n\n').replace(/[ \t]+/g, ' ').trim();
};

// Descrições dos códigos fiscais conhecidos (referência para o usuário/contador).
const DESC_ITEM = { '17.01': 'Assessoria/consultoria de qualquer natureza; análise, exame, pesquisa, coleta e fornecimento de dados.' };
const DESC_CNAE = { '8211300': 'Serviços combinados de escritório e apoio administrativo.' };
const DESC_MUN = { '821130001': 'Serviços de análise, exame, pesquisa, coleta e fornecimento de dados.' };
const DESC_NBS = { '114039000': 'NBS de serviços de engenharia/consultoria — confirmar com a contabilidade.' };
const DESC_CTRIB = { '170101': 'CTribNac 17.01.01 — Assessoria ou consultoria de qualquer natureza.' };
import { useToast } from '../../hooks/use-toast';
import { Input } from '../../components/ui/input';

const VERDE = '#0C3320';

const CFG0 = {
  id: null, municipio_nome: 'Açailândia', municipio_uf: 'MA', codigo_ibge: '2100055',
  provider: 'abrasf', ambiente: 'homologacao', ativo: true, template_danfse: 'prime1',
  emitente: { razao_social: 'J R P BEZERRA LTDA', nome_fantasia: 'ROMATEC CONSULTORIA TOTAL', cnpj: '17261987000109', inscricao_municipal: '26800', inscricao_estadual: '0', optante_simples: false, telefone: '9991811246', endereco: { logradouro: 'RUA MANOEL ELZEBRIO', numero: '14', complemento: 'QUADRA 104', bairro: 'NOVA AÇAILÂNDIA', cep: '65930000', codigo_ibge: '2100055' } },
  sefin: { base_url_sefin: 'https://sefin.producaorestrita.nfse.gov.br/API/SefinNacional', base_url_adn: 'https://adn.producaorestrita.nfse.gov.br', certificado_id: '', certificado_ref: '', certificado_senha_ref: 'ROMATEC_CERT_SENHA', serie_dps: '1', transmissao_habilitada: false, rota_emissao: '/nfse', rota_consulta: '/nfse' },
  abrasf: { url_ws: 'http://speedgov.com.br/wsacl/Nfes', url_ws_producao: 'http://speedgov.com.br/wsacl/Nfes', versao_abrasf: '1.00', namespace: 'http://www.abrasf.org.br/nfse.xsd', namespace_ws: 'http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd', operacao_envio: 'RecepcionarLoteRps', soap_action: '', serie_rps: '1', assinatura_sha: 'sha1', certificado_id: '', transmissao_habilitada: false },
  fiscal_defaults: { item_lista_servico: '17.01', codigo_tributacao_municipal: '821130001', codigo_tributacao_nacional: '170101', cnae: '8211300', codigo_nbs: '114039000', aliquota_iss: 0.02, regime_especial_tributacao: '0' },
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
  const [certs, setCerts] = useState([]);
  const [clientes, setClientes] = useState([]);
  const nav = useNavigate();

  useEffect(() => {
    adminAPI.nfseConfigList().then((lst) => {
      const m = lst && lst[0];
      if (m) setCfg({
        ...CFG0, ...m,
        emitente: { ...CFG0.emitente, ...(m.emitente || {}) },
        sefin: { ...CFG0.sefin, ...(m.sefin || {}) },
        // valores vazios salvos NÃO sobrescrevem os defaults (ex.: url_ws/namespaces)
        abrasf: { ...CFG0.abrasf, ...Object.fromEntries(Object.entries(m.abrasf || {}).filter(([, v]) => v !== '' && v != null)) },
        fiscal_defaults: { ...CFG0.fiscal_defaults, ...(m.fiscal_defaults || {}) },
      });
    }).catch(() => {});
    certificadosAPI.list().then((d) => setCerts((d || []).filter((c) => c.ativo !== false))).catch(() => {});
    clientsAPI.list().then((d) => setClientes(Array.isArray(d) ? d : [])).catch(() => {});
  }, []);

  const selecionarCliente = (cid) => {
    const c = clientes.find((x) => String(x.id) === String(cid));
    if (!c) return;
    setTeste((t) => ({ ...t, cliente_id: cid, cnpj: c.doc || c.cpf_cnpj || '', nome: c.name || c.nome || '' }));
  };

  const certTipo = (c) => (c?.perfil === 'PJ' ? 'e-CNPJ' : 'e-CPF');

  const setE = (k, v) => setCfg((c) => ({ ...c, emitente: { ...c.emitente, [k]: v } }));
  const setS = (k, v) => setCfg((c) => ({ ...c, sefin: { ...c.sefin, [k]: v } }));
  const setA = (k, v) => setCfg((c) => ({ ...c, abrasf: { ...(c.abrasf || {}), [k]: v } }));
  const setF = (k, v) => setCfg((c) => ({ ...c, fiscal_defaults: { ...c.fiscal_defaults, [k]: v } }));
  const isAbrasf = cfg.provider === 'abrasf';
  const [rps, setRps] = useState(null);
  const [gerandoRps, setGerandoRps] = useState(false);
  const [envioResp, setEnvioResp] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [consultaResp, setConsultaResp] = useState(null);
  const [consultando, setConsultando] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);

  const consultarRps = async () => {
    if (!cfg.id) { toast({ title: 'Salve a configuração primeiro' }); return; }
    setConsultando(true); setConsultaResp(null);
    try {
      setConsultaResp(await adminAPI.nfseAbrasfConsultarRps({ config_id: cfg.id, numero: 1 }));
    } catch (e) { setConsultaResp({ ok: false, erro: e.response?.data?.detail || 'Falha na chamada' }); }
    finally { setConsultando(false); }
  };

  const renderParsed = (p) => {
    if (!p) return null;
    if (p.sucesso || p.numero_nfse) {
      return (
        <div className="rounded-lg px-3 py-2 text-sm bg-emerald-100 text-emerald-900 font-semibold">
          🎉 Sucesso{p.numero_nfse ? ` — NFS-e nº ${p.numero_nfse}` : ''}{p.codigo_verificacao ? ` · cód. ${p.codigo_verificacao}` : ''}{p.protocolo ? ` · protocolo ${p.protocolo}` : ''}
        </div>
      );
    }
    if (p.mensagens?.length) {
      return (
        <div className="space-y-1">
          {p.mensagens.map((m, i) => (
            <div key={i} className="rounded-lg px-3 py-2 text-sm bg-amber-50 text-amber-900 border border-amber-200">
              <b>{m.codigo}</b> — {m.mensagem}
              {m.correcao && <div className="text-[11px] mt-0.5">💡 {m.correcao}</div>}
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const aperfeicoarDiscriminacao = async (html) => {
    const atual = stripHtml(html);
    setAiLoading(true);
    try {
      const prompt =
        'Aperfeiçoe a descrição de serviço abaixo para uma NFS-e (nota fiscal de serviço eletrônica), ' +
        'tom formal, claro e objetivo em português-BR, conciso (1 a 3 frases). NÃO use formatação, ' +
        'títulos nem rótulos — retorne APENAS o texto.\n\nServiço atual:\n' +
        (atual || '(vazio — gere uma descrição adequada de serviço de engenharia/agrimensura)');
      const res = await aiAPI.chat(`nfse_discr_${Date.now()}`, prompt);
      const texto = (res?.reply || '').trim();
      if (texto) setTeste((t) => ({ ...t, discriminacao: texto }));
      toast({ title: 'Discriminação aperfeiçoada com IA' });
    } catch (e) { toast({ title: 'Erro na IA', description: e.response?.data?.detail || 'Tente novamente', variant: 'destructive' }); }
    finally { setAiLoading(false); }
  };

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
        servico: { discriminacao: stripHtml(teste.discriminacao), item_lista_servico: cfg.fiscal_defaults.item_lista_servico, codigo_tributacao_municipal: cfg.fiscal_defaults.codigo_tributacao_municipal, cnbs: cfg.fiscal_defaults.codigo_nbs, local_prestacao_ibge: cfg.codigo_ibge, valor_servico: num(teste.valor), aliquota_iss: num(teste.aliquota) },
        origem: { tipo: 'servico_avulso' },
      });
      setDps(r);
    } catch (e) { toast({ title: 'Erro ao gerar DPS', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setGerando(false); }
  };

  const gerarRps = async () => {
    if (!cfg.id) { toast({ title: 'Salve a configuração primeiro' }); return; }
    setGerandoRps(true); setRps(null);
    const num = (s) => Number(String(s).replace(/\./g, '').replace(',', '.')) || 0;
    try {
      const r = await adminAPI.nfseAbrasfPreview({
        config_id: cfg.id,
        tomador: { tipo_documento: 'cnpj', documento: teste.cnpj, razao_nome: teste.nome },
        servico: { discriminacao: stripHtml(teste.discriminacao), item_lista_servico: cfg.fiscal_defaults.item_lista_servico, codigo_tributacao_municipal: cfg.fiscal_defaults.codigo_tributacao_municipal, local_prestacao_ibge: cfg.codigo_ibge, valor_servico: num(teste.valor), aliquota_iss: num(teste.aliquota) },
        origem: { tipo: 'servico_avulso' },
      });
      setRps(r);
    } catch (e) { toast({ title: 'Erro ao gerar RPS', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setGerandoRps(false); }
  };

  const testarEnvio = async () => {
    if (!cfg.id) { toast({ title: 'Salve a configuração primeiro' }); return; }
    const url = cfg.abrasf?.url_ws || '';
    if (/wsacl|produc/i.test(url)) {     // /wsacl/ = PRODUÇÃO do SpeedGov → criaria NFS-e REAL
      if (!window.confirm('⚠️ ATENÇÃO: esta URL é de PRODUÇÃO. Enviar aqui cria uma NFS-e REAL (não é teste) — você teria que cancelar. Tem certeza que quer continuar?')) return;
    }
    setEnviando(true); setEnvioResp(null);
    const num = (s) => Number(String(s).replace(/\./g, '').replace(',', '.')) || 0;
    try {
      const r = await adminAPI.nfseAbrasfTestar({
        config_id: cfg.id,
        tomador: { tipo_documento: 'cnpj', documento: teste.cnpj, razao_nome: teste.nome },
        servico: { discriminacao: stripHtml(teste.discriminacao), item_lista_servico: cfg.fiscal_defaults.item_lista_servico, codigo_tributacao_municipal: cfg.fiscal_defaults.codigo_tributacao_municipal, local_prestacao_ibge: cfg.codigo_ibge, valor_servico: num(teste.valor), aliquota_iss: num(teste.aliquota) },
        origem: { tipo: 'servico_avulso' },
      });
      setEnvioResp(r);
    } catch (e) { setEnvioResp({ ok: false, erro: e.response?.data?.detail || 'Falha na chamada' }); }
    finally { setEnviando(false); }
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-1 font-display" style={{ color: VERDE }}>NFS-e — Configuração & Teste</h1>
      <p className="text-sm text-gray-500 mb-4">Configure o município/certificado, teste o certificado e gere/valide a DPS. A emissão real fica <b>travada</b> até a homologação.</p>

      <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-[13px] text-amber-800">
        🔒 Transmissão <b>{(isAbrasf ? cfg.abrasf?.transmissao_habilitada : cfg.sefin?.transmissao_habilitada) ? 'HABILITADA' : 'DESABILITADA'}</b> (segurança).
        {isAbrasf
          ? <> Açailândia emite por <b>SpeedGov (ABRASF/RPS)</b>. Falta a <b>URL do webservice (WSDL)</b> + teste em homologação p/ transmitir.</>
          : <> Usa o <b>e-CNPJ</b> de <b>Configurações → Certificados</b> (PJ) — clique <b>Testar certificado</b> p/ confirmar.</>}
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

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Sistema de emissão</div>
          <Field label="Provedor (como o município emite)">
            <select value={cfg.provider} onChange={(e) => setCfg({ ...cfg, provider: e.target.value })} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm">
              <option value="abrasf">ABRASF / SpeedGov (Açailândia — login municipal)</option>
              <option value="sefin_nacional">Sefin Nacional (DPS — quando migrar)</option>
            </select>
          </Field>
          {isAbrasf && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="URL do webservice (SpeedGov)"><Input value={cfg.abrasf.url_ws} onChange={(e) => setA('url_ws', e.target.value)} placeholder="http://speedgov.com.br/wsmod/Nfes" /></Field>
              <Field label="Versão ABRASF"><Input value={cfg.abrasf.versao_abrasf} onChange={(e) => setA('versao_abrasf', e.target.value)} placeholder="1.00" /></Field>
            </div>
          )}

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
          <Field label="Certificado para assinar a NFS-e">
            <select value={cfg.sefin.certificado_id || ''} onChange={(e) => setS('certificado_id', e.target.value)}
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm">
              <option value="">Automático — e-CNPJ (PJ) ativo</option>
              {certs.map((c) => (
                <option key={c.id} value={c.id}>{certTipo(c)} — {c.titular || c.label}{c.documento ? ` · ${c.documento}` : ''}</option>
              ))}
            </select>
            <p className="text-[10px] text-gray-400 mt-0.5">A NFS-e exige o <b>e-CNPJ (PJ)</b>. Use o automático, salvo orientação da contabilidade.</p>
          </Field>

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Defaults Fiscais</div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Item LC 116"><Input value={cfg.fiscal_defaults.item_lista_servico} onChange={(e) => setF('item_lista_servico', e.target.value)} />{DESC_ITEM[cfg.fiscal_defaults.item_lista_servico] && <p className="text-[10px] text-gray-400 mt-0.5">{DESC_ITEM[cfg.fiscal_defaults.item_lista_servico]}</p>}</Field>
            <Field label="Alíquota ISS (fração)"><Input value={cfg.fiscal_defaults.aliquota_iss} onChange={(e) => setF('aliquota_iss', Number(e.target.value) || 0)} /></Field>
            <Field label="Cód. Trib. Municipal"><Input value={cfg.fiscal_defaults.codigo_tributacao_municipal} onChange={(e) => setF('codigo_tributacao_municipal', e.target.value)} />{DESC_MUN[cfg.fiscal_defaults.codigo_tributacao_municipal] && <p className="text-[10px] text-gray-400 mt-0.5">{DESC_MUN[cfg.fiscal_defaults.codigo_tributacao_municipal]}</p>}</Field>
            <Field label="CNAE"><Input value={cfg.fiscal_defaults.cnae || ''} onChange={(e) => setF('cnae', e.target.value)} placeholder="8211300" />{DESC_CNAE[cfg.fiscal_defaults.cnae] && <p className="text-[10px] text-gray-400 mt-0.5">{DESC_CNAE[cfg.fiscal_defaults.cnae]}</p>}</Field>
            <Field label="cNBS (9 díg.)"><Input value={cfg.fiscal_defaults.codigo_nbs} onChange={(e) => setF('codigo_nbs', e.target.value)} />{DESC_NBS[cfg.fiscal_defaults.codigo_nbs] && <p className="text-[10px] text-gray-400 mt-0.5">{DESC_NBS[cfg.fiscal_defaults.codigo_nbs]}</p>}</Field>
            <Field label="Cód. Trib. Nacional"><Input value={cfg.fiscal_defaults.codigo_tributacao_nacional || ''} onChange={(e) => setF('codigo_tributacao_nacional', e.target.value)} placeholder="170101" />{DESC_CTRIB[cfg.fiscal_defaults.codigo_tributacao_nacional] && <p className="text-[10px] text-gray-400 mt-0.5">{DESC_CTRIB[cfg.fiscal_defaults.codigo_tributacao_nacional]}</p>}</Field>
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
          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Tomador & Serviço (teste)</div>
          <Field label="Cliente (tomador) cadastrado">
            <div className="flex items-center gap-2">
              <select value={teste.cliente_id || ''} onChange={(e) => selecionarCliente(e.target.value)} className="flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm">
                <option value="">Selecionar cliente cadastrado…</option>
                {clientes.map((c) => (<option key={c.id} value={c.id}>{c.name || c.nome}{(c.doc || c.cpf_cnpj) ? ` · ${c.doc || c.cpf_cnpj}` : ''}</option>))}
              </select>
              <button type="button" onClick={() => nav('/dashboard/clientes')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-300 text-emerald-800 px-2.5 py-2 text-xs font-semibold whitespace-nowrap">
                <UserPlus className="w-3.5 h-3.5" /> Clientes
              </button>
            </div>
            <p className="text-[10px] text-gray-400 mt-0.5">Os tomadores das notas vêm do cadastro de <b>Clientes</b>. Escolha um ou preencha abaixo.</p>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Valor do serviço"><Input value={teste.valor} onChange={(e) => setTeste({ ...teste, valor: e.target.value })} /></Field>
            <Field label="Alíquota ISS %"><Input value={teste.aliquota} onChange={(e) => setTeste({ ...teste, aliquota: e.target.value })} /></Field>
            <Field label="Tomador CNPJ"><Input value={teste.cnpj} onChange={(e) => setTeste({ ...teste, cnpj: e.target.value })} /></Field>
            <Field label="Tomador Nome"><Input value={teste.nome} onChange={(e) => setTeste({ ...teste, nome: e.target.value })} /></Field>
          </div>
          <Field label="Discriminação">
            <RichTextEditor
              value={paraEditorHtml(teste.discriminacao)}
              onChange={(h) => setTeste((t) => ({ ...t, discriminacao: h }))}
              onBlurHtml={(h) => setTeste((t) => ({ ...t, discriminacao: h }))}
              minHeight={90}
              showAiButton={true}
              onAiImprove={aperfeicoarDiscriminacao}
            />
            {aiLoading && <p className="text-[10px] text-emerald-700 mt-0.5">✨ Aperfeiçoando com IA…</p>}
            <p className="text-[10px] text-gray-400 mt-0.5">O texto vai para a nota como texto simples (a formatação é só para edição).</p>
          </Field>
          <div className="flex flex-wrap items-center gap-2">
            {isAbrasf && (
              <button onClick={gerarRps} disabled={gerandoRps} className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: VERDE }}>
                {gerandoRps ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCode2 className="w-4 h-4" />} Gerar RPS (XML)
              </button>
            )}
            {isAbrasf && (
              <button onClick={testarEnvio} disabled={enviando} title="Envia o RPS ao Ambiente de TESTE do SpeedGov" className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: '#1d4ed8' }}>
                {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />} Testar envio (homologação)
              </button>
            )}
            {isAbrasf && (
              <button onClick={consultarRps} disabled={consultando} title="Consulta no SpeedGov se a NFS-e foi gerada a partir do RPS nº 1" className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 border border-blue-300 text-blue-800">
                {consultando ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCode2 className="w-4 h-4" />} Consultar NFS-e por RPS
              </button>
            )}
            <button onClick={gerarDps} disabled={gerando} className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 border border-emerald-300 text-emerald-800">
              {gerando ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCode2 className="w-4 h-4" />} Gerar DPS (XML)
            </button>
          </div>
          {rps && (
            <div className="space-y-2">
              <div className={`rounded-lg px-3 py-1.5 text-sm ${rps.valido == null ? 'bg-gray-100 text-gray-600' : rps.valido ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-700'}`}>
                {rps.valido == null ? 'RPS (ABRASF) gerado.' : rps.valido ? '✓ RPS válido contra o XSD oficial do SpeedGov' : `✗ Inválido: ${(rps.erros || []).join(' · ')}`}
              </div>
              <pre className="text-[10px] bg-gray-900 text-emerald-200 rounded-lg p-3 overflow-auto max-h-[360px]">{rps.xml}</pre>
            </div>
          )}
          {envioResp && (
            <div className="space-y-2">
              <div className={`rounded-lg px-3 py-1.5 text-sm ${envioResp.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-700'}`}>
                {envioResp.ok ? '✓ Resposta recebida do SpeedGov:' : `✗ Falha${envioResp.etapa ? ` (${envioResp.etapa})` : ''}: ${envioResp.erro}`}
              </div>
              {renderParsed(envioResp.parsed)}
              {(envioResp.resposta || envioResp.erro) && (
                <pre className="text-[10px] bg-gray-900 text-blue-200 rounded-lg p-3 overflow-auto max-h-[360px] whitespace-pre-wrap">{envioResp.resposta || envioResp.erro}</pre>
              )}
            </div>
          )}
          {consultaResp && (
            <div className="space-y-2">
              <div className={`rounded-lg px-3 py-1.5 text-sm ${consultaResp.ok ? 'bg-blue-50 text-blue-800' : 'bg-red-50 text-red-700'}`}>
                {consultaResp.ok ? '🔎 Consulta NFS-e por RPS — resposta do SpeedGov:' : `✗ ${consultaResp.erro}`}
              </div>
              {renderParsed(consultaResp.parsed)}
              {(consultaResp.resposta || consultaResp.erro) && (
                <pre className="text-[10px] bg-gray-900 text-blue-200 rounded-lg p-3 overflow-auto max-h-[360px] whitespace-pre-wrap">{consultaResp.resposta || consultaResp.erro}</pre>
              )}
            </div>
          )}
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
