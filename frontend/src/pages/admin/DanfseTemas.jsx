// DANFSe — Editar & Gerar. Rota: /dashboard/admin/danfse (admin).
// Formulário dos campos da nota (pré-preenchido c/ a NFS-e 59), Discriminação e Outras
// Informações em RICH TEXT, escolha de tema (Prime I/II/Tradicional) e preview ao vivo.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FileText, Download, Loader2 } from 'lucide-react';
import { adminAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { Input } from '../../components/ui/input';
import RichTextEditor from '../../components/ui/RichTextEditor';
import { paraEditorHtml } from '../../components/ui/RichField';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const TEMAS = [
  { id: 'prime1', nome: 'Prime I', desc: 'Split-diagonal preto × verde', sw: ['#0E0E0E', '#0C3320', '#C9A84C'] },
  { id: 'prime2', nome: 'Prime II', desc: 'Verde gradiente + numeral-fantasma', sw: ['#0C3320', '#15724A', '#C9A84C'] },
  { id: 'tradicional', nome: 'Tradicional', desc: 'Branco serifado, cartorial', sw: ['#FFFFFF', '#EAEAEA', '#8A6D1F'] },
];

// Documento inicial — caso real NFS-e 59 (Açailândia)
const DOC0 = {
  numero_nfse: '0000000059', serie: 'ELETRÔNICA', data_geracao: '12/06/2026', competencia: 'JUN/2026',
  numero_rps: '0', dps_substituida: '0', local_prestacao: 'AÇAILÂNDIA-MA', optante_simples: 'NÃO',
  regime_esp: '0-Nenhum', chave_acesso: '21000551217261987000109000000000005926060160875518',
  prest_razao: 'J R P BEZERRA LTDA', prest_fantasia: 'ROMATEC CONSULTORIA TOTAL',
  prest_endereco: 'RUA MANOEL ELZEBRIO, 14 - NOVA AÇAILÂNDIA - 2ª PART - QUADRA 104',
  prest_cnpj: '17261987000109', prest_im: '26800', prest_uf: 'MA', prest_ie: '0',
  prest_cidade: 'Açailândia', prest_cep: '65930000', prest_fone: '9991811246',
  tom_razao: 'RODO RANCHO COMBUSTIVEIS LTDA', tom_email: 'autopostorancho@...',
  tom_endereco: 'ROD BR010, 15 KM1407 SETOR LADEIRA VERMELHA 65930000 AÇAILÂNDIA-MA',
  tom_cnpj: '57123389000180', tom_im: '0', tom_fone: '',
  discriminacao: '<p>4ª parcela do contrato de serviços de engenharia e agrimensura para a obra comercial <b>Posto Chapadão</b> (Itinga/MA), cliente RODO RANCHO COMBUSTÍVEIS LTDA. Quinzena 09/06/2026 a 22/06/2026. Valor: <b>R$ 17.500,00</b> de um total contratual de R$ 70.000,00.</p>',
  cod_atividade: '1701 / 0 / 821130001 - Serviços de análise, exame, pesquisa, coleta, compilação e fornecimento de dados e informações de qualquer natureza, inclusive cadastro e similares',
  natureza: 'Tributada no Município', cod_validacao: '38ejmlvaqcwns6yt5gurfi42xzo',
  link_consulta: 'https://servicos2.speedgov.com.br/acailandia/', iss_a_reter: 'Não',
  tipo_ret: 'Não Retido', aliq_pis: '1,50', pis: '0,00', aliq_cofins: '1,50', cofins: '0,00',
  inss: '0,00', csll: '0,00', irrf: '0,00',
  valor_servico: '17.500,00', deducao: '0,00', desc_incond: '0,00', desc_cond: '0,00',
  ret_fed: '0,00', outras_ret: '0,00', iss_retido_v: '0,00', aliquota_iss: '2,0000',
  ibs_mun: '0,00', ibs_est: '0,00', cbs: '0,00',
  cno: '', iptu: '', end_obra: '', outras_info: '',
  impressa_em: '12/06/26 12:13', hora_emissao: '12:12:40',
};

const SECOES = [
  { t: 'Identificação', c: [['numero_nfse', 'Nota Nº', 1], ['serie', 'Série', 1], ['data_geracao', 'Data de Geração', 1], ['competencia', 'Competência', 1], ['numero_rps', 'Nº do RPS', 1], ['dps_substituida', 'Nº DPS Substituída', 1], ['local_prestacao', 'Local da Prestação', 2], ['regime_esp', 'Regime Especial', 1], ['optante_simples', 'Optante do Simples', 1], ['chave_acesso', 'Chave de Acesso', 4]] },
  { t: 'Prestador', c: [['prest_razao', 'Razão Social', 2], ['prest_fantasia', 'Nome Fantasia', 2], ['prest_endereco', 'Endereço', 4], ['prest_cnpj', 'CPF/CNPJ', 1], ['prest_im', 'Insc. Municipal', 1], ['prest_uf', 'UF', 1], ['prest_ie', 'Insc. Estadual', 1], ['prest_cidade', 'Cidade', 1], ['prest_cep', 'CEP', 1], ['prest_fone', 'Telefone', 2]] },
  { t: 'Tomador', c: [['tom_razao', 'Razão Social / Nome', 2], ['tom_email', 'E-mail', 2], ['tom_endereco', 'Endereço', 4], ['tom_cnpj', 'CPF/CNPJ', 2], ['tom_im', 'Insc. Municipal', 1], ['tom_fone', 'Telefone', 1]] },
  { t: 'Serviço', rich: 'discriminacao', c: [['cod_atividade', 'Código da Atividade / Serviço', 4], ['natureza', 'Natureza da Operação', 2], ['cod_validacao', 'Código de Validação', 2], ['link_consulta', 'Link de Consulta', 3], ['iss_a_reter', 'ISS a Reter', 1]] },
  { t: 'Valores & ISS', calc: true, c: [['valor_servico', 'Valor dos Serviços', 1], ['deducao', '(-) Dedução em lei', 1], ['desc_incond', '(-) Desc. Incondicionado', 1], ['desc_cond', '(-) Desc. Condicionado', 1], ['ret_fed', '(-) Retenções Federais', 1], ['outras_ret', 'Outras Retenções', 1], ['iss_retido_v', '(-) ISS Retido', 1], ['aliquota_iss', 'Alíquota ISS %', 1]] },
  { t: 'Tributos Federais', c: [['tipo_ret', 'Tipo Retenção', 1], ['aliq_pis', 'Aliq. PIS %', 1], ['pis', 'PIS R$', 1], ['aliq_cofins', 'Aliq. COFINS %', 1], ['cofins', 'COFINS R$', 1], ['inss', 'INSS R$', 1], ['csll', 'CSLL R$', 1], ['irrf', 'IRRF R$', 1]] },
  { t: 'IBS / CBS', c: [['ibs_mun', 'IBS Municipal R$', 1], ['ibs_est', 'IBS Estadual R$', 1], ['cbs', 'CBS R$', 2]] },
  { t: 'Construção Civil', rich: 'outras_info', c: [['cno', 'Código CNO/CEI', 1], ['iptu', 'Insc. Imobiliária (IPTU)', 1], ['end_obra', 'Endereço da Obra', 2]] },
];

const numBR = (v) => { const s = String(v ?? '').replace(/\./g, '').replace(',', '.').replace(/[^0-9.\-]/g, ''); const n = parseFloat(s); return isNaN(n) ? 0 : n; };
const brl = (n) => (n || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function DanfseTemas() {
  const { toast } = useToast();
  const [tema, setTema] = useState('prime1');
  const [doc, setDoc] = useState(DOC0);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const urlRef = useRef(null);
  const debRef = useRef(null);

  const set = (k, v) => setDoc((d) => ({ ...d, [k]: v }));

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const gerar = useCallback(async () => {
    setLoading(true);
    try {
      const blob = await adminAPI.danfsePreview(doc, tema);
      const u = URL.createObjectURL(blob);
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      urlRef.current = u; setPdfUrl(u);
    } catch (e) {
      toast({ title: 'Erro ao gerar DANFSe', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setLoading(false); }
  }, [doc, tema, toast]);

  // preview ao vivo (debounce)
  useEffect(() => {
    if (debRef.current) clearTimeout(debRef.current);
    debRef.current = setTimeout(gerar, 800);
    return () => debRef.current && clearTimeout(debRef.current);
  }, [doc, tema, gerar]);

  const baixar = () => {
    if (!pdfUrl) return;
    const a = document.createElement('a');
    a.href = pdfUrl; a.download = `danfse-${doc.numero_nfse || 'nota'}-${tema}.pdf`;
    document.body.appendChild(a); a.click(); a.remove();
  };

  // cálculo ao vivo
  const base = numBR(doc.valor_servico) - numBR(doc.deducao) - numBR(doc.desc_incond);
  const aliq = numBR(doc.aliquota_iss); const pct = aliq > 0 && aliq <= 1 ? aliq * 100 : aliq;
  const iss = base * pct / 100;
  const liquido = numBR(doc.valor_servico) - numBR(doc.desc_incond) - numBR(doc.desc_cond) - numBR(doc.ret_fed) - numBR(doc.outras_ret) - numBR(doc.iss_retido_v);

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-1 font-display" style={{ color: VERDE }}>DANFSe — Editar & Gerar</h1>
      <p className="text-sm text-gray-500 mb-4">Edite os campos da nota; Discriminação e Outras Informações aceitam formatação (negrito/itálico). O PDF atualiza ao vivo no tema escolhido.</p>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_440px] gap-5">
        {/* Formulário */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-5">
          {SECOES.map((sec) => (
            <div key={sec.t}>
              <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">{sec.t}</div>
              {sec.rich === 'discriminacao' && (
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Discriminação dos Serviços</label>
                  <RichTextEditor value={paraEditorHtml(doc.discriminacao)} onChange={(h) => set('discriminacao', h)} onBlurHtml={(h) => set('discriminacao', h)} minHeight={110} showAiButton={false} />
                </div>
              )}
              <div className="grid grid-cols-4 gap-2">
                {sec.c.map(([k, label, w]) => (
                  <div key={k} className={`col-span-${w} ${w === 4 ? 'sm:col-span-4' : w === 2 ? 'sm:col-span-2' : 'sm:col-span-1'}`} style={{ gridColumn: `span ${w} / span ${w}` }}>
                    <label className="block text-[11px] font-medium text-gray-500 mb-0.5">{label}</label>
                    <Input value={doc[k] ?? ''} onChange={(e) => set(k, e.target.value)} className="text-sm" />
                  </div>
                ))}
              </div>
              {sec.calc && (
                <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
                  <div className="rounded-lg bg-gray-50 border border-gray-100 p-2"><div className="text-[11px] text-gray-500">Base de Cálculo</div><div className="font-semibold text-gray-800">R$ {brl(base)}</div></div>
                  <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-2"><div className="text-[11px] text-gray-500">Valor do ISS</div><div className="font-bold" style={{ color: VERDE }}>R$ {brl(iss)}</div></div>
                  <div className="rounded-lg bg-amber-50 border border-amber-100 p-2"><div className="text-[11px] text-gray-500">Valor Líquido</div><div className="font-bold" style={{ color: '#92600A' }}>R$ {brl(liquido)}</div></div>
                </div>
              )}
              {sec.rich === 'outras_info' && (
                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Outras Informações</label>
                  <RichTextEditor value={paraEditorHtml(doc.outras_info)} onChange={(h) => set('outras_info', h)} onBlurHtml={(h) => set('outras_info', h)} minHeight={70} showAiButton={false} />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Tema + preview */}
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            {TEMAS.map((t) => {
              const ativo = tema === t.id;
              return (
                <button key={t.id} type="button" onClick={() => setTema(t.id)}
                  className={`text-left rounded-lg border-2 p-2 transition ${ativo ? 'shadow' : 'border-gray-200 hover:border-emerald-300'}`}
                  style={ativo ? { borderColor: DOURADO, backgroundColor: '#FBF8F0' } : {}}>
                  <div className="flex gap-1 mb-1">{t.sw.map((cor, i) => <span key={i} className="w-4 h-4 rounded border border-gray-300" style={{ backgroundColor: cor }} />)}</div>
                  <div className="text-xs font-bold text-gray-800">{t.nome}</div>
                  <div className="text-[10px] text-gray-500 leading-tight">{t.desc}</div>
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-sm font-semibold" style={{ color: VERDE }}>
              <FileText className="w-4 h-4" /> Pré-visualização {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            </span>
            <button onClick={baixar} disabled={!pdfUrl}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: VERDE }}>
              <Download className="w-4 h-4" /> Baixar
            </button>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden sticky top-2">
            {pdfUrl ? (
              <iframe title="DANFSe" src={`${pdfUrl}#toolbar=1&navpanes=0`} style={{ width: '100%', height: '76vh', border: 0 }} />
            ) : (
              <div className="h-[76vh] flex items-center justify-center text-gray-400 text-sm">
                <Loader2 className="w-4 h-4 animate-spin mr-2" /> Gerando DANFSe…
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
