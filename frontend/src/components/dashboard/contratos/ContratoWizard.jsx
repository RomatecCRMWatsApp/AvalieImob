// @module contratos/ContratoWizard — Wizard de 11 etapas para criacao/edicao de contratos
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  ArrowLeft, ChevronLeft, ChevronRight, Save, Loader2, Check,
  FileSignature, Building2, Car, Tractor, User, Users, Briefcase,
  MapPin, DollarSign, AlertCircle, Plus, Trash2, Info,
  Sparkles, RotateCcw, Edit2, X, FileText, Shield, AlertTriangle,
  ChevronDown, ChevronUp, Download, Send, Link, MessageCircle,
  Mail, Lock, Eye, Copy, CheckCircle2,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { contratosAPI, perfilAPI, testemunhasAPI, aiAPI, API_BASE } from '../../../lib/api';
import { useAuth } from '../../../contexts/AuthContext';
import ImovelMap from '../../maps/ImovelMap';
import ImageUploader from '../ptam/ImageUploader';
import EtapaConcluidaBox from '../ptam/EtapaConcluidaBox';
import RichTextEditor from '../../ui/RichTextEditor';
import { paraEditorHtml } from '../../ui/RichField';
import { AiButton } from '../ptam/shared/primitives';
import RomaIAAvatar from '../../common/RomaIAAvatar';
import { getWizardConfig, etapaLabel } from '../../../constants/contratoWizardConfig';

/* Papéis, rótulos e descrições por tipo vivem em constants/contratoWizardConfig.js
   (fonte única). Este arquivo só consome via getWizardConfig/etapaLabel. */


/* ─── Tipos de contrato por categoria ───────────────────── */
const TIPOS = [
  {
    categoria: 'Compra e Venda',
    items: [
      { value: 'compra_venda',          label: 'Compra e Venda',          desc: 'Transferência definitiva de propriedade entre vendedor e comprador.' },
      { value: 'promessa_compra_venda', label: 'Promessa C&V',            desc: 'Compromisso de compra e venda, com prazo para escritura definitiva.' },
      { value: 'permuta',               label: 'Permuta',                 desc: 'Troca de bens entre as partes, com ou sem torna.' },
      { value: 'cessao_direitos',       label: 'Cessão de Direitos',      desc: 'Transferência de direitos sobre imóvel em construção ou herança.' },
    ],
  },
  {
    categoria: 'Locação',
    items: [
      { value: 'locacao_residencial', label: 'Locação Residencial', desc: 'Locação de imóvel para fins residenciais — Lei 8.245/91.' },
      { value: 'locacao_comercial',   label: 'Locação Comercial',  desc: 'Locação de imóvel para fins comerciais.' },
      { value: 'comodato',            label: 'Comodato',           desc: 'Empréstimo gratuito de bem móvel ou imóvel.' },
      { value: 'arrendamento_rural',  label: 'Arrendamento Rural', desc: 'Cessão de uso de imóvel rural mediante pagamento.' },
    ],
  },
  {
    categoria: 'Imóvel Rural',
    items: [
      { value: 'parceria_rural', label: 'Parceria Rural', desc: 'Exploração conjunta de imóvel rural com partilha de frutos.' },
      { value: 'doacao',         label: 'Doação',         desc: 'Transferência gratuita de propriedade.' },
    ],
  },
  {
    categoria: 'Outros',
    items: [
      { value: 'arras',                label: 'Arras / Sinal',       desc: 'Recibo de arras confirmatórias ou penitenciais.' },
      { value: 'intermediacao',        label: 'Intermediação',       desc: 'Contrato de corretagem imobiliária — art. 725 CC.' },
      { value: 'exclusividade',        label: 'Exclusividade',       desc: 'Contrato de exclusividade de venda — apenas o corretor indicado pode vender o imóvel por prazo definido, garantindo comissão independentemente de quem trouxer o comprador (art. 725 CC, § 2º + Súmula 335 STJ).' },
      { value: 'usufruto',             label: 'Usufruto',            desc: 'Direito real de uso e gozo de bem alheio.' },
      { value: 'compra_venda_veiculo', label: 'C&V Veículo',         desc: 'Compra e venda de veículo automotor.' },
      { value: 'distrato',             label: 'Distrato',            desc: 'Desfazimento de contrato anterior entre as partes.' },
    ],
  },
];

/* Ênfase jurídica das cláusulas geradas pela IA */
const ENFASE_LABEL = { equilibrada: 'Equilibrada', unilateral_vendedor: 'Pró-vendedor', unilateral_comprador: 'Pró-comprador' };

/* Há preenchimento REAL? (decide se o contrato novo deve ser salvo — evita rascunho vazio) */
const temConteudo = (f) => {
  if (!f) return false;
  const algum = (arr) => (arr || []).some((p) => `${p?.nome || ''}${p?.razao_social || ''}${p?.cpf || ''}${p?.cnpj || ''}`.trim());
  const o = f.objeto || {};
  const objPreenchido = `${o.endereco || ''}${o.endereco_completo || ''}${o.matricula || ''}${o.descricao || ''}${o.descricao_veiculo || ''}${o.placa || ''}`.trim();
  const pagamento = parseFloat(f.pagamento?.valor_total) > 0;
  const clausulas = (f.clausulas || []).length > 0;
  return !!(algum(f.vendedores) || algum(f.compradores) || objPreenchido || pagamento || clausulas);
};

/* ─── Empty form ─────────────────────────────────────────── */
const EMPTY = {
  tipo_contrato: '',
  status: 'MINUTA',
  cidade_assinatura: '',
  data_assinatura: '',
  foro_eleito: '',
  vendedores: [],
  compradores: [],
  corretor: { incluir: false, nome: '', cpf_cnpj: '', creci: '', email: '', telefone: '', nacionalidade: 'brasileiro(a)', profissao: 'Corretor de Imóveis', estado_civil: '', rg: '', rg_orgao: '', cnh: '', cnh_categoria: '', cnh_validade: '', cnh_orgao: '', endereco: '', numero: '', bairro: '', cidade: '', uf: '', cep: '', conjuge_nome: '', conjuge_cpf: '', conjuge_rg: '', regime_bens: '', comissao_percentual: 6, exclusividade: false, prazo_exclusividade: '', comissao_responsavel: 'vendedor', comissao_parcela1_pct: 50, comissao_parcela2_pct: 50, banco: 'Santander', agencia: '1225', conta: '130007144', banco_cnpj: '17.261.987/0001-09', banco_pix: 'romatec.cad@hotmail.com' },
  objeto: { tipo_bem: 'imovel_urbano', endereco: '', bairro: '', cidade: '', uf: '', cep: '', registro_imovel: '', cns: '', matricula: '', latitude: '', longitude: '', endereco_completo: '', area_total: '', area_construida: '', situacao_ocupacao: '', onus: '', benfeitorias: '', ccir: '', car: '', modulos_fiscais: '', descricao_veiculo: '', placa: '', renavam: '', chassi: '', ano_fabricacao: '', cor: '' },
  pagamento: { valor_total: '', arras_valor: '', arras_data: '', arras_tipo: 'confirmatorias', formas: [], penalidades: null },
  config: { incluir_logo: true, incluir_recibo_arras: true, incluir_checklist: true },
};

const EMPTY_PESSOA = { tipo: 'pf', nome: '', cpf: '', rg: '', rg_orgao: '', nascimento: '', estado_civil: '', profissao: '', nacionalidade: 'brasileiro(a)', email: '', telefone: '', endereco: '', cidade: '', uf: '', cep: '', conjuge_nome: '', conjuge_cpf: '', conjuge_rg: '', conjuge_nascimento: '', conjuge_profissao: '', conjuge_nacionalidade: 'brasileiro(a)', conjuge_telefone: '', conjuge_email: '', procurador: false, procurador_nome: '', procurador_cpf: '', procurador_instrumento: '', cnpj: '', razao_social: '', nome_fantasia: '', inscricao_estadual: '', representante_nome: '', representante_cpf: '', representante_cargo: '' };

/* ─── Helpers ────────────────────────────────────────────── */
const Input = ({ label, value, onChange, placeholder, type = 'text', required, note }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      {note && <span className="text-xs text-gray-400 ml-1.5 font-normal">{note}</span>}
    </label>
    <input
      type={type}
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
    />
  </div>
);

const Select = ({ label, value, onChange, options, required }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

const fmtCurrency = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/* ═══════════════════════════════════════════════════════════
   STEP 1 — Tipo de Contrato
═══════════════════════════════════════════════════════════ */
const Step1Tipo = ({ form, setForm }) => (
  <div className="space-y-6">
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Tipo de Contrato</h2>
      <p className="text-sm text-gray-500">Selecione a modalidade contratual. O wizard se adapta ao tipo escolhido.</p>
    </div>

    <div className="bg-gray-50 rounded-xl p-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">Modalidade contratual</label>
      <select
        value={form.tipo_contrato || ''}
        onChange={(e) => setForm({ ...form, tipo_contrato: e.target.value })}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
      >
        <option value="">Selecione o tipo de contrato…</option>
        {TIPOS.map((grupo) => (
          <optgroup key={grupo.categoria} label={grupo.categoria}>
            {grupo.items.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </optgroup>
        ))}
      </select>
      {(() => {
        const sel = TIPOS.flatMap((g) => g.items).find((t) => t.value === form.tipo_contrato);
        return sel ? (
          <p className="text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 mt-2 leading-snug">
            <span className="font-semibold">{sel.label}:</span> {sel.desc}
          </p>
        ) : null;
      })()}
    </div>

    <div className="bg-gray-50 rounded-xl p-4 grid sm:grid-cols-3 gap-4">
      <Input label="Cidade de Assinatura" value={form.cidade_assinatura} onChange={(v) => setForm({ ...form, cidade_assinatura: v })} placeholder="Ex: Cuiabá/MT" />
      <div>
        <Input label="Data de Assinatura" value={form.data_assinatura} onChange={(v) => setForm({ ...form, data_assinatura: v })} type="date" />
        <p className="text-xs text-gray-500 mt-1">🔒 Preenchida automaticamente após todas as assinaturas. Pode deixar em branco.</p>
      </div>
      <Input label="Foro Eleito" value={form.foro_eleito} onChange={(v) => setForm({ ...form, foro_eleito: v })} placeholder="Ex: Comarca de Cuiabá/MT" />
    </div>
  </div>
);

/* ═══════════════════════════════════════════════════════════
   PessoaForm — reutilizado em Step2 e Step3
═══════════════════════════════════════════════════════════ */
const PessoaForm = ({ pessoa, onChange, titulo }) => {
  const upd = (key, val) => onChange({ ...pessoa, [key]: val });

  return (
    <div className="bg-gray-50 rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="font-semibold text-gray-800 text-sm">{titulo}</div>
        <div className="flex gap-2">
          {['pf', 'pj'].map(t => (
            <button
              key={t}
              onClick={() => upd('tipo', t)}
              className={`text-xs px-3 py-1 rounded-lg font-medium transition ${pessoa.tipo === t ? 'bg-emerald-800 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:border-emerald-400'}`}
            >
              {t === 'pf' ? 'Pessoa Física' : 'Pessoa Jurídica'}
            </button>
          ))}
        </div>
      </div>

      {pessoa.tipo === 'pj' ? (
        <div className="grid sm:grid-cols-2 gap-3">
          <Input label="CNPJ" value={pessoa.cnpj} onChange={(v) => upd('cnpj', v)} placeholder="00.000.000/0001-00" />
          <Input label="Razão Social" value={pessoa.razao_social} onChange={(v) => upd('razao_social', v)} required />
          <Input label="Nome Fantasia" value={pessoa.nome_fantasia} onChange={(v) => upd('nome_fantasia', v)} />
          <Input label="Insc. Estadual" value={pessoa.inscricao_estadual} onChange={(v) => upd('inscricao_estadual', v)} />
          <Input label="Representante Legal" value={pessoa.representante_nome} onChange={(v) => upd('representante_nome', v)} required />
          <Input label="CPF do Representante" value={pessoa.representante_cpf} onChange={(v) => upd('representante_cpf', v)} />
          <Input label="Cargo" value={pessoa.representante_cargo} onChange={(v) => upd('representante_cargo', v)} placeholder="Sócio-administrador" />
          <Input label="E-mail" value={pessoa.email} onChange={(v) => upd('email', v)} type="email" />
          <Input label="Telefone" value={pessoa.telefone} onChange={(v) => upd('telefone', v)} placeholder="(65) 99999-9999" />
          <Input label="Endereço" value={pessoa.endereco} onChange={(v) => upd('endereco', v)} />
          <Input label="Cidade" value={pessoa.cidade} onChange={(v) => upd('cidade', v)} />
          <Input label="UF" value={pessoa.uf} onChange={(v) => upd('uf', v)} placeholder="MT" />
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 gap-3">
            <Input label="Nome Completo" value={pessoa.nome} onChange={(v) => upd('nome', v)} required />
            <Input label="CPF" value={pessoa.cpf} onChange={(v) => upd('cpf', v)} placeholder="000.000.000-00" required />
            <Input label="RG" value={pessoa.rg} onChange={(v) => upd('rg', v)} />
            <Input label="Órgão Emissor" value={pessoa.rg_orgao} onChange={(v) => upd('rg_orgao', v)} placeholder="SSP/MT" />
            <Input label="Data de Nascimento" value={pessoa.nascimento} onChange={(v) => upd('nascimento', v)} type="date" />
            <Select
              label="Estado Civil"
              value={pessoa.estado_civil}
              onChange={(v) => upd('estado_civil', v)}
              options={[
                { value: '', label: 'Selecione...' },
                { value: 'solteiro', label: 'Solteiro(a)' },
                { value: 'casado', label: 'Casado(a)' },
                { value: 'uniao_estavel', label: 'União Estável' },
                { value: 'separado', label: 'Separado(a)' },
                { value: 'divorciado', label: 'Divorciado(a)' },
                { value: 'viuvo', label: 'Viúvo(a)' },
              ]}
            />
            <Input label="Profissão" value={pessoa.profissao} onChange={(v) => upd('profissao', v)} />
            <Input label="Nacionalidade" value={pessoa.nacionalidade} onChange={(v) => upd('nacionalidade', v)} />
            <Input label="CNH (nº de registro)" value={pessoa.cnh} onChange={(v) => upd('cnh', v)} placeholder="00000000000" />
            <Select
              label="Categoria da CNH"
              value={pessoa.cnh_categoria}
              onChange={(v) => upd('cnh_categoria', v)}
              options={[
                { value: '', label: 'Selecione...' },
                { value: 'A', label: 'A' }, { value: 'B', label: 'B' }, { value: 'AB', label: 'AB' },
                { value: 'C', label: 'C' }, { value: 'D', label: 'D' }, { value: 'E', label: 'E' },
                { value: 'AC', label: 'AC' }, { value: 'AD', label: 'AD' }, { value: 'AE', label: 'AE' },
              ]}
            />
            <Input label="Validade da CNH" value={pessoa.cnh_validade} onChange={(v) => upd('cnh_validade', v)} type="date" />
            <Input label="Órgão Expedidor da CNH" value={pessoa.cnh_orgao} onChange={(v) => upd('cnh_orgao', v)} placeholder="DETRAN/MT" />
            <Input label="Nome da Mãe (filiação)" value={pessoa.filiacao_mae} onChange={(v) => upd('filiacao_mae', v)} />
            <Input label="Nome do Pai (filiação)" value={pessoa.filiacao_pai} onChange={(v) => upd('filiacao_pai', v)} />
            <Input label="E-mail" value={pessoa.email} onChange={(v) => upd('email', v)} type="email" />
            <Input label="Telefone" value={pessoa.telefone} onChange={(v) => upd('telefone', v)} placeholder="(65) 99999-9999" />
            <Input label="Endereço" value={pessoa.endereco} onChange={(v) => upd('endereco', v)} />
            <Input label="Cidade" value={pessoa.cidade} onChange={(v) => upd('cidade', v)} />
            <Input label="UF" value={pessoa.uf} onChange={(v) => upd('uf', v)} placeholder="MT" />
            <Input label="CEP" value={pessoa.cep} onChange={(v) => upd('cep', v)} placeholder="00000-000" />
          </div>

          {/* Cônjuge — CC art. 1.647 */}
          {(pessoa.estado_civil === 'casado' || pessoa.estado_civil === 'uniao_estavel') && (
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2 text-amber-800 text-xs font-semibold">
                <AlertCircle className="w-3.5 h-3.5" /> CC art. 1.647 — Outorga conjugal obrigatória
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input label="Nome do Cônjuge" value={pessoa.conjuge_nome} onChange={(v) => upd('conjuge_nome', v)} required />
                <Input label="CPF do Cônjuge" value={pessoa.conjuge_cpf} onChange={(v) => upd('conjuge_cpf', v)} placeholder="000.000.000-00" required />
                <Input label="RG do Cônjuge" value={pessoa.conjuge_rg} onChange={(v) => upd('conjuge_rg', v)} />
                <Input label="Órgão Emissor (Cônjuge)" value={pessoa.conjuge_rg_orgao} onChange={(v) => upd('conjuge_rg_orgao', v)} placeholder="SSP/MT" />
                <Input label="Nascimento" value={pessoa.conjuge_nascimento} onChange={(v) => upd('conjuge_nascimento', v)} type="date" />
                <Input label="Profissão" value={pessoa.conjuge_profissao} onChange={(v) => upd('conjuge_profissao', v)} />
                <Input label="Nacionalidade" value={pessoa.conjuge_nacionalidade} onChange={(v) => upd('conjuge_nacionalidade', v)} />
                <Input label="CNH do Cônjuge (nº)" value={pessoa.conjuge_cnh} onChange={(v) => upd('conjuge_cnh', v)} placeholder="00000000000" />
                <Select
                  label="Categoria da CNH (Cônjuge)"
                  value={pessoa.conjuge_cnh_categoria}
                  onChange={(v) => upd('conjuge_cnh_categoria', v)}
                  options={[
                    { value: '', label: 'Selecione...' },
                    { value: 'A', label: 'A' }, { value: 'B', label: 'B' }, { value: 'AB', label: 'AB' },
                    { value: 'C', label: 'C' }, { value: 'D', label: 'D' }, { value: 'E', label: 'E' },
                    { value: 'AC', label: 'AC' }, { value: 'AD', label: 'AD' }, { value: 'AE', label: 'AE' },
                  ]}
                />
                <Input label="Validade da CNH (Cônjuge)" value={pessoa.conjuge_cnh_validade} onChange={(v) => upd('conjuge_cnh_validade', v)} type="date" />
                <Input label="Órgão Expedidor da CNH (Cônjuge)" value={pessoa.conjuge_cnh_orgao} onChange={(v) => upd('conjuge_cnh_orgao', v)} placeholder="DETRAN/MT" />
                <Input label="Nome da Mãe do Cônjuge" value={pessoa.conjuge_filiacao_mae} onChange={(v) => upd('conjuge_filiacao_mae', v)} />
                <Input label="Nome do Pai do Cônjuge" value={pessoa.conjuge_filiacao_pai} onChange={(v) => upd('conjuge_filiacao_pai', v)} />
                <Input label="Contato / WhatsApp do Cônjuge" value={pessoa.conjuge_telefone || ''} onChange={(v) => upd('conjuge_telefone', v)} placeholder="(99) 99999-9999" />
                <Input label="E-mail do Cônjuge" value={pessoa.conjuge_email || ''} onChange={(v) => upd('conjuge_email', v)} type="email" placeholder="email@exemplo.com" />
              </div>
            </div>
          )}

          {/* Procurador */}
          <div className="mt-2">
            <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-700">
              <input
                type="checkbox"
                checked={!!pessoa.procurador}
                onChange={(e) => upd('procurador', e.target.checked)}
                className="rounded"
              />
              Representado por procurador
            </label>
            {pessoa.procurador && (
              <div className="grid sm:grid-cols-2 gap-3 mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <Input label="Nome do Procurador" value={pessoa.procurador_nome} onChange={(v) => upd('procurador_nome', v)} required />
                <Input label="CPF do Procurador" value={pessoa.procurador_cpf} onChange={(v) => upd('procurador_cpf', v)} />
                <Input label="Instrumento de Procuração" value={pessoa.procurador_instrumento} onChange={(v) => upd('procurador_instrumento', v)} placeholder="Ex: Pública, livro X, folha Y, Cartório Z" className="sm:col-span-2" />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 4 — Corretor (etapa própria; StepParte cobre as demais partes)
═══════════════════════════════════════════════════════════ */
const Step4Corretor = ({ form, setForm, perfil, corretorLabel }) => {
  const parte3 = 'Corretor';
  const cor = form.corretor;
  const upd = (key, val) => setForm({ ...form, corretor: { ...cor, [key]: val } });

  // Prazo de exclusividade dinâmico: data inicial + dias → calcula a data final.
  const calcDataFim = (inicio, dias) => {
    if (!inicio || !dias) return '';
    const d = new Date(`${inicio}T00:00:00`);
    if (isNaN(d.getTime())) return '';
    d.setDate(d.getDate() + Number(dias));
    return d.toISOString().slice(0, 10);
  };
  const fmtBR = (iso) => (iso ? iso.split('-').reverse().join('/') : '');
  const updPrazo = (patch) => {
    const next = { ...cor, ...patch };
    let dataFim = '';
    let texto = '';
    if (next.exclusividade_indeterminado) {
      texto = 'Prazo indeterminado';
    } else if (next.exclusividade_data_inicio && next.exclusividade_prazo_dias) {
      dataFim = calcDataFim(next.exclusividade_data_inicio, next.exclusividade_prazo_dias);
      texto = `${next.exclusividade_prazo_dias} dias, de ${fmtBR(next.exclusividade_data_inicio)} a ${fmtBR(dataFim)}`;
    }
    setForm({
      ...form,
      regime_prazo: next.exclusividade_indeterminado ? 'indeterminado' : 'determinado',
      corretor: { ...next, exclusividade_data_fim: dataFim, prazo_exclusividade: texto },
    });
  };
  const prazoDataFim = cor.exclusividade_indeterminado
    ? '' : calcDataFim(cor.exclusividade_data_inicio, cor.exclusividade_prazo_dias);

  const valorComissao = cor.comissao_percentual && form.pagamento?.valor_total
    ? (parseFloat(form.pagamento.valor_total) * parseFloat(cor.comissao_percentual)) / 100
    : null;

  const usarMeusDados = () => {
    if (!perfil) return;
    const creciReg = (perfil.registros || []).find(r => (r.tipo || '').toUpperCase().includes('CRECI'));
    const creci = creciReg ? `CRECI${creciReg.uf ? '/' + creciReg.uf : ''} ${creciReg.numero}` : cor.creci;
    setForm({
      ...form,
      corretor: {
        ...cor,
        nome: perfil.nome_completo || cor.nome,
        email: perfil.email_profissional || perfil.email || cor.email,
        telefone: perfil.telefone || cor.telefone,
        creci,
        cpf_cnpj: perfil.cpf || cor.cpf_cnpj,
        endereco: perfil.endereco_escritorio || cor.endereco,
        cidade: perfil.cidade || cor.cidade,
        uf: perfil.uf || cor.uf,
        cep: perfil.cep || cor.cep,
        profissao: cor.profissao || 'Corretor de Imóveis',
        nacionalidade: cor.nacionalidade || 'brasileiro(a)',
      },
    });
  };

  const titulo = corretorLabel || 'Corretor de Imóveis';
  const descricao = 'Dados do corretor/escritório responsável pela intermediação.';

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">{titulo}</h2>
        <p className="text-sm text-gray-500">{descricao}</p>
      </div>

      <label className="flex items-center gap-2 cursor-pointer select-none text-sm font-medium text-gray-700 bg-gray-50 p-3 rounded-xl">
        <input
          type="checkbox"
          checked={!!cor.incluir}
          onChange={(e) => upd('incluir', e.target.checked)}
          className="rounded"
        />
        Incluir {parte3.toLowerCase()} neste contrato
      </label>

      {cor.incluir && (
        <div className="space-y-4">
          {parte3 === 'Corretor' && (
            <div className="flex justify-end">
              <Button
                size="sm"
                variant="outline"
                onClick={usarMeusDados}
                className="text-emerald-700 border-emerald-300 hover:bg-emerald-50"
              >
                <User className="w-3.5 h-3.5 mr-1.5" /> Usar meus dados
              </Button>
            </div>
          )}

          <div className="bg-gray-50 rounded-xl p-4 grid sm:grid-cols-2 gap-3">
            <Input label={`Nome do ${parte3}`} value={cor.nome} onChange={(v) => upd('nome', v)} required />
            {parte3 === 'Corretor' && (
              <Input label="CRECI" value={cor.creci} onChange={(v) => upd('creci', v)} placeholder="CRECI/MA 4705" />
            )}
            {(parte3 === 'Fiador' || parte3 === 'Corretor') && (
              <Input label="CPF" value={cor.cpf_cnpj} onChange={(v) => upd('cpf_cnpj', v)} placeholder="000.000.000-00" />
            )}
            <Input label="E-mail" value={cor.email} onChange={(v) => upd('email', v)} type="email" />
            <Input label="Telefone" value={cor.telefone} onChange={(v) => upd('telefone', v)} placeholder="(65) 99999-9999" />
            {parte3 === 'Corretor' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Comissão (%)</label>
                <input
                  type="number"
                  min="0" max="100" step="0.1"
                  value={cor.comissao_percentual ?? 6}
                  onChange={(e) => upd('comissao_percentual', e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                {valorComissao !== null && (
                  <p className="text-xs text-emerald-700 font-semibold mt-1">
                    = {fmtCurrency(valorComissao)}
                  </p>
                )}
              </div>
            )}
          </div>

          {parte3 === 'Corretor' && (
            <div className="bg-gray-50 rounded-xl p-4 space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Qualificação completa do corretor (vai ao contrato e à procuração)</p>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input label="Nacionalidade" value={cor.nacionalidade} onChange={(v) => upd('nacionalidade', v)} placeholder="brasileiro(a)" />
                <Input label="Profissão" value={cor.profissao} onChange={(v) => upd('profissao', v)} placeholder="Corretor de Imóveis" />
                <Select label="Estado Civil" value={cor.estado_civil || ''} onChange={(v) => upd('estado_civil', v)}
                  options={[{ value: '', label: '—' }, { value: 'solteiro(a)', label: 'Solteiro(a)' }, { value: 'casado(a)', label: 'Casado(a)' }, { value: 'união estável', label: 'União estável' }, { value: 'divorciado(a)', label: 'Divorciado(a)' }, { value: 'viúvo(a)', label: 'Viúvo(a)' }]} />
                <Input label="RG" value={cor.rg} onChange={(v) => upd('rg', v)} placeholder="Nº do RG" />
                <Input label="Órgão Emissor do RG" value={cor.rg_orgao} onChange={(v) => upd('rg_orgao', v)} placeholder="SSP/MA" />
                <Input label="CNH (nº registro)" value={cor.cnh} onChange={(v) => upd('cnh', v)} />
                <Select label="Categoria da CNH" value={cor.cnh_categoria || ''} onChange={(v) => upd('cnh_categoria', v)}
                  options={[{ value: '', label: '—' }, ...['A', 'B', 'AB', 'C', 'D', 'E', 'AC', 'AD', 'AE'].map(x => ({ value: x, label: x }))]} />
                <Input label="Validade da CNH" type="date" value={cor.cnh_validade} onChange={(v) => upd('cnh_validade', v)} />
              </div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide pt-1">Endereço profissional</p>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input label="Logradouro" value={cor.endereco} onChange={(v) => upd('endereco', v)} placeholder="Rua / Av." />
                <Input label="Número" value={cor.numero} onChange={(v) => upd('numero', v)} />
                <Input label="Bairro" value={cor.bairro} onChange={(v) => upd('bairro', v)} />
                <Input label="Cidade" value={cor.cidade} onChange={(v) => upd('cidade', v)} />
                <Input label="UF" value={cor.uf} onChange={(v) => upd('uf', v)} placeholder="MA" />
                <Input label="CEP" value={cor.cep} onChange={(v) => upd('cep', v)} placeholder="00000-000" />
              </div>
              {['casado(a)', 'união estável'].includes(cor.estado_civil) && (
                <>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide pt-1">Cônjuge</p>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <Input label="Nome do Cônjuge" value={cor.conjuge_nome} onChange={(v) => upd('conjuge_nome', v)} />
                    <Input label="CPF do Cônjuge" value={cor.conjuge_cpf} onChange={(v) => upd('conjuge_cpf', v)} placeholder="000.000.000-00" />
                    <Input label="RG do Cônjuge" value={cor.conjuge_rg} onChange={(v) => upd('conjuge_rg', v)} />
                    <Input label="Regime de Bens" value={cor.regime_bens} onChange={(v) => upd('regime_bens', v)} placeholder="comunhão parcial de bens" />
                  </div>
                </>
              )}
            </div>
          )}

          {parte3 === 'Corretor' && (
            <>
              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Responsável e Parcelas da Comissão</p>
                <Select
                  label="Responsável pelo pagamento"
                  value={cor.comissao_responsavel || 'vendedor'}
                  onChange={(v) => upd('comissao_responsavel', v)}
                  options={[
                    { value: 'vendedor', label: 'Vendedor' },
                    { value: 'comprador', label: 'Comprador' },
                    { value: 'ambos', label: 'Ambos (50/50)' },
                  ]}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Input label="1ª parcela (% no sinal)" value={cor.comissao_parcela1_pct ?? 50} onChange={(v) => upd('comissao_parcela1_pct', v)} type="number" placeholder="50" />
                  <Input label="2ª parcela (% na quitação)" value={cor.comissao_parcela2_pct ?? 50} onChange={(v) => upd('comissao_parcela2_pct', v)} type="number" placeholder="50" />
                </div>
              </div>

              <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 space-y-3">
                <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide">Dados Bancários para Recebimento</p>
                <div className="grid sm:grid-cols-3 gap-3">
                  <Input label="Banco" value={cor.banco || ''} onChange={(v) => upd('banco', v)} placeholder="Santander" />
                  <Input label="Agência" value={cor.agencia || ''} onChange={(v) => upd('agencia', v)} placeholder="1225" />
                  <Input label="Conta Corrente" value={cor.conta || ''} onChange={(v) => upd('conta', v)} placeholder="130007144" />
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <Input label="CNPJ/CPF da conta" value={cor.banco_cnpj || ''} onChange={(v) => upd('banco_cnpj', v)} placeholder="17.261.987/0001-09" />
                  <Input label="Chave PIX" value={cor.banco_pix || ''} onChange={(v) => upd('banco_pix', v)} placeholder="romatec.cad@hotmail.com" />
                </div>
              </div>
            </>
          )}

          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-700">
              <input
                type="checkbox"
                checked={!!cor.exclusividade}
                onChange={(e) => upd('exclusividade', e.target.checked)}
                className="rounded"
              />
              Cláusula de exclusividade
            </label>
            {cor.exclusividade && (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-4 text-sm text-gray-700">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="radio" checked={!cor.exclusividade_indeterminado}
                           onChange={() => updPrazo({ exclusividade_indeterminado: false })} />
                    Prazo determinado
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="radio" checked={!!cor.exclusividade_indeterminado}
                           onChange={() => updPrazo({ exclusividade_indeterminado: true })} />
                    Prazo indeterminado
                  </label>
                </div>

                {!cor.exclusividade_indeterminado ? (
                  <>
                    <div className="grid sm:grid-cols-2 gap-3">
                      <Input label="Data inicial" type="date" value={cor.exclusividade_data_inicio}
                             onChange={(v) => updPrazo({ exclusividade_data_inicio: v })} />
                      <Input label="Quantidade de dias" type="number" value={cor.exclusividade_prazo_dias}
                             onChange={(v) => updPrazo({ exclusividade_prazo_dias: v })} placeholder="Ex: 90" />
                    </div>
                    {prazoDataFim ? (
                      <div className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
                        Data final: <b>{fmtBR(prazoDataFim)}</b>
                        <span className="text-emerald-600"> ({cor.exclusividade_prazo_dias} dias a partir de {fmtBR(cor.exclusividade_data_inicio)})</span>
                      </div>
                    ) : (
                      <p className="text-xs text-gray-400">Informe a data inicial e a quantidade de dias para calcular a data final.</p>
                    )}
                  </>
                ) : (
                  <div className="text-sm text-gray-600 bg-gray-100 rounded-lg px-3 py-2">
                    Vigência por <b>prazo indeterminado</b>, podendo ser denunciado por qualquer das partes mediante aviso prévio.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 5 — Objeto
═══════════════════════════════════════════════════════════ */
const Step5Objeto = ({ form, setForm }) => {
  const obj = form.objeto;
  const upd = (key, val) => setForm({ ...form, objeto: { ...obj, [key]: val } });

  // Marca a localização no mapa: grava lat/lng e busca o endereço (reverse-geocode)
  // SEM sobrescrever o que o usuário já editou no campo "Endereço completo".
  const marcarNoMapa = async (la, ln) => {
    setForm((f) => ({ ...f, objeto: { ...f.objeto, latitude: String(la), longitude: String(ln) } }));
    try {
      const r = await fetch(`${API_BASE}/maps/reverse?lat=${la}&lng=${ln}`);
      if (!r.ok) return;
      const d = await r.json();
      if (d?.endereco) {
        setForm((f) => (
          (f.objeto.endereco_completo || '').trim()
            ? f
            : { ...f, objeto: { ...f.objeto, endereco_completo: d.endereco } }
        ));
      }
    } catch { /* best-effort */ }
  };
  const buscarEnderecoDasCoords = async () => {
    if (!obj.latitude || !obj.longitude) return;
    try {
      const r = await fetch(`${API_BASE}/maps/reverse?lat=${obj.latitude}&lng=${obj.longitude}`);
      if (!r.ok) return;
      const d = await r.json();
      if (d?.endereco) upd('endereco_completo', d.endereco);
    } catch { /* best-effort */ }
  };

  // Alienação fiduciária / financiamento (sub-objeto obj.alienacao)
  const al = obj.alienacao || {};
  const setAl = (patch) => upd('alienacao', { ...al, ...patch });
  const setAlGrp = (grp, patch) => setAl({ [grp]: { ...(al[grp] || {}), ...patch } });
  const PROG_LEI = {
    MCMV: 'Lei nº 11.977/2009, reeditado pela Lei nº 14.620/2023',
    SFH: 'Lei nº 4.380/1964',
    SFI: 'Lei nº 9.514/1997',
    PRO_COTISTA: 'Resolução CCFGTS — recursos FGTS',
  };
  const numDocsImovel = (obj.documentos_imovel || []).length;

  // Aperfeiçoar com IA (campos de texto longo do imóvel)
  const { toast: toastObj } = useToast();
  const [aiCampo, setAiCampo] = useState(null);
  const aperfeicoarCampo = async (campo, instrucao) => {
    const atual = (obj[campo] || '').replace(/<[^>]+>/g, ' ').trim();
    const prompt =
      `${instrucao} Mantenha tom formal, jurídico e claro em português-BR, conciso. ` +
      'Retorne APENAS o texto aperfeiçoado, sem explicações, títulos ou rótulos.\n\n' +
      `Imóvel: ${obj.endereco || ''} ${obj.matricula ? '— matrícula ' + obj.matricula : ''}\n` +
      `Texto atual:\n${atual || '(vazio — gere um texto inicial adequado)'}`;
    setAiCampo(campo);
    try {
      const res = await aiAPI.chat(`contrato_objeto_${campo}_${Date.now()}`, prompt);
      const texto = (res?.reply || '').trim();
      if (texto) upd(campo, texto);
      toastObj({ title: 'Texto aperfeiçoado com IA' });
    } catch (e) {
      toastObj({ title: 'Erro na IA', description: e.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
    } finally {
      setAiCampo(null);
    }
  };

  const somaValores = ['entrada_recursos_proprios', 'subsidio', 'valor_financiado']
    .reduce((s, k) => s + (parseFloat((al.valores || {})[k]) || 0), 0);
  const valorCompra = parseFloat((al.valores || {}).valor_compra) || 0;
  const divergeValores = valorCompra > 0 && somaValores > 0 && Math.abs(somaValores - valorCompra) > 0.01;

  const enderecoCompleto = [obj.endereco, obj.bairro, obj.cidade, obj.uf].filter(Boolean).join(', ');

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Objeto do Contrato</h2>
        <p className="text-sm text-gray-500">Descreva o bem objeto da negociação.</p>
      </div>

      <Select
        label="Tipo do Bem"
        value={obj.tipo_bem}
        onChange={(v) => upd('tipo_bem', v)}
        options={[
          { value: 'imovel_urbano', label: 'Imóvel Urbano' },
          { value: 'imovel_rural', label: 'Imóvel Rural' },
          { value: 'veiculo', label: 'Veículo' },
        ]}
        required
      />

      {/* Imóvel Urbano */}
      {obj.tipo_bem === 'imovel_urbano' && (
        <div className="space-y-4">
          <div className="bg-gray-50 rounded-xl p-4 grid sm:grid-cols-2 gap-3">
            <div className="sm:col-span-2">
              <Input label="Endereço" value={obj.endereco} onChange={(v) => upd('endereco', v)} placeholder="Rua, número, complemento" required />
            </div>
            <Input label="Bairro" value={obj.bairro} onChange={(v) => upd('bairro', v)} />
            <Input label="Cidade" value={obj.cidade} onChange={(v) => upd('cidade', v)} />
            <Input label="UF" value={obj.uf} onChange={(v) => upd('uf', v)} placeholder="MT" />
            <Input label="CEP" value={obj.cep} onChange={(v) => upd('cep', v)} placeholder="00000-000" />
            <Input label="Matrícula" value={obj.matricula} onChange={(v) => upd('matricula', v)} placeholder="Nº da matrícula no CRI" />
            <Input label="Serventia / Cartório (Registro de Imóveis)" value={obj.registro_imovel} onChange={(v) => upd('registro_imovel', v)} placeholder="Ex: 1º Ofício de Registro de Imóveis de Açailândia/MA" />
            <Input label="CNS da Serventia" value={obj.cns} onChange={(v) => upd('cns', v)} placeholder="Código Nacional da Serventia (ex: 12.345-6)" />
            <Input label="Latitude (grau decimal)" value={obj.latitude} onChange={(v) => upd('latitude', v)} placeholder="-4.932001" />
            <Input label="Longitude (grau decimal)" value={obj.longitude} onChange={(v) => upd('longitude', v)} placeholder="-47.515477" />
            <div className="sm:col-span-2 -mt-1">
              <p className="text-xs text-gray-500">📍 Coordenadas do imóvel (SINCETI/mapa). Vão para o contrato com o mapa de localização. {obj.latitude && obj.longitude ? <a className="text-emerald-700 underline" href={`https://www.openstreetmap.org/?mlat=${obj.latitude}&mlon=${obj.longitude}#map=17/${obj.latitude}/${obj.longitude}`} target="_blank" rel="noreferrer">ver no mapa</a> : null}</p>
            </div>
            <Input label="Área Total (m²)" value={obj.area_total} onChange={(v) => upd('area_total', v)} type="number" />
            <Input label="Área Construída (m²)" value={obj.area_construida} onChange={(v) => upd('area_construida', v)} type="number" />
            <Select
              label="Situação de Ocupação"
              value={obj.situacao_ocupacao}
              onChange={(v) => upd('situacao_ocupacao', v)}
              options={[
                { value: '', label: 'Selecione...' },
                { value: 'desocupado', label: 'Desocupado' },
                { value: 'ocupado_vendedor', label: 'Ocupado pelo Vendedor' },
                { value: 'ocupado_terceiros', label: 'Ocupado por Terceiros' },
                { value: 'locado', label: 'Locado' },
              ]}
            />
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Ônus / Gravames</label>
              <RichTextEditor
                value={paraEditorHtml(obj.onus)}
                onChange={(html) => upd('onus', html)}
                onBlurHtml={(html) => upd('onus', html)}
                placeholder="Ex: Livre e desembaraçado de quaisquer ônus ou inscrever gravame específico"
                minHeight={140}
                showAiButton={false}
              />
              <div className="flex justify-end mt-1">
                <AiButton onClick={() => aperfeicoarCampo('onus', 'A partir do texto abaixo — que pode conter o HISTÓRICO REGISTRAL da matrícula (protocolos, registros R-xx, averbações AV-xx, selos, emolumentos, partes anteriores) — redija uma DECLARAÇÃO DE ÔNUS E GRAVAMES concisa e formal para o contrato: diga objetivamente se o imóvel está livre e desembaraçado de ônus OU descreva apenas os gravames VIGENTES (ex.: alienação fiduciária/hipoteca em favor do credor, citando só o registro R-xx pertinente), em no máximo 2 ou 3 frases. NÃO reproduza o histórico registral completo, números de protocolo, selo ou emolumentos.')} loading={aiCampo === 'onus'} />
              </div>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Benfeitorias Incluídas</label>
              <RichTextEditor
                value={paraEditorHtml(obj.benfeitorias)}
                onChange={(html) => upd('benfeitorias', html)}
                onBlurHtml={(html) => upd('benfeitorias', html)}
                placeholder="Ex: Incluídas as instalações elétricas, hidráulicas e etc."
                minHeight={140}
                showAiButton={false}
              />
              <div className="flex justify-end mt-1">
                <AiButton onClick={() => aperfeicoarCampo('benfeitorias', 'A partir do texto abaixo (que pode trazer a averbação/habite-se com protocolos e selos), redija uma descrição CONCISA e formal das benfeitorias/edificação incluídas no negócio (tipo da construção, padrão, área construída e principais cômodos), em 1 a 3 frases. NÃO reproduza números de protocolo, selo, emolumentos nem o texto registral integral.')} loading={aiCampo === 'benfeitorias'} />
              </div>
            </div>
          </div>

          {/* Ficha completa do imóvel (BCI/IPTU/medidas/alienação/fotos/docs) — para TODOS os tipos */}
          {(
            <div className="space-y-4">
              {/* Cadastro Imobiliário Municipal (BCI) */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-3">Cadastro Imobiliário Municipal (BCI)</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  <Input label="Código do Imóvel (CTI)" value={obj.cti || ''} onChange={(v) => upd('cti', v)} />
                  <Input label="Inscrição Cadastral" value={obj.inscricao_cadastral || ''} onChange={(v) => upd('inscricao_cadastral', v)} />
                  <Input label="Setor" value={obj.setor || ''} onChange={(v) => upd('setor', v)} />
                  <Input label="Quadra" value={obj.quadra || ''} onChange={(v) => upd('quadra', v)} />
                  <Input label="Lote" value={obj.lote || ''} onChange={(v) => upd('lote', v)} />
                  <Input label="Unidade" value={obj.unidade || ''} onChange={(v) => upd('unidade', v)} />
                  <Input label="Situação Cadastral" value={obj.situacao_cadastral || ''} onChange={(v) => upd('situacao_cadastral', v)} />
                  <Input label="Natureza" value={obj.natureza || ''} onChange={(v) => upd('natureza', v)} />
                  <Input label="Data de Cadastro" type="date" value={obj.data_cadastro || ''} onChange={(v) => upd('data_cadastro', v)} />
                  <Input label="Data de Construção" type="date" value={obj.data_construcao || ''} onChange={(v) => upd('data_construcao', v)} />
                </div>
              </div>

              {/* Proprietário / Detentor (BCI) */}
              <div className="grid sm:grid-cols-2 gap-3">
                <Input label="Proprietário/Detentor (BCI)" value={obj.proprietario_bci_nome || ''} onChange={(v) => upd('proprietario_bci_nome', v)} placeholder="Conforme BCI" />
                <Input label="CPF/CNPJ (BCI)" value={obj.proprietario_bci_doc || ''} onChange={(v) => upd('proprietario_bci_doc', v)} />
              </div>

              {/* Medidas do Imóvel (BCI) */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-3">Medidas do Imóvel (BCI)</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  <Input label="Testada Principal (m)" type="number" value={obj.testada_principal || ''} onChange={(v) => upd('testada_principal', v)} />
                  <Input label="Profundidade do Lote (m)" type="number" value={obj.profundidade_lote || ''} onChange={(v) => upd('profundidade_lote', v)} />
                  <Input label="Área do Terreno (m²)" type="number" value={obj.area_terreno || ''} onChange={(v) => upd('area_terreno', v)} />
                  <Input label="Área da Edificação (m²)" type="number" value={obj.area_edificacao || ''} onChange={(v) => upd('area_edificacao', v)} />
                  <Input label="Área Total da Edificação (m²)" type="number" value={obj.area_total_edificacao || ''} onChange={(v) => upd('area_total_edificacao', v)} />
                </div>
              </div>

              {/* IPTU */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-3">IPTU</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  <Input label="Inscrição do Contribuinte" value={obj.iptu_inscricao_contribuinte || ''} onChange={(v) => upd('iptu_inscricao_contribuinte', v)} />
                  <Input label="Exercício de Referência" value={obj.iptu_exercicio || ''} onChange={(v) => upd('iptu_exercicio', v)} />
                  <Input label="Valor Anual do IPTU (R$)" type="number" value={obj.iptu_valor_anual || ''} onChange={(v) => upd('iptu_valor_anual', v)} />
                  <Select label="Situação do IPTU" value={obj.iptu_situacao || ''} onChange={(v) => upd('iptu_situacao', v)}
                          options={[{ value: '', label: 'Selecione...' }, { value: 'quitado', label: 'Quitado' }, { value: 'parcelado', label: 'Parcelado' }, { value: 'em_debito', label: 'Em débito' }, { value: 'isento', label: 'Isento' }]} />
                  <Input label="Vencimento" type="date" value={obj.iptu_vencimento || ''} onChange={(v) => upd('iptu_vencimento', v)} />
                  <Input label="Débito Total / Valor em Aberto (R$)" type="number" value={obj.iptu_debito_total || ''} onChange={(v) => upd('iptu_debito_total', v)} />
                  <Input label="Desconto Concedido (R$)" type="number" value={obj.iptu_desconto || ''} onChange={(v) => upd('iptu_desconto', v)} />
                  <Input label="Valor Cobrado / a Pagar (R$)" type="number" value={obj.iptu_valor_cobrado || ''} onChange={(v) => upd('iptu_valor_cobrado', v)} />
                </div>
              </div>

              {/* Imóvel alienado / financiado — alienação fiduciária */}
              <div className="rounded-xl border border-gray-200 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-800">Imóvel alienado / financiado?</p>
                    <p className="text-xs text-gray-500">Ative se o imóvel possui alienação fiduciária ou financiamento registrado na matrícula.</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={!!al.alienado}
                    onClick={() => setAl({ alienado: !al.alienado })}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition focus:outline-none focus:ring-2 focus:ring-[#C9A84C] ${al.alienado ? 'bg-[#0C3320]' : 'bg-gray-300'}`}
                  >
                    <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${al.alienado ? 'translate-x-5' : 'translate-x-1'}`} />
                  </button>
                </div>

                {al.alienado && (
                  <div className="mt-4 space-y-4">
                    {/* Bloco A — Credor Fiduciário */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-2">Credor Fiduciário</p>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Input label="Banco / Credor Fiduciário" value={(al.credor || {}).nome || ''} onChange={(v) => setAlGrp('credor', { nome: v })} placeholder="Banco do Brasil S.A." required />
                        <Input label="CNPJ do Credor" value={(al.credor || {}).cnpj || ''} onChange={(v) => setAlGrp('credor', { cnpj: v })} placeholder="00.000.000/0001-91" required />
                        <Input label="Agência" value={(al.credor || {}).agencia || ''} onChange={(v) => setAlGrp('credor', { agencia: v })} placeholder="Ag. Parque das Nações-MA, prefixo 5908-0" />
                        <Input label="Endereço da Agência" value={(al.credor || {}).endereco_agencia || ''} onChange={(v) => setAlGrp('credor', { endereco_agencia: v })} />
                      </div>
                    </div>

                    {/* Bloco B — Instrumento / Título */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-2">Instrumento / Título</p>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Select
                          label="Tipo do Instrumento"
                          value={(al.instrumento || {}).tipo || 'INSTRUMENTO_PARTICULAR_EFEITO_ESCRITURA'}
                          onChange={(v) => setAlGrp('instrumento', { tipo: v })}
                          options={[
                            { value: 'INSTRUMENTO_PARTICULAR_EFEITO_ESCRITURA', label: 'Instrumento Particular c/ efeito de escritura' },
                            { value: 'ESCRITURA_PUBLICA', label: 'Escritura Pública' },
                            { value: 'CEDULA_CREDITO_IMOBILIARIO', label: 'Cédula de Crédito Imobiliário (CCI)' },
                            { value: 'CONTRATO_GAVETA', label: 'Contrato particular não registrado (gaveta)' },
                            { value: 'OUTRO', label: 'Outro' },
                          ]}
                        />
                        {(al.instrumento || {}).tipo === 'OUTRO' && (
                          <Input label="Descrição (Outro)" value={(al.instrumento || {}).tipo_outro_descricao || ''} onChange={(v) => setAlGrp('instrumento', { tipo_outro_descricao: v })} />
                        )}
                        <Input label="Nº do Instrumento/Contrato" value={(al.instrumento || {}).numero || ''} onChange={(v) => setAlGrp('instrumento', { numero: v })} placeholder="131.105.731" />
                        <Input label="Data do Instrumento" type="date" value={(al.instrumento || {}).data || ''} onChange={(v) => setAlGrp('instrumento', { data: v })} />
                        <Input label="Base Legal" value={(al.instrumento || {}).base_legal || ''} onChange={(v) => setAlGrp('instrumento', { base_legal: v })} placeholder="art. 61 e §§ da Lei nº 4.380/1964" />
                      </div>
                    </div>

                    {/* Bloco C — Programa Habitacional */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-2">Programa Habitacional</p>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Select
                          label="Programa"
                          value={(al.programa || {}).nome || 'NENHUM'}
                          onChange={(v) => setAlGrp('programa', { nome: v, lei_referencia: (al.programa || {}).lei_referencia || PROG_LEI[v] || '' })}
                          options={[
                            { value: 'NENHUM', label: 'Nenhum' },
                            { value: 'MCMV', label: 'Minha Casa, Minha Vida' },
                            { value: 'SFH', label: 'SFH' },
                            { value: 'SFI', label: 'SFI' },
                            { value: 'PRO_COTISTA', label: 'Pró-Cotista' },
                            { value: 'OUTRO', label: 'Outro' },
                          ]}
                        />
                        <Input label="Lei de Referência" value={(al.programa || {}).lei_referencia || ''} onChange={(v) => setAlGrp('programa', { lei_referencia: v })} placeholder="Lei nº 11.977/2009..." />
                      </div>
                    </div>

                    {/* Bloco D — Registro na Matrícula */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-2">Registro na Matrícula</p>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Input label="Registro da Compra e Venda" value={(al.registro || {}).registro_compra_venda || ''} onChange={(v) => setAlGrp('registro', { registro_compra_venda: v })} placeholder="R-03/26.016" />
                        <Input label="Registro da Alienação Fiduciária" value={(al.registro || {}).registro_alienacao || ''} onChange={(v) => setAlGrp('registro', { registro_alienacao: v })} placeholder="R-04/26.016" />
                        <Input label="Data do Registro" type="date" value={(al.registro || {}).data_registro || ''} onChange={(v) => setAlGrp('registro', { data_registro: v })} />
                      </div>
                    </div>

                    {/* Bloco E — Valores da Operação Original */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-2">Valores da Operação Original</p>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Input label="Valor da Compra e Venda (R$)" type="number" value={(al.valores || {}).valor_compra || ''} onChange={(v) => setAlGrp('valores', { valor_compra: v })} placeholder="115000.00" />
                        <Input label="Entrada — Recursos Próprios (R$)" type="number" value={(al.valores || {}).entrada_recursos_proprios || ''} onChange={(v) => setAlGrp('valores', { entrada_recursos_proprios: v })} placeholder="7000.00" />
                        <Input label="Subsídio (R$)" type="number" value={(al.valores || {}).subsidio || ''} onChange={(v) => setAlGrp('valores', { subsidio: v })} placeholder="16146.00" />
                        <Input label="Origem do Subsídio" value={(al.valores || {}).subsidio_origem || ''} onChange={(v) => setAlGrp('valores', { subsidio_origem: v })} placeholder="FGTS na forma de desconto" />
                        <Input label="Valor Financiado (R$)" type="number" value={(al.valores || {}).valor_financiado || ''} onChange={(v) => setAlGrp('valores', { valor_financiado: v })} placeholder="91854.00" required />
                      </div>
                      {divergeValores && (
                        <p className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          A soma de entrada + subsídio + financiado (R$ {somaValores.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}) difere do valor da compra (R$ {valorCompra.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}). Verifique os valores na matrícula.
                        </p>
                      )}
                    </div>

                    {/* Bloco F — Condições do Financiamento */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-2">Condições do Financiamento</p>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Input label="Prazo (meses)" type="number" value={(al.condicoes || {}).prazo_meses || ''} onChange={(v) => setAlGrp('condicoes', { prazo_meses: v })} placeholder="361" />
                        <Input label="Parcela Inicial (R$)" type="number" value={(al.condicoes || {}).parcela_inicial || ''} onChange={(v) => setAlGrp('condicoes', { parcela_inicial: v })} placeholder="518.08" />
                        <Input label="Taxa de Juros Nominal (% a.a.)" type="number" value={(al.condicoes || {}).taxa_juros_nominal_aa || ''} onChange={(v) => setAlGrp('condicoes', { taxa_juros_nominal_aa: v })} placeholder="5.004" />
                        <Input label="Taxa de Juros Efetiva (% a.a.)" type="number" value={(al.condicoes || {}).taxa_juros_efetiva_aa || ''} onChange={(v) => setAlGrp('condicoes', { taxa_juros_efetiva_aa: v })} placeholder="5.116" />
                        <Input label="Início da Amortização" type="date" value={(al.condicoes || {}).amortizacao_inicio || ''} onChange={(v) => setAlGrp('condicoes', { amortizacao_inicio: v })} />
                        <Input label="Fim da Amortização" type="date" value={(al.condicoes || {}).amortizacao_fim || ''} onChange={(v) => setAlGrp('condicoes', { amortizacao_fim: v })} />
                      </div>
                    </div>

                    {/* Bloco G — Saldo Devedor Atual */}
                    <div className="rounded-lg p-3 border border-[#C9A84C] bg-[#C9A84C]/5">
                      <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-2">Saldo Devedor Atual</p>
                      <label className="flex items-start gap-2 cursor-pointer select-none text-sm text-gray-700 mb-2">
                        <input type="checkbox" className="mt-0.5 rounded"
                          checked={!!(al.saldo_devedor || {}).obter_apos_assinatura}
                          onChange={(e) => setAlGrp('saldo_devedor', { obter_apos_assinatura: e.target.checked })} />
                        <span>Saldo a ser obtido <b>após a assinatura</b> (com a procuração) — só com os documentos assinados é possível puxar o extrato no banco. O contrato registrará que o saldo será apurado após a assinatura.</span>
                      </label>
                      {!(al.saldo_devedor || {}).obter_apos_assinatura && (
                        <>
                          <div className="grid sm:grid-cols-2 gap-3">
                            <Input label="Saldo Devedor (R$)" type="number" value={(al.saldo_devedor || {}).valor || ''} onChange={(v) => setAlGrp('saldo_devedor', { valor: v })} placeholder="conforme extrato" />
                            <Input label="Data de Referência do Extrato" type="date" value={(al.saldo_devedor || {}).data_referencia || ''} onChange={(v) => setAlGrp('saldo_devedor', { data_referencia: v })} />
                          </div>
                          <p className={`mt-2 text-xs rounded px-2 py-1.5 flex items-center gap-1 ${numDocsImovel > 0 ? 'text-emerald-700 bg-emerald-50 border border-emerald-200' : 'text-amber-700 bg-amber-50 border border-amber-200'}`}>
                            {numDocsImovel > 0
                              ? <><CheckCircle2 className="w-3.5 h-3.5" /> {numDocsImovel} documento(s) anexado(s). Confirme que o extrato do financiamento está entre eles (seção Documentos do Imóvel).</>
                              : <><AlertTriangle className="w-3.5 h-3.5" /> Anexe o extrato do financiamento na seção “Documentos do Imóvel” abaixo para comprovar o saldo devedor.</>}
                          </p>
                        </>
                      )}
                    </div>

                    {/* Observações */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                      <textarea
                        value={al.observacoes || ''}
                        onChange={(e) => setAl({ observacoes: e.target.value })}
                        rows={2}
                        maxLength={2000}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Fotos do Imóvel — vão para o Anexo I do PDF */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-1">Fotos do Imóvel</p>
                <p className="text-xs text-gray-500 mb-3">Anexadas ao contrato como <b>Anexo I — Relatório Fotográfico</b>.</p>
                <ImageUploader
                  images={obj.fotos_imovel || []}
                  onImagesChange={(ids) => upd('fotos_imovel', ids)}
                  maxImages={20}
                  label="Fotos"
                  accept="image/jpeg,image/jpg,image/png,image/webp"
                />
              </div>

              {/* Documentos do Imóvel — vão para o Anexo II do PDF */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-1">Documentos do Imóvel</p>
                <p className="text-xs text-gray-500 mb-3">Matrícula, IPTU, BCI etc. — anexados como <b>Anexo II — Documentação</b> (JPG, PNG ou PDF; PDF vira páginas).</p>
                <ImageUploader
                  images={obj.documentos_imovel || []}
                  onImagesChange={(ids) => upd('documentos_imovel', ids)}
                  maxImages={20}
                  label="Documentos"
                  accept="image/jpeg,image/jpg,image/png,image/webp,application/pdf"
                />
              </div>
            </div>
          )}

          <div className="sm:col-span-2">
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">Endereço completo (como sairá no contrato)</label>
              <button type="button" onClick={buscarEnderecoDasCoords} disabled={!obj.latitude || !obj.longitude}
                className="text-xs text-emerald-700 underline disabled:text-gray-300 disabled:no-underline">
                ↻ Buscar do mapa
              </button>
            </div>
            <textarea
              value={obj.endereco_completo || ''}
              onChange={(e) => upd('endereco_completo', e.target.value)}
              placeholder={enderecoCompleto || 'Rua, nº, quadra/lote, bairro, cidade-UF, CEP'}
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="text-xs text-gray-500 mt-1">Trazido do mapa ao marcar a localização. Edite/insira/apague livremente — este texto é o endereço usado no contrato (se vazio, montamos dos campos acima).</p>
          </div>

          {(enderecoCompleto.length > 5 || (obj.latitude && obj.longitude)) && (
            <ImovelMap
              endereco={obj.endereco_completo || enderecoCompleto}
              lat={obj.latitude}
              lng={obj.longitude}
              height={260}
              onPick={marcarNoMapa}
            />
          )}
        </div>
      )}

      {/* Imóvel Rural */}
      {obj.tipo_bem === 'imovel_rural' && (
        <div className="bg-gray-50 rounded-xl p-4 grid sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <Input label="Denominação / Nome da Fazenda" value={obj.endereco} onChange={(v) => upd('endereco', v)} placeholder="Ex: Fazenda Boa Vista" required />
          </div>
          <Input label="Município" value={obj.cidade} onChange={(v) => upd('cidade', v)} />
          <Input label="UF" value={obj.uf} onChange={(v) => upd('uf', v)} placeholder="MT" />
          <Input label="CCIR" value={obj.ccir} onChange={(v) => upd('ccir', v)} placeholder="Código INCRA" />
          <Input label="CAR" value={obj.car} onChange={(v) => upd('car', v)} placeholder="Código CAR" />
          <Input label="Área Total (ha)" value={obj.area_total} onChange={(v) => upd('area_total', v)} type="number" />
          <Input label="Módulos Fiscais" value={obj.modulos_fiscais} onChange={(v) => upd('modulos_fiscais', v)} type="number" />
          <Input label="Matrícula" value={obj.matricula} onChange={(v) => upd('matricula', v)} />
          <Input label="Serventia / Cartório (Registro de Imóveis)" value={obj.registro_imovel} onChange={(v) => upd('registro_imovel', v)} placeholder="Ex: 1º Ofício de Registro de Imóveis de Açailândia/MA" />
          <Input label="CNS da Serventia" value={obj.cns} onChange={(v) => upd('cns', v)} placeholder="Código Nacional da Serventia" />
          <Input label="Latitude (grau decimal)" value={obj.latitude} onChange={(v) => upd('latitude', v)} placeholder="-4.932001" />
          <Input label="Longitude (grau decimal)" value={obj.longitude} onChange={(v) => upd('longitude', v)} placeholder="-47.515477" />
          <div className="sm:col-span-2 -mt-1">
            <p className="text-xs text-gray-500">📍 Coordenadas (SINCETI/mapa) — vão para o contrato com o mapa de localização. {obj.latitude && obj.longitude ? <a className="text-emerald-700 underline" href={`https://www.openstreetmap.org/?mlat=${obj.latitude}&mlon=${obj.longitude}#map=17/${obj.latitude}/${obj.longitude}`} target="_blank" rel="noreferrer">ver no mapa</a> : null}</p>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Ônus / Gravames</label>
            <RichTextEditor
              value={paraEditorHtml(obj.onus)}
              onChange={(html) => upd('onus', html)}
              onBlurHtml={(html) => upd('onus', html)}
              minHeight={140}
              showAiButton={false}
            />
            <div className="flex justify-end mt-1">
              <AiButton onClick={() => aperfeicoarCampo('onus', 'A partir do texto abaixo — que pode conter o HISTÓRICO REGISTRAL da matrícula (protocolos, registros R-xx, averbações AV-xx, selos, emolumentos, partes anteriores) — redija uma DECLARAÇÃO DE ÔNUS E GRAVAMES concisa e formal para um contrato de imóvel RURAL: diga objetivamente se o imóvel está livre e desembaraçado de ônus OU descreva apenas os gravames VIGENTES (ex.: alienação fiduciária/hipoteca/penhor, citando só o registro R-xx pertinente), em no máximo 2 ou 3 frases. NÃO reproduza o histórico registral completo, números de protocolo, selo ou emolumentos.')} loading={aiCampo === 'onus'} />
            </div>
          </div>
        </div>
      )}

      {/* Veículo */}
      {obj.tipo_bem === 'veiculo' && (
        <div className="bg-gray-50 rounded-xl p-4 grid sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <Input label="Descrição do Veículo" value={obj.descricao_veiculo} onChange={(v) => upd('descricao_veiculo', v)} placeholder="Ex: Honda Civic EXL 2.0 Flex" required />
          </div>
          <Input label="Placa" value={obj.placa} onChange={(v) => upd('placa', v)} placeholder="ABC-1234" />
          <Input label="RENAVAM" value={obj.renavam} onChange={(v) => upd('renavam', v)} />
          <Input label="Chassi" value={obj.chassi} onChange={(v) => upd('chassi', v)} />
          <Input label="Ano Fab./Mod." value={obj.ano_fabricacao} onChange={(v) => upd('ano_fabricacao', v)} placeholder="2022/2023" />
          <Input label="Cor" value={obj.cor} onChange={(v) => upd('cor', v)} placeholder="Prata" />
          <Input label="KM Atual" value={obj.km} onChange={(v) => upd('km', v)} type="number" />
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 6 — Pagamento
═══════════════════════════════════════════════════════════ */
const FORMA_VAZIA = { tipo: 'dinheiro', descricao: '', valor: '', data: '', parcelas: '', banco: '' };

const Step6Pagamento = ({ form, setForm, contratoId }) => {
  const pag = form.pagamento;
  const updPag = (key, val) => setForm({ ...form, pagamento: { ...pag, [key]: val } });
  const [penalidades, setPenalidades] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const { toast } = useToast();

  const addForma = () => updPag('formas', [...(pag.formas || []), { ...FORMA_VAZIA }]);
  const removeForma = (i) => updPag('formas', pag.formas.filter((_, idx) => idx !== i));
  const updateForma = (i, key, val) =>
    updPag('formas', pag.formas.map((f, idx) => idx === i ? { ...f, [key]: val } : f));

  const calcPenalidades = async () => {
    if (!contratoId || !pag.arras_valor) return;
    setCalcLoading(true);
    try {
      const res = await contratosAPI.simuladorPenalidades(contratoId, {
        valor_total: pag.valor_total,
        arras_valor: pag.arras_valor,
        arras_tipo: pag.arras_tipo,
      });
      setPenalidades(res);
    } catch {
      toast({ title: 'Erro ao calcular penalidades', variant: 'destructive' });
    } finally {
      setCalcLoading(false);
    }
  };

  useEffect(() => {
    if (pag.arras_valor && parseFloat(pag.arras_valor) > 0 && contratoId) {
      calcPenalidades();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pag.arras_valor, pag.arras_tipo, contratoId]);

  // Exclusividade de corretagem NÃO tem arras/sinal nem formas de pagamento (não há
  // comprador): as condições são comissão e prazo, definidos na etapa do Corretor.
  const isExclusividade = form.tipo_contrato === 'exclusividade';
  if (isExclusividade) {
    const cor = form.corretor || {};
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-1">Condições da Corretagem</h2>
          <p className="text-sm text-gray-500">Na exclusividade de corretagem não há arras nem sinal — as condições são a comissão e o prazo de exclusividade.</p>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
          <label className="block text-sm font-semibold text-emerald-800 mb-2">
            <DollarSign className="w-4 h-4 inline mr-1" /> Valor anunciado do imóvel
          </label>
          <input type="number" value={pag.valor_total || ''} onChange={(e) => updPag('valor_total', e.target.value)} placeholder="0,00"
                 className="w-full text-2xl font-bold border-0 border-b-2 border-emerald-300 bg-transparent px-0 py-1 focus:outline-none focus:border-emerald-600 text-emerald-900" />
          {pag.valor_total > 0 && <p className="text-sm text-emerald-700 mt-1">{fmtCurrency(pag.valor_total)}</p>}
        </div>
        <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-600 space-y-1">
          <div className="font-semibold text-gray-800 flex items-center gap-2"><Info className="w-4 h-4 text-emerald-600" /> Comissão e prazo</div>
          <p>Comissão: <b>{cor.comissao_percentual ?? '—'}%</b> · Prazo de exclusividade: <b>{cor.prazo_exclusividade || '—'}</b></p>
          <p className="text-xs text-gray-400">Defina/edite na etapa “Corretor (Contratado)”. A comissão é devida integralmente durante o prazo, ainda que a venda ocorra diretamente pelo proprietário (art. 726, parte final, CC).</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Condições de Pagamento</h2>
        <p className="text-sm text-gray-500">Defina o valor, as arras e as formas de pagamento.</p>
      </div>

      {/* Valor Total */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
        <label className="block text-sm font-semibold text-emerald-800 mb-2">
          <DollarSign className="w-4 h-4 inline mr-1" /> Valor Total do Negócio
        </label>
        <input
          type="number"
          value={pag.valor_total || ''}
          onChange={(e) => updPag('valor_total', e.target.value)}
          placeholder="0,00"
          className="w-full text-2xl font-bold border-0 border-b-2 border-emerald-300 bg-transparent px-0 py-1 focus:outline-none focus:border-emerald-600 text-emerald-900"
        />
        {pag.valor_total > 0 && (
          <p className="text-sm text-emerald-700 mt-1">
            {fmtCurrency(pag.valor_total)}
          </p>
        )}
      </div>

      {/* Arras */}
      <div className="bg-gray-50 rounded-xl p-4 space-y-3">
        <div className="font-semibold text-gray-800 text-sm flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-500" /> Arras (Sinal)
          <span className="text-xs text-gray-400 font-normal">— art. 417-420 CC</span>
        </div>
        <div className="grid sm:grid-cols-3 gap-3">
          <Input label="Valor das Arras" value={pag.arras_valor} onChange={(v) => updPag('arras_valor', v)} type="number" placeholder="0,00" />
          <Input label="Data de Pagamento" value={pag.arras_data} onChange={(v) => updPag('arras_data', v)} type="date" />
          <Select
            label="Tipo de Arras"
            value={pag.arras_tipo}
            onChange={(v) => updPag('arras_tipo', v)}
            options={[
              { value: 'confirmatorias', label: 'Confirmatórias' },
              { value: 'penitenciais', label: 'Penitenciais' },
            ]}
          />
        </div>
        {pag.arras_valor > 0 && pag.valor_total > 0 && (
          <p className="text-xs text-gray-500">
            {((pag.arras_valor / pag.valor_total) * 100).toFixed(1)}% do valor total
          </p>
        )}
        {Number(pag.arras_valor) > 0 && Number(pag.valor_total) > 0 && Number(pag.arras_valor) >= Number(pag.valor_total) && (
          <p className="text-xs text-red-600 font-medium">⚠ O sinal deve ser menor que o valor total do negócio.</p>
        )}
      </div>

      {/* Simulador de Penalidades */}
      {(pag.arras_valor > 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="font-semibold text-amber-800 text-sm mb-2 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" /> Simulador de Penalidades
            {calcLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          </div>
          {penalidades ? (
            <div className="grid sm:grid-cols-2 gap-3 text-sm">
              <div className="bg-white rounded-lg p-3 border border-amber-100">
                <div className="text-xs text-gray-500 mb-0.5">Se o vendedor desistir</div>
                <div className="font-bold text-red-700">{fmtCurrency(penalidades.vendedor_desiste)}</div>
                <div className="text-xs text-gray-400 mt-0.5">Devolve em dobro as arras</div>
              </div>
              <div className="bg-white rounded-lg p-3 border border-amber-100">
                <div className="text-xs text-gray-500 mb-0.5">Se o comprador desistir</div>
                <div className="font-bold text-red-700">{fmtCurrency(penalidades.comprador_desiste)}</div>
                <div className="text-xs text-gray-400 mt-0.5">Perde as arras pagas</div>
              </div>
            </div>
          ) : (
            !calcLoading && <p className="text-xs text-amber-700">Preencha as arras e salve para calcular.</p>
          )}
        </div>
      )}

      {/* Formas de Pagamento */}
      <div className="space-y-3">
        <div className="font-semibold text-gray-800 text-sm">Formas de Pagamento</div>

        {(pag.formas || []).map((f, i) => (
          <div key={i} className="bg-gray-50 rounded-xl p-4 relative">
            <button onClick={() => removeForma(i)} className="absolute top-3 right-3 text-red-400 hover:text-red-600">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
            <div className="grid sm:grid-cols-3 gap-3">
              <Select
                label="Modalidade"
                value={f.tipo}
                onChange={(v) => updateForma(i, 'tipo', v)}
                options={[
                  { value: 'dinheiro', label: 'Dinheiro/PIX' },
                  { value: 'financiamento', label: 'Financiamento' },
                  { value: 'parcelado', label: 'Parcelado' },
                  { value: 'cheque', label: 'Cheque' },
                  { value: 'permuta', label: 'Permuta/Troca' },
                  { value: 'fgts', label: 'FGTS' },
                  { value: 'consorcio', label: 'Consórcio' },
                  { value: 'outro', label: 'Outro' },
                ]}
              />
              <Input label="Valor" value={f.valor} onChange={(v) => updateForma(i, 'valor', v)} type="number" placeholder="0,00" />
              <Input label="Data / Vencimento" value={f.data} onChange={(v) => updateForma(i, 'data', v)} type="date" />
              {(f.tipo === 'parcelado' || f.tipo === 'financiamento') && (
                <>
                  <Input label="Parcelas" value={f.parcelas} onChange={(v) => updateForma(i, 'parcelas', v)} type="number" placeholder="Ex: 12" />
                  <Input label="Banco / Inst. Financeira" value={f.banco} onChange={(v) => updateForma(i, 'banco', v)} placeholder="Caixa, Bradesco..." />
                </>
              )}
              <div className={f.tipo === 'parcelado' || f.tipo === 'financiamento' ? '' : 'sm:col-span-3'}>
                <Input label="Descrição / Observações" value={f.descricao} onChange={(v) => updateForma(i, 'descricao', v)} placeholder="Detalhes adicionais..." />
              </div>
            </div>
          </div>
        ))}

        <Button variant="outline" onClick={addForma} className="w-full border-dashed border-emerald-300 text-emerald-700 hover:bg-emerald-50">
          <Plus className="w-4 h-4 mr-2" /> Adicionar forma de pagamento
        </Button>
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 7 — IA Cláusulas
═══════════════════════════════════════════════════════════ */
const Step7Clausulas = ({ form, setForm, contratoId }) => {
  const { toast } = useToast();
  const [iaState, setIaState] = useState('idle'); // idle | thinking | done
  const [clausulas, setClausulas] = useState(form.clausulas || []);
  const [editando, setEditando] = useState(null); // index sendo editado
  const [editBuffer, setEditBuffer] = useState({});
  const [preview, setPreview] = useState(null);
  const [enfase, setEnfase] = useState(form.clausulas_enfase || 'equilibrada');
  const [aiEdit, setAiEdit] = useState(false);
  const autoGenRef = useRef(false);

  // Tipos com texto jurídico canônico (cláusulas fixas, montadas no backend).
  const ehCanonico = (form.tipo_contrato || '').includes('exclusiv');
  const stripBold = (s) => (s || '').replace(/<\/?b>/g, '');

  useEffect(() => {
    setForm(f => ({ ...f, clausulas }));
  }, [clausulas]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!ehCanonico || !contratoId) return;
    contratosAPI.clausulasPreview(contratoId)
      .then(setPreview)
      .catch(() => setPreview({ preambulo: [], clausulas: [], fecho: '' }));
  }, [ehCanonico, contratoId]);

  const gerarClausulas = async (enfaseArg, silent = false) => {
    if (!contratoId) {
      if (!silent) toast({ title: 'Preencha as partes/imóvel — o contrato é salvo e então geramos as cláusulas', variant: 'destructive' });
      return;
    }
    const ef = enfaseArg || enfase;
    setIaState('thinking');
    try {
      const res = await contratosAPI.gerarClausulas(contratoId, { tipo: form.tipo_contrato, enfase: ef });
      const todas = [...(res.clausulas || []), ...(res.clausulas_corretagem || [])]
        .map((c, i) => ({ ...c, numero: c.numero || i + 1 }));
      setClausulas(todas);
      setForm((f) => ({ ...f, clausulas_enfase: ef }));
      setIaState('done');
      if (!silent) toast({ title: `${todas.length} cláusulas geradas pela Roma_IA (${ENFASE_LABEL[ef] || ef})` });
    } catch (err) {
      setIaState('idle');
      if (!silent) toast({ title: 'Erro ao gerar cláusulas', description: err.response?.data?.detail, variant: 'destructive' });
    }
  };

  // Auto-geração ao abrir o passo (tipos não-canônicos) quando ainda não há cláusulas.
  useEffect(() => {
    if (ehCanonico || autoGenRef.current) return;
    if (contratoId && (form.clausulas || []).length === 0) {
      autoGenRef.current = true;
      gerarClausulas(enfase, true);
    }
  }, [ehCanonico, contratoId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Aperfeiçoar UMA cláusula com IA (no editor)
  const aperfeicoarClausula = async () => {
    const atual = (editBuffer.conteudo || '').replace(/<[^>]+>/g, ' ').trim();
    setAiEdit(true);
    try {
      const prompt =
        `Aperfeiçoe juridicamente a cláusula abaixo de um contrato de ${form.tipo_contrato}, ` +
        `em português-BR formal, completa e segura, citando a base legal pertinente quando couber. ` +
        `Retorne APENAS o texto da cláusula (sem título nem rótulos).\n\n` +
        `Título: ${editBuffer.titulo || ''}\nTexto atual: ${atual || '(vazio — redija uma cláusula adequada)'}`;
      const res = await aiAPI.chat(`contrato_clausula_${Date.now()}`, prompt);
      const texto = (res?.reply || '').trim();
      if (texto) setEditBuffer((b) => ({ ...b, conteudo: texto }));
    } catch (e) {
      toast({ title: 'Erro na IA', description: e.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
    } finally {
      setAiEdit(false);
    }
  };

  const addManual = () => {
    const nova = { numero: clausulas.length + 1, titulo: 'Nova Cláusula', conteudo: '', base_legal: '', tipo: 'padrao' };
    setClausulas([...clausulas, nova]);
  };

  const remover = (i) => setClausulas(clausulas.filter((_, idx) => idx !== i));

  const iniciarEdicao = (i) => {
    setEditando(i);
    setEditBuffer({ ...clausulas[i] });
  };

  const salvarEdicao = () => {
    setClausulas(clausulas.map((c, i) => i === editando ? editBuffer : c));
    setEditando(null);
  };

  const grupos = [
    { tipo: 'padrao', label: 'Cláusulas Padrão', cor: 'blue' },
    { tipo: 'corretor', label: 'Cláusulas do Corretor', cor: 'emerald' },
    { tipo: 'especial', label: 'Cláusulas Especiais', cor: 'amber' },
  ];

  // Tipos canônicos (ex.: Exclusividade): cláusulas fixas → preview SOMENTE LEITURA.
  if (ehCanonico) {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-1">Cláusulas do Contrato</h2>
          <p className="text-sm text-gray-500">Para este tipo, as cláusulas são padronizadas e aplicadas automaticamente ao PDF.</p>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-sm text-emerald-800">
          <strong>Texto canônico aplicado.</strong> As 12 cláusulas do Contrato de Exclusividade são montadas
          automaticamente conforme o regime de prazo e os dados preenchidos. Pré-visualização abaixo (somente leitura).
        </div>
        {!preview ? (
          <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-emerald-700" /></div>
        ) : (
          <div className="space-y-4">
            {(preview.preambulo || []).map((p, i) => (
              <p key={`pre-${i}`} className="text-sm text-gray-700 leading-relaxed text-justify">{stripBold(p)}</p>
            ))}
            {(preview.clausulas || []).map((c, i) => (
              <div key={`cl-${i}`} className="bg-gray-50 rounded-xl border border-gray-200 p-4">
                <div className="font-bold text-emerald-900 text-sm mb-1.5">{c.titulo}</div>
                {(c.itens || []).map((it, j) => (
                  <p key={j} className="text-sm text-gray-700 leading-relaxed text-justify mb-1.5">{stripBold(it)}</p>
                ))}
              </div>
            ))}
            {preview.fecho && <p className="text-sm text-gray-700 italic leading-relaxed">{stripBold(preview.fecho)}</p>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Cláusulas do Contrato</h2>
        <p className="text-sm text-gray-500">As cláusulas são geradas automaticamente pela Roma_IA conforme o tipo. Todas editáveis (com IA por cláusula).</p>
      </div>

      {/* Ênfase jurídica */}
      <div className="flex items-center gap-2 flex-wrap bg-gray-50 border border-gray-200 rounded-xl px-3 py-2">
        <span className="text-xs font-semibold text-gray-600">Ênfase jurídica:</span>
        {Object.entries(ENFASE_LABEL).map(([val, lbl]) => (
          <button key={val} onClick={() => { setEnfase(val); gerarClausulas(val); }} disabled={iaState === 'thinking'}
            className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition ${enfase === val ? 'bg-emerald-800 text-white border-emerald-800' : 'bg-white text-gray-600 border-gray-300 hover:border-emerald-400'}`}>
            {lbl}
          </button>
        ))}
        <span className="text-[11px] text-gray-400">— clicar regenera as cláusulas com essa ênfase</span>
      </div>

      {/* Roma_IA card */}
      <div className="bg-gradient-to-r from-emerald-950 to-emerald-800 rounded-xl p-5 flex items-center gap-5">
        <RomaIAAvatar state={iaState === 'thinking' ? 'thinking' : iaState === 'done' ? 'speaking' : 'idle'} size="md" />
        <div className="flex-1 min-w-0">
          <div className="text-white font-semibold text-sm mb-0.5">Roma_IA — Geração de Cláusulas</div>
          <div className="text-emerald-300 text-xs">
            {iaState === 'thinking' ? 'Analisando tipo de contrato e gerando cláusulas jurídicas...' :
             iaState === 'done' ? `${clausulas.length} cláusulas (${ENFASE_LABEL[enfase]}). Revise e edite conforme necessário.` :
             'As cláusulas são geradas automaticamente ao abrir este passo.'}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Button size="sm" onClick={() => gerarClausulas()} disabled={iaState === 'thinking'}
            className="bg-amber-500 hover:bg-amber-400 text-white text-xs">
            {iaState === 'thinking' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (clausulas.length > 0 ? <RotateCcw className="w-3.5 h-3.5 mr-1" /> : <Sparkles className="w-3.5 h-3.5 mr-1" />)}
            {iaState === 'thinking' ? 'Gerando...' : (clausulas.length > 0 ? 'Regenerar' : 'Gerar Cláusulas via Roma_IA')}
          </Button>
        </div>
      </div>

      {/* Cláusulas por grupo */}
      {clausulas.length > 0 && grupos.map(g => {
        const itens = clausulas.filter(c => (c.tipo || 'padrao') === g.tipo);
        if (itens.length === 0) return null;
        const colorMap = { blue: 'bg-blue-50 border-blue-200 text-blue-800', emerald: 'bg-emerald-50 border-emerald-200 text-emerald-800', amber: 'bg-amber-50 border-amber-200 text-amber-800' };
        return (
          <div key={g.tipo}>
            <div className={`text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-lg border inline-block mb-3 ${colorMap[g.cor]}`}>{g.label}</div>
            <div className="space-y-2">
              {itens.map((c) => {
                const idx = clausulas.indexOf(c);
                return (
                  <div key={idx} className="bg-gray-50 rounded-xl border border-gray-200 p-4">
                    {editando === idx ? (
                      <div className="space-y-3">
                        <div className="grid sm:grid-cols-2 gap-3">
                          <Input label="Número" value={editBuffer.numero} onChange={(v) => setEditBuffer({ ...editBuffer, numero: v })} />
                          <Input label="Título" value={editBuffer.titulo} onChange={(v) => setEditBuffer({ ...editBuffer, titulo: v })} />
                          <Select label="Tipo" value={editBuffer.tipo || 'padrao'} onChange={(v) => setEditBuffer({ ...editBuffer, tipo: v })}
                            options={[{ value: 'padrao', label: 'Padrão' }, { value: 'corretor', label: 'Corretor' }, { value: 'especial', label: 'Especial' }]} />
                          <Input label="Base Legal" value={editBuffer.base_legal} onChange={(v) => setEditBuffer({ ...editBuffer, base_legal: v })} />
                        </div>
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <label className="block text-sm font-medium text-gray-700">Conteúdo</label>
                            <AiButton onClick={aperfeicoarClausula} loading={aiEdit} />
                          </div>
                          <RichTextEditor
                            value={paraEditorHtml(editBuffer.conteudo)}
                            onChange={(html) => setEditBuffer({ ...editBuffer, conteudo: html })}
                            onBlurHtml={(html) => setEditBuffer({ ...editBuffer, conteudo: html })}
                            minHeight={140}
                            showAiButton={false}
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={salvarEdicao} className="bg-emerald-800 text-white"><Check className="w-3.5 h-3.5 mr-1" />Salvar</Button>
                          <Button size="sm" variant="outline" onClick={() => setEditando(null)}>Cancelar</Button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-gray-900 text-sm">
                              Cláusula {c.numero} — {c.titulo}
                            </div>
                            {c.base_legal && <div className="text-xs text-gray-400 mt-0.5">{c.base_legal}</div>}
                            <p className="text-sm text-gray-600 mt-1.5 leading-relaxed line-clamp-3">{(c.conteudo || '').replace(/<[^>]+>/g, ' ')}</p>
                          </div>
                          <div className="flex gap-1 flex-shrink-0">
                            <button onClick={() => iniciarEdicao(idx)} className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-500"><Edit2 className="w-3.5 h-3.5" /></button>
                            <button onClick={() => remover(idx)} className="p-1.5 rounded-lg hover:bg-red-100 text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {clausulas.length === 0 && (
        <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-200">
          <FileText className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Nenhuma cláusula ainda. Gere via Roma_IA ou adicione manualmente.</p>
        </div>
      )}

      <Button variant="outline" onClick={addManual} className="w-full border-dashed border-emerald-300 text-emerald-700 hover:bg-emerald-50">
        <Plus className="w-4 h-4 mr-2" /> Adicionar cláusula manual
      </Button>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 8 — Validação Jurídica
═══════════════════════════════════════════════════════════ */
const Step8Validacao = ({ contratoId, onGoToStep }) => {
  const { toast } = useToast();
  const [validando, setValidando] = useState(false);
  const [alertas, setAlertas] = useState(null);
  const [ciente, setCiente] = useState(false);

  const validar = async () => {
    if (!contratoId) {
      toast({ title: 'Salve o contrato antes de validar', variant: 'destructive' });
      return;
    }
    setValidando(true);
    try {
      const res = await contratosAPI.validarJuridico(contratoId);
      setAlertas(res.alertas || []);
      if ((res.alertas || []).length === 0) {
        toast({ title: 'Nenhum problema jurídico encontrado!' });
      }
    } catch (err) {
      toast({ title: 'Erro na validação', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setValidando(false);
    }
  };

  const nivelConfig = {
    critico:  { bg: 'bg-red-50', border: 'border-red-300', icon: <AlertTriangle className="w-4 h-4 text-red-600" />, label: 'Crítico', cor: 'text-red-800' },
    atencao:  { bg: 'bg-amber-50', border: 'border-amber-300', icon: <AlertCircle className="w-4 h-4 text-amber-600" />, label: 'Atenção', cor: 'text-amber-800' },
    info:     { bg: 'bg-blue-50', border: 'border-blue-300', icon: <Info className="w-4 h-4 text-blue-600" />, label: 'Informação', cor: 'text-blue-800' },
  };

  const criticos = alertas?.filter(a => a.nivel === 'critico') || [];
  const atencoes = alertas?.filter(a => a.nivel === 'atencao') || [];
  const infos    = alertas?.filter(a => a.nivel === 'info') || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Validação Jurídica</h2>
        <p className="text-sm text-gray-500">Verifique alertas e inconsistências jurídicas antes de prosseguir.</p>
      </div>

      <Button onClick={validar} disabled={validando} className="bg-emerald-900 hover:bg-emerald-800 text-white">
        {validando ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Validando...</> : <><Shield className="w-4 h-4 mr-2" />Validar Juridicamente</>}
      </Button>

      {alertas !== null && (
        <div className="space-y-4">
          {alertas.length === 0 ? (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-600" />
              <div>
                <div className="font-semibold text-emerald-900">Nenhum problema encontrado</div>
                <div className="text-sm text-emerald-700">O contrato está juridicamente consistente.</div>
              </div>
            </div>
          ) : (
            <>
              {/* Resumo */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { count: criticos.length, label: 'Críticos', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
                  { count: atencoes.length, label: 'Atenções', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
                  { count: infos.length,    label: 'Infos',    bg: 'bg-blue-50',  text: 'text-blue-700',  border: 'border-blue-200' },
                ].map(s => (
                  <div key={s.label} className={`${s.bg} border ${s.border} rounded-xl p-3 text-center`}>
                    <div className={`text-2xl font-bold ${s.text}`}>{s.count}</div>
                    <div className={`text-xs font-medium ${s.text}`}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Lista de alertas */}
              {[...criticos, ...atencoes, ...infos].map((alerta, i) => {
                const cfg = nivelConfig[alerta.nivel] || nivelConfig.info;
                return (
                  <div key={i} className={`${cfg.bg} border ${cfg.border} rounded-xl p-4`}>
                    <div className={`flex items-start gap-2 ${cfg.cor}`}>
                      {cfg.icon}
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm">{alerta.mensagem}</div>
                        {alerta.base_legal && <div className="text-xs mt-0.5 opacity-75">{alerta.base_legal}</div>}
                      </div>
                      {alerta.step != null && (
                        <button
                          onClick={() => onGoToStep && onGoToStep(alerta.step)}
                          className="text-xs underline flex-shrink-0 opacity-75 hover:opacity-100"
                        >
                          Ir para campo
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Ciente */}
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-700">
                  <input type="checkbox" checked={ciente} onChange={(e) => setCiente(e.target.checked)} className="rounded" />
                  Estou ciente dos alertas acima e desejo prosseguir mesmo assim
                </label>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 9 — Testemunhas
═══════════════════════════════════════════════════════════ */
const EMPTY_TESTEMUNHA = { nome: '', cpf: '', rg: '', documento: '', cnh: '', profissao: '', email: '', contato: '', endereco: '', cidade: '', uf: '' };

const Step9Testemunhas = ({ form, setForm }) => {
  const testemunhas = form.testemunhas || [{ ...EMPTY_TESTEMUNHA }, { ...EMPTY_TESTEMUNHA }];
  const { toast } = useToast();
  const [salvas, setSalvas] = useState([]);
  const [salvando, setSalvando] = useState({});

  const upd = (i, key, val) => {
    const list = [...testemunhas];
    list[i] = { ...list[i], [key]: val };
    setForm({ ...form, testemunhas: list });
  };

  const setTestemunha = (i, dados) => {
    const list = [...testemunhas];
    list[i] = { ...EMPTY_TESTEMUNHA, ...dados };
    setForm({ ...form, testemunhas: list });
  };

  const carregarSalvas = useCallback(async () => {
    try { setSalvas(await testemunhasAPI.listar()); } catch { /* silent */ }
  }, []);

  useEffect(() => {
    if (!form.testemunhas) {
      setForm(f => ({ ...f, testemunhas: [{ ...EMPTY_TESTEMUNHA }, { ...EMPTY_TESTEMUNHA }] }));
    }
    carregarSalvas();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selecionarSalva = (i, id) => {
    if (!id) return;
    const t = salvas.find(s => s.id === id);
    if (t) setTestemunha(i, {
      nome: t.nome || '', cpf: t.cpf || '', rg: t.rg || '', documento: t.documento || '',
      cnh: t.cnh || '', profissao: t.profissao || '', email: t.email || '', contato: t.contato || '',
      endereco: t.endereco || '', cidade: t.cidade || '', uf: t.uf || '',
    });
  };

  const salvarTestemunha = async (i) => {
    const t = testemunhas[i] || {};
    if (!(t.nome || '').trim()) { toast({ title: 'Informe o nome da testemunha antes de salvar', variant: 'destructive' }); return; }
    setSalvando(p => ({ ...p, [i]: true }));
    try {
      await testemunhasAPI.salvar({
        nome: t.nome, cpf: t.cpf, rg: t.rg, documento: t.documento,
        cnh: t.cnh, profissao: t.profissao, email: t.email, contato: t.contato,
        endereco: t.endereco, cidade: t.cidade, uf: t.uf,
      });
      await carregarSalvas();
      toast({ title: 'Testemunha salva para reutilizar' });
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro ao salvar testemunha', variant: 'destructive' });
    } finally {
      setSalvando(p => ({ ...p, [i]: false }));
    }
  };

  // Validar CPF único
  const cpfsPartes = [
    ...(form.vendedores || []).map(v => v.cpf || v.representante_cpf),
    ...(form.compradores || []).map(c => c.cpf || c.representante_cpf),
    form.corretor?.cpf_cnpj,
  ].filter(Boolean);

  const cpfDuplicado = (cpf, idx) => {
    if (!cpf) return false;
    const outrasTest = testemunhas.filter((_, i) => i !== idx).map(t => t.cpf);
    return cpfsPartes.includes(cpf) || outrasTest.includes(cpf);
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Testemunhas</h2>
        <p className="text-sm text-gray-500">Informe 2 testemunhas. Os CPFs não podem coincidir com os das partes ou entre si.</p>
      </div>

      {[0, 1].map(i => (
        <div key={i} className="bg-gray-50 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="font-semibold text-gray-800 text-sm">Testemunha {i + 1}</div>
            <div className="flex items-center gap-2">
              {salvas.length > 0 && (
                <select
                  value=""
                  onChange={(e) => { selecionarSalva(i, e.target.value); e.target.value = ''; }}
                  className="border border-gray-300 rounded-lg px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Usar testemunha salva…</option>
                  {salvas.map(s => (
                    <option key={s.id} value={s.id}>{s.nome}{s.cpf ? ` — ${s.cpf}` : ''}</option>
                  ))}
                </select>
              )}
              <button
                type="button"
                onClick={() => salvarTestemunha(i)}
                disabled={salvando[i]}
                className="flex items-center gap-1 text-xs font-medium text-emerald-700 border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 rounded-lg px-2.5 py-1.5 transition disabled:opacity-50"
              >
                {salvando[i] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Salvar
              </button>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <Input label="Nome Completo" value={testemunhas[i]?.nome} onChange={(v) => upd(i, 'nome', v)} required />
            <div>
              <Input
                label="CPF"
                value={testemunhas[i]?.cpf}
                onChange={(v) => upd(i, 'cpf', v)}
                placeholder="000.000.000-00"
                required
              />
              {cpfDuplicado(testemunhas[i]?.cpf, i) && (
                <p className="text-xs text-red-600 mt-0.5 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" /> CPF duplicado — não pode coincidir com as partes
                </p>
              )}
            </div>
            <Input label="RG" value={testemunhas[i]?.rg} onChange={(v) => upd(i, 'rg', v)} />
            <Input label="Documento" value={testemunhas[i]?.documento} onChange={(v) => upd(i, 'documento', v)} placeholder="Ex.: Passaporte AB123456" />
            <Input label="CNH" value={testemunhas[i]?.cnh} onChange={(v) => upd(i, 'cnh', v)} placeholder="Nº de registro" />
            <Input label="Profissão" value={testemunhas[i]?.profissao} onChange={(v) => upd(i, 'profissao', v)} />
            <Input label="E-mail" value={testemunhas[i]?.email} onChange={(v) => upd(i, 'email', v)} placeholder="email@exemplo.com" />
            <Input label="Contato / Telefone" value={testemunhas[i]?.contato} onChange={(v) => upd(i, 'contato', v)} placeholder="(99) 99999-9999" />
            <div className="sm:col-span-2">
              <Input label="Endereço" value={testemunhas[i]?.endereco} onChange={(v) => upd(i, 'endereco', v)} />
            </div>
            <Input label="Cidade" value={testemunhas[i]?.cidade} onChange={(v) => upd(i, 'cidade', v)} />
            <Input label="UF" value={testemunhas[i]?.uf} onChange={(v) => upd(i, 'uf', v)} placeholder="MT" />
          </div>
        </div>
      ))}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 9 — Procuração Particular (só exclusividade)
═══════════════════════════════════════════════════════════ */
const PODERES_CATALOGO = [
  { chave: 'CERTIDOES_CRI', titulo: 'Certidões no Registro de Imóveis', descricao: 'Solicitar e retirar certidões de inteiro teor, ônus reais e ações reipersecutórias da matrícula do imóvel.' },
  { chave: 'PREFEITURA_IPTU', titulo: 'Prefeitura / IPTU', descricao: 'Solicitar carnês e demonstrativos de IPTU, certidões negativas municipais, dados cadastrais (CIM) e certidão de valor venal.' },
  { chave: 'BANCO_FINANCIAMENTO', titulo: 'Banco / Financiamento', descricao: 'Solicitar ao credor fiduciário extratos, saldo devedor, demonstrativos, boletos e informações para quitação/transferência do financiamento.' },
  { chave: 'CONCESSIONARIAS', titulo: 'Concessionárias', descricao: 'Solicitar segundas vias, declarações e certidões de débitos de energia elétrica e água/esgoto do imóvel.' },
  { chave: 'CONDOMINIO', titulo: 'Condomínio', descricao: 'Solicitar declaração de quitação de débitos condominiais.' },
  { chave: 'ANUNCIAR_DIVULGAR', titulo: 'Anunciar e divulgar', descricao: 'Fotografar, anunciar, divulgar o imóvel em quaisquer meios e acompanhar visitas de interessados.' },
  { chave: 'RECEBER_PROPOSTAS', titulo: 'Receber propostas', descricao: 'Receber e encaminhar propostas de compra, sem poderes para aceitá-las, alienar, assinar contratos ou receber valores.' },
  { chave: 'RECEITA_CERTIDOES', titulo: 'Certidões federais', descricao: 'Solicitar certidões negativas federais relativas ao imóvel e aos outorgantes, para fins de instrução da venda.' },
];
const PODERES_DEFAULT_ON = ['CERTIDOES_CRI', 'PREFEITURA_IPTU', 'CONCESSIONARIAS', 'ANUNCIAR_DIVULGAR', 'RECEBER_PROPOSTAS'];

const Step9Procuracao = ({ form, setForm, contratoId, irParaEtapa }) => {
  const { toast } = useToast();
  const proc = form.procuracao || {};
  const obj = form.objeto || {};
  const alienado = !!obj.alienacao?.alienado;
  const corretor = form.corretor || {};
  const outorgantes = form.vendedores || [];
  const [gerando, setGerando] = useState(false);
  const [editandoPoder, setEditandoPoder] = useState(null);

  const setProc = (patch) => setForm({ ...form, procuracao: { ...proc, ...patch } });

  // Inicializa poderes na 1ª vez (BANCO_FINANCIAMENTO só on se alienado)
  useEffect(() => {
    if (!form.procuracao || !Array.isArray(form.procuracao.poderes)) {
      const poderes = PODERES_CATALOGO.map(p => ({
        chave: p.chave,
        ativo: PODERES_DEFAULT_ON.includes(p.chave) || (p.chave === 'BANCO_FINANCIAMENTO' && alienado),
        texto_customizado: null,
      }));
      setForm(f => ({ ...f, procuracao: { gerar: false, vigencia_vinculada_contrato: true,
        substabelecimento_permitido: false, local_assinatura: 'Açailândia/MA', ...f.procuracao, poderes } }));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const poderes = proc.poderes || [];
  const poderAtivo = (chave) => poderes.find(p => p.chave === chave)?.ativo;
  const togglePoder = (chave) => setProc({ poderes: poderes.map(p => p.chave === chave ? { ...p, ativo: !p.ativo } : p) });
  const setPoderTexto = (chave, txt) => setProc({ poderes: poderes.map(p => p.chave === chave ? { ...p, texto_customizado: txt } : p) });

  const credorNome = obj.alienacao?.credor?.nome;

  const baixarProcuracao = async () => {
    if (!contratoId) { toast({ title: 'Salve o contrato antes de gerar a procuração', variant: 'destructive' }); return; }
    setGerando(true);
    try {
      const blob = await contratosAPI.procuracaoPdf(contratoId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `procuracao_${obj.matricula || 'imovel'}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro ao gerar procuração', variant: 'destructive' });
    } finally { setGerando(false); }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Procuração Particular</h2>
        <p className="text-sm text-gray-500">Documento separado que autoriza o corretor a obter certidões, IPTU e extrato de financiamento referentes exclusivamente ao imóvel deste contrato.</p>
      </div>

      {/* Toggle principal */}
      <div className="rounded-xl border border-gray-200 p-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">Gerar procuração particular vinculada?</p>
          <p className="text-xs text-gray-500">Opcional. Se ativada, será exportada junto com o contrato.</p>
        </div>
        <button type="button" role="switch" aria-checked={!!proc.gerar}
          onClick={() => setProc({ gerar: !proc.gerar })}
          className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition focus:outline-none focus:ring-2 focus:ring-[#C9A84C] ${proc.gerar ? 'bg-[#0C3320]' : 'bg-gray-300'}`}>
          <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${proc.gerar ? 'translate-x-5' : 'translate-x-1'}`} />
        </button>
      </div>

      {proc.gerar && (
        <div className="space-y-4">
          {/* Partes (somente leitura) */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide">Partes & Imóvel (puxados das etapas anteriores)</p>
            </div>
            <div className="text-sm space-y-2">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-700">Outorgante(s)</span>
                  <button type="button" onClick={() => irParaEtapa?.('partes')} className="text-xs text-emerald-700 hover:underline flex items-center gap-1"><Edit2 className="w-3 h-3" />Editar</button>
                </div>
                {outorgantes.length === 0 && <p className="text-xs text-red-600">Nenhum proprietário cadastrado na etapa Contratante.</p>}
                {outorgantes.map((o, i) => (
                  <p key={i} className="text-gray-600">{o.nome || o.razao_social || '—'}{o.cpf ? ` — CPF ${o.cpf}` : ''}{o.conjuge_nome ? ` · cônjuge: ${o.conjuge_nome}` : ''}</p>
                ))}
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-700">Outorgado (Corretor)</span>
                  <button type="button" onClick={() => irParaEtapa?.('corretor')} className="text-xs text-emerald-700 hover:underline flex items-center gap-1"><Edit2 className="w-3 h-3" />Editar</button>
                </div>
                <p className="text-gray-600">{corretor.nome || '—'}{corretor.creci ? ` — CRECI ${corretor.creci}` : ''}{corretor.cpf_cnpj ? ` · ${corretor.cpf_cnpj}` : ''}</p>
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-700">Imóvel (objeto exclusivo)</span>
                  <button type="button" onClick={() => irParaEtapa?.('objeto')} className="text-xs text-emerald-700 hover:underline flex items-center gap-1"><Edit2 className="w-3 h-3" />Editar</button>
                </div>
                <p className="text-gray-600">{obj.endereco || '—'}</p>
                {obj.matricula && <span className="inline-block mt-1 text-[10px] font-bold tracking-wide px-2 py-0.5 rounded bg-[#C9A84C] text-[#0C3320]">LIMITADA À MATRÍCULA {obj.matricula}</span>}
              </div>
            </div>
          </div>

          {/* Checklist de poderes */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-2">
            <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide mb-1">Poderes outorgados</p>
            {PODERES_CATALOGO.map(p => {
              const pe = poderes.find(x => x.chave === p.chave) || {};
              const isBanco = p.chave === 'BANCO_FINANCIAMENTO';
              return (
                <div key={p.chave} className="border border-gray-100 rounded-lg p-2.5">
                  <div className="flex items-start gap-2">
                    <input type="checkbox" checked={!!pe.ativo} onChange={() => togglePoder(p.chave)} className="mt-0.5 rounded" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-gray-800">{p.titulo}</span>
                        <button type="button" onClick={() => setEditandoPoder(editandoPoder === p.chave ? null : p.chave)} className="text-gray-400 hover:text-emerald-700"><Edit2 className="w-3.5 h-3.5" /></button>
                      </div>
                      <p className="text-xs text-gray-500">{pe.texto_customizado || p.descricao}{isBanco && credorNome ? ` (Credor: ${credorNome})` : ''}</p>
                      {editandoPoder === p.chave && (
                        <textarea value={pe.texto_customizado || ''} onChange={(e) => setPoderTexto(p.chave, e.target.value)} rows={2} placeholder="Texto personalizado deste poder (opcional)"
                          maxLength={600} className="mt-2 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500" />
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            <div className="pt-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Poderes adicionais (opcional)</label>
              <textarea value={proc.poderes_adicionais || ''} onChange={(e) => setProc({ poderes_adicionais: e.target.value })} rows={2} maxLength={2000}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-700 pt-1">
              <input type="checkbox" checked={!!proc.substabelecimento_permitido} onChange={(e) => setProc({ substabelecimento_permitido: e.target.checked })} className="rounded" />
              Permitir substabelecimento {!proc.substabelecimento_permitido && <span className="text-xs text-gray-400">(padrão: vedado)</span>}
            </label>
          </div>

          {/* Vigência e assinatura */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-[#C9A84C] uppercase tracking-wide">Vigência & Assinatura</p>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="radio" checked={proc.vigencia_vinculada_contrato !== false} onChange={() => setProc({ vigencia_vinculada_contrato: true })} />
              Vinculada à vigência do contrato de exclusividade
              {form.corretor?.exclusividade_data_fim && <span className="text-xs text-gray-400">(até {form.corretor.exclusividade_data_fim})</span>}
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="radio" checked={proc.vigencia_vinculada_contrato === false} onChange={() => setProc({ vigencia_vinculada_contrato: false })} />
              Data específica
            </label>
            {proc.vigencia_vinculada_contrato === false && (
              <Input label="Vigência até" type="date" value={proc.vigencia_data_fim || ''} onChange={(v) => setProc({ vigencia_data_fim: v })} />
            )}
            <div className="grid sm:grid-cols-2 gap-3">
              <Input label="Local da Assinatura" value={proc.local_assinatura || 'Açailândia/MA'} onChange={(v) => setProc({ local_assinatura: v })} />
              <Input label="Data da Assinatura" type="date" value={proc.data_assinatura || ''} onChange={(v) => setProc({ data_assinatura: v })} />
            </div>
          </div>

          <Button type="button" onClick={baixarProcuracao} disabled={gerando} className="bg-[#0C3320] hover:bg-[#0C3320]/90 text-white">
            {gerando ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Download className="w-4 h-4 mr-2" />}
            Visualizar / Baixar Procuração (PDF)
          </Button>
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 10 — Revisão Final
═══════════════════════════════════════════════════════════ */
const Step10Revisao = ({ form, contratoId }) => {
  const { toast } = useToast();
  const [checklistData, setChecklistData] = useState(null);
  const [checklistOpen, setChecklistOpen] = useState(false);
  const [checklistLoading, setChecklistLoading] = useState(false);
  const [lido, setLido] = useState(false);
  const [openSec, setOpenSec] = useState({ partes: true, objeto: false, pagamento: false, clausulas: false });

  const toggleSec = (k) => setOpenSec(s => ({ ...s, [k]: !s[k] }));

  const carregarChecklist = async () => {
    if (!contratoId || checklistData) { setChecklistOpen(o => !o); return; }
    setChecklistLoading(true);
    setChecklistOpen(true);
    try {
      const res = await contratosAPI.checklist(contratoId);
      setChecklistData(res);
    } catch {
      toast({ title: 'Erro ao carregar checklist', variant: 'destructive' });
    } finally {
      setChecklistLoading(false);
    }
  };

  const vendedores = form.vendedores || [];
  const compradores = form.compradores || [];
  const pag = form.pagamento || {};
  const obj = form.objeto || {};
  const clausulas = form.clausulas || [];

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Revisão Final</h2>
        <p className="text-sm text-gray-500">Revise todas as informações antes de exportar ou assinar.</p>
      </div>

      {/* Accordion — Partes */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button onClick={() => toggleSec('partes')} className="w-full flex items-center justify-between px-5 py-3 bg-gray-50 hover:bg-gray-100 transition text-sm font-semibold text-gray-800">
          <span className="flex items-center gap-2"><Users className="w-4 h-4" />Partes ({vendedores.length + compradores.length})</span>
          {openSec.partes ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {openSec.partes && (
          <div className="p-4 space-y-3 bg-white">
            {vendedores.map((v, i) => (
              <div key={i} className="text-sm"><span className="font-medium text-gray-600">Vendedor {i+1}:</span> {v.nome || v.razao_social || '—'} {v.cpf ? `— CPF ${v.cpf}` : ''}</div>
            ))}
            {compradores.map((c, i) => (
              <div key={i} className="text-sm"><span className="font-medium text-gray-600">Comprador {i+1}:</span> {c.nome || c.razao_social || '—'} {c.cpf ? `— CPF ${c.cpf}` : ''}</div>
            ))}
          </div>
        )}
      </div>

      {/* Accordion — Objeto */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button onClick={() => toggleSec('objeto')} className="w-full flex items-center justify-between px-5 py-3 bg-gray-50 hover:bg-gray-100 transition text-sm font-semibold text-gray-800">
          <span className="flex items-center gap-2"><MapPin className="w-4 h-4" />Objeto do Contrato</span>
          {openSec.objeto ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {openSec.objeto && (
          <div className="p-4 text-sm space-y-1 bg-white">
            <div><span className="text-gray-500">Tipo:</span> {obj.tipo_bem}</div>
            <div><span className="text-gray-500">Endereço:</span> {obj.endereco || obj.descricao_veiculo || '—'}</div>
            {obj.matricula && <div><span className="text-gray-500">Matrícula:</span> {obj.matricula}</div>}
            {obj.area_total && <div><span className="text-gray-500">Área:</span> {obj.area_total} {obj.tipo_bem === 'imovel_rural' ? 'ha' : 'm²'}</div>}

            {obj.alienacao?.alienado && (
              <div className="mt-3 rounded-lg border border-[#C9A84C] bg-[#C9A84C]/5 p-3 space-y-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold tracking-wide px-2 py-0.5 rounded bg-[#C9A84C] text-[#0C3320]">ALIENADO</span>
                  <span className="text-sm font-semibold text-gray-800">Gravame — Alienação Fiduciária</span>
                </div>
                {obj.alienacao.credor?.nome && <div><span className="text-gray-500">Credor:</span> {obj.alienacao.credor.nome}{obj.alienacao.credor.cnpj ? ` — CNPJ ${obj.alienacao.credor.cnpj}` : ''}</div>}
                {obj.alienacao.instrumento?.numero && <div><span className="text-gray-500">Instrumento:</span> nº {obj.alienacao.instrumento.numero}{obj.alienacao.instrumento.data ? ` — ${obj.alienacao.instrumento.data}` : ''}</div>}
                {obj.alienacao.programa?.nome && obj.alienacao.programa.nome !== 'NENHUM' && <div><span className="text-gray-500">Programa:</span> {obj.alienacao.programa.nome}</div>}
                {(obj.alienacao.registro?.registro_compra_venda || obj.alienacao.registro?.registro_alienacao) && (
                  <div><span className="text-gray-500">Registros:</span> {[obj.alienacao.registro.registro_compra_venda, obj.alienacao.registro.registro_alienacao].filter(Boolean).join(' · ')}</div>
                )}
                {obj.alienacao.valores?.valor_financiado && <div><span className="text-gray-500">Valor financiado:</span> R$ {obj.alienacao.valores.valor_financiado}</div>}
                {obj.alienacao.condicoes?.prazo_meses && <div><span className="text-gray-500">Prazo:</span> {obj.alienacao.condicoes.prazo_meses} meses{obj.alienacao.condicoes.parcela_inicial ? ` — parcela inicial R$ ${obj.alienacao.condicoes.parcela_inicial}` : ''}</div>}
                {obj.alienacao.saldo_devedor?.valor != null && (
                  <div className="font-semibold text-[#0C3320]">Saldo devedor: R$ {obj.alienacao.saldo_devedor.valor}{obj.alienacao.saldo_devedor.data_referencia ? ` (ref. ${obj.alienacao.saldo_devedor.data_referencia})` : ''}</div>
                )}
                <div className="text-xs text-gray-500">{(obj.documentos_imovel || []).length > 0 ? '✓ Documentos anexados ao contrato' : '⚠ Extrato não anexado'}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Procuração Particular */}
      {form.tipo_contrato === 'exclusividade' && (
        <div className="border border-gray-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1 text-sm font-semibold text-gray-800">
            <FileText className="w-4 h-4" /> Procuração Particular
          </div>
          {!form.procuracao?.gerar ? (
            <p className="text-sm text-gray-500">Não será gerada procuração.</p>
          ) : (
            <div className="text-sm text-gray-600 space-y-1">
              <div><span className="text-gray-500">Outorgante(s):</span> {(form.vendedores || []).map(v => v.nome || v.razao_social).filter(Boolean).join('; ') || '—'}</div>
              <div><span className="text-gray-500">Outorgado:</span> {form.corretor?.nome || '—'}</div>
              <div><span className="text-gray-500">Objeto:</span> Matrícula {form.objeto?.matricula || '—'}</div>
              <div><span className="text-gray-500">Poderes ativos:</span> {(form.procuracao?.poderes || []).filter(p => p.ativo).map(p => (PODERES_CATALOGO.find(c => c.chave === p.chave)?.titulo || p.chave)).join(', ') || '—'}</div>
              <div><span className="text-gray-500">Vigência:</span> {form.procuracao?.vigencia_vinculada_contrato === false ? `até ${form.procuracao?.vigencia_data_fim || '—'}` : 'vinculada ao contrato'} · Substabelecimento: {form.procuracao?.substabelecimento_permitido ? 'permitido' : 'vedado'}</div>
            </div>
          )}
        </div>
      )}

      {/* Accordion — Pagamento / Penalidades */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button onClick={() => toggleSec('pagamento')} className="w-full flex items-center justify-between px-5 py-3 bg-gray-50 hover:bg-gray-100 transition text-sm font-semibold text-gray-800">
          <span className="flex items-center gap-2"><DollarSign className="w-4 h-4" />Pagamento & Penalidades</span>
          {openSec.pagamento ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {openSec.pagamento && (
          <div className="p-4 bg-white space-y-3">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-500">Valor Total:</span> <span className="font-bold text-emerald-800">{fmtCurrency(pag.valor_total)}</span></div>
              <div><span className="text-gray-500">Arras:</span> {fmtCurrency(pag.arras_valor)} ({pag.arras_tipo})</div>
            </div>
            {pag.penalidades && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
                <div className="font-semibold text-amber-800 mb-1 flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5" />Simulador de Penalidades</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>Se vendedor desistir: <strong className="text-red-700">{fmtCurrency(pag.penalidades?.vendedor_desiste)}</strong></div>
                  <div>Se comprador desistir: <strong className="text-red-700">{fmtCurrency(pag.penalidades?.comprador_desiste)}</strong></div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Accordion — Cláusulas */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button onClick={() => toggleSec('clausulas')} className="w-full flex items-center justify-between px-5 py-3 bg-gray-50 hover:bg-gray-100 transition text-sm font-semibold text-gray-800">
          <span className="flex items-center gap-2"><FileText className="w-4 h-4" />Cláusulas ({clausulas.length})</span>
          {openSec.clausulas ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {openSec.clausulas && (
          <div className="p-4 bg-white space-y-2">
            {clausulas.map((c, i) => (
              <div key={i} className="text-sm border-b border-gray-100 pb-2 last:border-0">
                <span className="font-medium">Cláusula {c.numero}:</span> {c.titulo}
              </div>
            ))}
            {clausulas.length === 0 && <p className="text-sm text-gray-400">Nenhuma cláusula definida.</p>}
          </div>
        )}
      </div>

      {/* Checklist Documental */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button onClick={carregarChecklist} className="w-full flex items-center justify-between px-5 py-3 bg-gray-50 hover:bg-gray-100 transition text-sm font-semibold text-gray-800">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />Checklist Documental
            {checklistLoading && <Loader2 className="w-3.5 h-3.5 animate-spin ml-1" />}
          </span>
          {checklistOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {checklistOpen && checklistData && (
          <div className="p-4 bg-white space-y-2">
            {(checklistData.itens || []).map((item, i) => (
              <div key={i} className={`flex items-center gap-2 text-sm ${item.ok ? 'text-emerald-700' : 'text-gray-600'}`}>
                {item.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertCircle className="w-4 h-4 text-amber-500" />}
                {item.descricao}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Confirmação */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
        <label className="flex items-center gap-2 cursor-pointer select-none text-sm font-medium text-emerald-800">
          <input type="checkbox" checked={lido} onChange={(e) => setLido(e.target.checked)} className="rounded" />
          Li e revisei todas as informações deste contrato
        </label>
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 11 — Exportar e Assinar
═══════════════════════════════════════════════════════════ */
// Miniaturas dos templates via CSS (sem precisar de assets de imagem)
const TEMPLATES_PDF = [
  { id: 'prime1', nome: 'Prime I', desc: 'Editorial — preto & verde',
    preview: 'linear-gradient(115deg,#0E0E0E 0 54%,#0C3320 54% 100%)' },
  { id: 'prime2', nome: 'Prime II', desc: 'Institucional — verde & dourado',
    preview: 'linear-gradient(#0C3320 0 72%,#C9A84C 72% 100%)' },
  { id: 'tradicional', nome: 'Tradicional', desc: 'Clássico — cartório/impressão',
    preview: 'repeating-linear-gradient(#fff,#fff 5px,#e7e5e0 5px,#e7e5e0 6px)' },
];

const Step11Exportar = ({ form, setForm, contratoId, user }) => {
  const { toast } = useToast();
  const [loadingDocx, setLoadingDocx] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [loadingArras, setLoadingArras] = useState(false);
  const [loadingProc, setLoadingProc] = useState(false);
  const [loadingLacrar, setLoadingLacrar] = useState(false);
  const [lacrado, setLacrado] = useState(form.lacrado || false);
  const [loadingD4sign, setLoadingD4sign] = useState(false);
  const [linkPublico, setLinkPublico] = useState(form.link_publico || null);
  const [linkCopiado, setLinkCopiado] = useState(false);

  const config = form.config || { incluir_logo: true, incluir_recibo_arras: true, incluir_checklist: true };
  const updConfig = (key, val) => setForm({ ...form, config: { ...config, [key]: val } });

  const hasLogo = !!user?.company_logo;
  const logoUrl = hasLogo ? `/api/upload/image/${user.company_logo}` : null;

  const downloadBlob = (data, filename) => {
    const blob = data instanceof Blob ? data : new Blob([data]);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Adia a revogação para garantir que o browser terminou o download
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  };

  const baixarDocx = async () => {
    if (!contratoId) return;
    setLoadingDocx(true);
    try {
      const blob = await contratosAPI.docx(contratoId);
      downloadBlob(blob, `contrato_${form.numero || contratoId}.docx`);
    } catch {
      toast({ title: 'Erro ao gerar DOCX', variant: 'destructive' });
    } finally {
      setLoadingDocx(false);
    }
  };

  const baixarPdf = async () => {
    if (!contratoId) return;
    setLoadingPdf(true);
    try {
      const blob = await contratosAPI.pdf(contratoId, form.template_pdf || 'prime2');
      downloadBlob(blob, `contrato_${form.numero || contratoId}.pdf`);
    } catch {
      toast({ title: 'Erro ao gerar PDF', variant: 'destructive' });
    } finally {
      setLoadingPdf(false);
    }
  };

  const baixarArras = async () => {
    if (!contratoId) return;
    setLoadingArras(true);
    try {
      const blob = await contratosAPI.reciboArras(contratoId);
      downloadBlob(blob, `recibo_arras_${form.numero || contratoId}.docx`);
    } catch {
      toast({ title: 'Erro ao gerar Recibo de Arras', variant: 'destructive' });
    } finally {
      setLoadingArras(false);
    }
  };

  const baixarProcuracao = async () => {
    if (!contratoId) return;
    setLoadingProc(true);
    try {
      const blob = await contratosAPI.procuracaoPdf(contratoId);
      downloadBlob(blob, `procuracao_${form.objeto?.matricula || form.numero || contratoId}.pdf`);
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro ao gerar Procuração', variant: 'destructive' });
    } finally {
      setLoadingProc(false);
    }
  };

  const lacrarContrato = async () => {
    if (!contratoId) return;
    if (!window.confirm('Ao lacrar esta versão, ela será marcada como definitiva. Deseja continuar?')) return;
    setLoadingLacrar(true);
    try {
      await contratosAPI.lacrar(contratoId, {});
      setLacrado(true);
      toast({ title: 'Contrato lacrado com sucesso!' });
    } catch (err) {
      toast({ title: 'Erro ao lacrar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setLoadingLacrar(false);
    }
  };

  const enviarD4sign = async () => {
    if (!contratoId) return;
    setLoadingD4sign(true);
    try {
      const signatarios = [
        ...(form.vendedores || []).map(v => ({ nome: v.nome || v.razao_social, email: v.email })),
        ...(form.compradores || []).map(c => ({ nome: c.nome || c.razao_social, email: c.email })),
        ...(form.corretor?.incluir && form.corretor.email ? [{ nome: form.corretor.nome, email: form.corretor.email }] : []),
      ].filter(s => s.email);
      await contratosAPI.assinarD4sign(contratoId, { signatarios });
      toast({ title: 'Contrato enviado para assinatura D4Sign!' });
    } catch (err) {
      toast({ title: 'Erro ao enviar D4Sign', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setLoadingD4sign(false);
    }
  };

  const gerarLinkPublico = async () => {
    if (!contratoId) return;
    try {
      const res = await contratosAPI.compartilhar(contratoId);
      const url = `${window.location.origin}/contrato/public/${res.token}`;
      setLinkPublico(url);
    } catch {
      toast({ title: 'Erro ao gerar link', variant: 'destructive' });
    }
  };

  const copiarLink = () => {
    if (!linkPublico) return;
    navigator.clipboard.writeText(linkPublico);
    setLinkCopiado(true);
    setTimeout(() => setLinkCopiado(false), 2000);
  };

  const whatsApp = () => {
    if (!linkPublico) return;
    window.open(`https://wa.me/?text=${encodeURIComponent(`Segue o contrato: ${linkPublico}`)}`, '_blank');
  };

  const signatarios = [
    ...(form.vendedores || []).map(v => ({ nome: v.nome || v.razao_social, papel: 'Vendedor', email: v.email })),
    ...(form.compradores || []).map(c => ({ nome: c.nome || c.razao_social, papel: 'Comprador', email: c.email })),
    ...(form.corretor?.incluir ? [{ nome: form.corretor.nome, papel: 'Corretor', email: form.corretor.email }] : []),
    ...((form.testemunhas || []).map((t, i) => ({ nome: t.nome, papel: `Testemunha ${i + 1}`, email: '' }))),
  ].filter(s => s.nome);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Exportar e Assinar</h2>
        <p className="text-sm text-gray-500">Baixe o documento, lacrare a versão definitiva e envie para assinatura.</p>
      </div>

      {/* Configurações do Documento */}
      <div className="bg-gray-50 rounded-xl p-5 space-y-4">
        <div className="font-semibold text-gray-800 text-sm mb-1">Configurações do Documento</div>
        
        {/* Logo do Escritório */}
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={config.incluir_logo}
              onChange={(e) => updConfig('incluir_logo', e.target.checked)}
              className="rounded"
            />
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-700">
                Incluir logo no documento
              </div>
              <div className="text-xs text-gray-500">
                {hasLogo 
                  ? 'Será usado o logo do seu escritório cadastrado'
                  : 'Será usado o logo padrão do sistema Romatec'
                }
              </div>
            </div>
          </label>
          
          {config.incluir_logo && (
            <div className="ml-6 p-3 bg-white rounded-lg border border-gray-200 inline-block">
              <img 
                src={hasLogo ? logoUrl : '/brand/logo_principal.png'} 
                alt="Logo" 
                className="h-16 object-contain"
                onError={(e) => { e.target.src = '/brand/logo_principal.png'; }}
              />
            </div>
          )}
          
          {!hasLogo && (
            <div className="ml-6 text-xs text-gray-400">
              <a href="/dashboard/config" className="text-emerald-600 hover:underline">Cadastrar meu logo</a> (opcional)
            </div>
          )}
        </div>

        <hr className="border-gray-200" />

        {/* Recibo de Arras */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={config.incluir_recibo_arras}
            onChange={(e) => updConfig('incluir_recibo_arras', e.target.checked)}
            className="rounded"
          />
          <div>
            <div className="text-sm font-medium text-gray-700">Incluir recibo de arras separado</div>
            <div className="text-xs text-gray-500">Gera um documento adicional com o recibo das arras/sinal</div>
          </div>
        </label>

        <hr className="border-gray-200" />

        {/* Checklist */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={config.incluir_checklist}
            onChange={(e) => updConfig('incluir_checklist', e.target.checked)}
            className="rounded"
          />
          <div>
            <div className="text-sm font-medium text-gray-700">Incluir checklist documental</div>
            <div className="text-xs text-gray-500">Adiciona lista de documentos necessários ao final do contrato</div>
          </div>
        </label>
      </div>

      {/* Modelo do PDF (Prime I / Prime II / Tradicional) */}
      <div className="bg-gray-50 rounded-xl p-5 space-y-3">
        <div className="font-semibold text-gray-800 text-sm mb-1">Modelo do PDF</div>
        <div className="grid grid-cols-3 gap-3">
          {TEMPLATES_PDF.map((t) => {
            const sel = (form.template_pdf || 'prime2') === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setForm({ ...form, template_pdf: t.id })}
                className={`text-left rounded-xl border-2 p-3 transition bg-white ${sel ? 'border-[#0C3320] shadow' : 'border-gray-200 hover:border-gray-300'}`}
              >
                <div className="h-20 rounded-md mb-2 border border-gray-200" style={{ background: t.preview }} />
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-800">{t.nome}</span>
                  {sel && <Check className="w-4 h-4 text-emerald-800" />}
                </div>
                <div className="text-[11px] text-gray-500 leading-tight">{t.desc}</div>
              </button>
            );
          })}
        </div>
        <p className="text-[11px] text-gray-400">O modelo escolhido é salvo no contrato e usado ao gerar o PDF.</p>
      </div>

      {/* Downloads */}
      <div className="bg-gray-50 rounded-xl p-5 space-y-3">
        <div className="font-semibold text-gray-800 text-sm mb-1">Exportar Documento</div>
        <div className="flex flex-wrap gap-3">
          <Button onClick={baixarDocx} disabled={loadingDocx || !contratoId} variant="outline" className="border-blue-300 text-blue-700 hover:bg-blue-50">
            {loadingDocx ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
            Baixar DOCX
          </Button>
          <Button onClick={baixarPdf} disabled={loadingPdf || !contratoId} variant="outline" className="border-red-300 text-red-700 hover:bg-red-50">
            {loadingPdf ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
            Baixar PDF
          </Button>
          {form.pagamento?.arras_valor > 0 && (
            <Button onClick={baixarArras} disabled={loadingArras || !contratoId} variant="outline" className="border-amber-300 text-amber-700 hover:bg-amber-50">
              {loadingArras ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
              Baixar Recibo de Arras
            </Button>
          )}
          {form.tipo_contrato === 'exclusividade' && form.procuracao?.gerar && (
            <Button onClick={baixarProcuracao} disabled={loadingProc || !contratoId} variant="outline" className="border-[#0C3320] text-[#0C3320] hover:bg-emerald-50">
              {loadingProc ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
              Baixar Procuração
            </Button>
          )}
        </div>
      </div>

      {/* Lacrar */}
      <div className={`rounded-xl p-5 border ${lacrado ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`}>
        <div className="flex items-center gap-3 mb-3">
          <Lock className={`w-5 h-5 ${lacrado ? 'text-emerald-700' : 'text-amber-700'}`} />
          <div>
            <div className={`font-semibold text-sm ${lacrado ? 'text-emerald-800' : 'text-amber-800'}`}>
              {lacrado ? 'Versão Lacrada' : 'Lacrar esta Versão'}
            </div>
            <div className={`text-xs ${lacrado ? 'text-emerald-600' : 'text-amber-600'}`}>
              {lacrado ? 'Este contrato está lacrado. Nenhuma alteração adicional será registrada nesta versão.' : 'Congela a versão atual com hash SHA-256 para garantia de autenticidade.'}
            </div>
          </div>
        </div>
        {!lacrado && (
          <Button onClick={lacrarContrato} disabled={loadingLacrar || !contratoId} className="bg-amber-600 hover:bg-amber-700 text-white">
            {loadingLacrar ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Lock className="w-4 h-4 mr-2" />}
            Lacrar esta versão
          </Button>
        )}
        {lacrado && (
          <div className="flex items-center gap-2 text-emerald-700 text-sm font-medium">
            <CheckCircle2 className="w-4 h-4" /> Versão lacrada com sucesso
          </div>
        )}
      </div>

      {/* D4Sign */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-4">
        <div className="font-semibold text-blue-900 text-sm flex items-center gap-2">
          <Send className="w-4 h-4" /> Assinatura Digital — D4Sign
        </div>

        {signatarios.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-blue-700 font-medium">Signatários identificados:</div>
            {signatarios.map((s, i) => (
              <div key={i} className="flex items-center gap-3 bg-white rounded-lg px-3 py-2 border border-blue-100 text-sm">
                <User className="w-3.5 h-3.5 text-blue-400" />
                <span className="font-medium text-gray-800">{s.nome}</span>
                <span className="text-gray-400 text-xs">({s.papel})</span>
                {s.email && <span className="text-gray-500 text-xs ml-auto">{s.email}</span>}
              </div>
            ))}
          </div>
        )}

        <Button onClick={enviarD4sign} disabled={loadingD4sign || !contratoId} className="bg-blue-700 hover:bg-blue-800 text-white">
          {loadingD4sign ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
          Enviar para Assinatura
        </Button>
      </div>

      {/* Link Público */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 space-y-3">
        <div className="font-semibold text-gray-800 text-sm flex items-center gap-2">
          <Link className="w-4 h-4" /> Compartilhar Contrato
        </div>

        {!linkPublico ? (
          <Button onClick={gerarLinkPublico} disabled={!contratoId} variant="outline" className="border-emerald-300 text-emerald-700 hover:bg-emerald-50">
            <Link className="w-4 h-4 mr-2" /> Gerar link público
          </Button>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input type="text" readOnly value={linkPublico}
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono text-gray-600 bg-white" />
              <Button size="sm" variant="outline" onClick={copiarLink}>
                {linkCopiado ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={whatsApp} className="bg-green-600 hover:bg-green-700 text-white">
                <MessageCircle className="w-3.5 h-3.5 mr-1.5" /> WhatsApp
              </Button>
              <Button size="sm" variant="outline" onClick={() => window.open(`mailto:?subject=Contrato&body=${encodeURIComponent(linkPublico)}`)}>
                <Mail className="w-3.5 h-3.5 mr-1.5" /> E-mail
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP genérico de PARTE (dirigido pelo registry — papel.dataKey)
═══════════════════════════════════════════════════════════ */
const StepParte = ({ form, setForm, papel }) => {
  const lista = form[papel.dataKey] || [];
  const setLista = (nova) => setForm({ ...form, [papel.dataKey]: nova });
  const add = () => setLista([...lista, { ...EMPTY_PESSOA }]);
  const remove = (i) => setLista(lista.filter((_, idx) => idx !== i));
  const upd = (i, p) => setLista(lista.map((v, idx) => (idx === i ? p : v)));

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">
          {papel.label}
          {papel.opcional && <span className="text-xs text-gray-400 font-normal ml-2">(opcional)</span>}
        </h2>
        <p className="text-sm text-gray-500">{papel.descricao}</p>
      </div>

      {lista.length === 0 && (
        <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-200">
          <Users className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Nenhum {papel.labelSingular.toLowerCase()} adicionado ainda.</p>
        </div>
      )}

      {lista.map((v, i) => (
        <div key={i} className="relative">
          <PessoaForm pessoa={v} onChange={(pp) => upd(i, pp)} titulo={`${papel.labelSingular} ${i + 1}`} />
          {lista.length > 1 && (
            <button onClick={() => remove(i)} className="absolute top-3 right-3 text-red-500 hover:text-red-700 transition" title="Remover">
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      ))}

      <Button variant="outline" onClick={add} className="w-full border-dashed border-emerald-300 text-emerald-700 hover:bg-emerald-50">
        <Plus className="w-4 h-4 mr-2" /> Adicionar outro {papel.labelSingular.toLowerCase()}
      </Button>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   MAIN WIZARD
═══════════════════════════════════════════════════════════ */
const ContratoWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const { user } = useAuth();

  const isNew = !id || id === 'novo';
  const tipoPreset = location.state?.tipoPreset || '';
  const [form, setForm] = useState({
    ...EMPTY, tipo_contrato: tipoPreset,
    vendedores: [{ ...EMPTY_PESSOA }], compradores: [{ ...EMPTY_PESSOA }],
    // atalho "Novo exclusivo": já abre com a procuração habilitada
    ...(tipoPreset === 'exclusividade' ? { procuracao: { gerar: true } } : {}),
  });
  const [contratoId, setContratoId] = useState(isNew ? null : id);
  const [step, setStep] = useState(location.state?.startStep || 0);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [perfil, setPerfil] = useState(null);
  const debounceRef = useRef(null);
  const creatingRef = useRef(false);      // trava criação concorrente (corrige duplicatas)
  const skipAutosaveRef = useRef(false);  // pula o autosave disparado pelo próprio load()
  // BUG 5-B — persistência ponta a ponta: garante que o último valor digitado
  // (ex.: cidade/data/foro) não seja engolido pelo debounce ao trocar de etapa
  // ou desmontar o wizard. formRef/contratoIdRef expõem o estado mais recente
  // ao flush; dirtyRef evita salvar (e versionar) sem alteração real.
  const formRef = useRef(form);
  const contratoIdRef = useRef(contratoId);
  const dirtyRef = useRef(false);

  const tipoAnteriorRef = useRef(form.tipo_contrato);

  // Registry: ÚNICA fonte de etapas/labels/título para o tipo selecionado.
  const config = getWizardConfig(form.tipo_contrato);
  const etapas = config.etapas;

  /* Load existing */
  const load = useCallback(async () => {
    if (!contratoId) return;
    setLoading(true);
    try {
      const data = await contratosAPI.buscar(contratoId);
      skipAutosaveRef.current = true;  // não autosalvar por causa do preenchimento do load
      // Merge PROFUNDO dos objetos aninhados: faz backfill dos defaults (ex.:
      // objeto.tipo_bem) quando o documento salvo vier parcial. Sem isso, o spread
      // raso ({...EMPTY, ...data}) substitui objeto/corretor/pagamento/config INTEIROS
      // pelo que veio do banco — e, se faltar tipo_bem, o bloco condicional da etapa
      // Imóvel não renderiza (os campos somem da tela, deixando só o dropdown).
      const objSalvo = data.objeto || {};
      setForm({
        ...EMPTY,
        vendedores: [{ ...EMPTY_PESSOA }],
        compradores: [{ ...EMPTY_PESSOA }],
        ...data,
        objeto: {
          ...EMPTY.objeto,
          ...objSalvo,
          tipo_bem: objSalvo.tipo_bem || objSalvo.tipo || 'imovel_urbano',
        },
        corretor: { ...EMPTY.corretor, ...(data.corretor || {}) },
        pagamento: { ...EMPTY.pagamento, ...(data.pagamento || {}) },
        config: { ...EMPTY.config, ...(data.config || {}) },
      });
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(err);
      }
      toast({ title: 'Erro ao carregar contrato', variant: 'destructive' });
      nav('/dashboard/contratos');
    } finally {
      setLoading(false);
    }
  }, [contratoId, nav, toast]);

  useEffect(() => { load(); }, [load]);

  /* Load perfil for corretor step */
  useEffect(() => {
    perfilAPI.get().then(setPerfil).catch(() => {});
  }, []);

  /* Save */
  const save = useCallback(async (silent = false) => {
    // Validação: tipo_contrato é obrigatório
    if (!form.tipo_contrato) {
      if (!silent) toast({ title: 'Selecione o tipo de contrato', description: 'Escolha uma modalidade na Etapa 1 antes de salvar.', variant: 'destructive' });
      return;
    }
    // Evita criação concorrente: se já há um POST de criação em andamento e
    // ainda não temos id, não dispara outro (corrige a geração de 3 rascunhos).
    if (!contratoId && creatingRef.current) return;
    setSaving(true);
    try {
      if (contratoId) {
        await contratosAPI.atualizar(contratoId, form);
      } else {
        creatingRef.current = true;
        const created = await contratosAPI.criar(form);
        setContratoId(created.id);
        // Só redireciona se for autosave (silent=true), não quando clica no botão Salvar
        if (silent) {
          nav(`/dashboard/contratos/${created.id}`, { replace: true });
        }
      }
      setLastSaved(new Date());        // "Salvo ✓" só após o 200 real do save
      dirtyRef.current = false;        // alteração persistida com sucesso
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      // Libera nova tentativa apenas se a CRIAÇÃO falhou (mantém a trava se já criou)
      if (!contratoId) creatingRef.current = false;
      if (process.env.NODE_ENV === 'development') {
        console.warn('Erro ao salvar contrato:', err);
      }
      const detail = err.response?.data?.detail || err.message || 'Erro desconhecido';
      if (!silent) toast({ title: 'Erro ao salvar', description: detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [form, contratoId, nav, toast]);

  /* Mantém o estado mais recente acessível ao flush (unmount / troca de etapa) */
  useEffect(() => { formRef.current = form; }, [form]);
  useEffect(() => { contratoIdRef.current = contratoId; }, [contratoId]);

  /* Flush síncrono: persiste já o estado atual sem esperar o debounce.
     Usado ao trocar de etapa e ao desmontar — corrige o BUG 5-B (último valor
     digitado, ex.: cidade/data/foro, era engolido pelo clearTimeout). */
  const flushSave = useCallback(() => {
    if (!dirtyRef.current) return;            // nada novo → não versiona à toa
    const cid = contratoIdRef.current;
    if (!cid) return;                          // criação fica a cargo do autosave
    clearTimeout(debounceRef.current);
    dirtyRef.current = false;
    // fire-and-forget: o save é idempotente ($set), o componente pode desmontar
    contratosAPI.atualizar(cid, formRef.current).catch(() => { dirtyRef.current = true; });
  }, []);

  /* Autosave */
  useEffect(() => {
    // Pula o autosave provocado pelo preenchimento do load() (evita update/versão à toa)
    if (skipAutosaveRef.current) { skipAutosaveRef.current = false; return; }
    // Contrato NOVO sem id: só cria quando houver PREENCHIMENTO real (evita rascunho vazio
    // a cada vez que se abre/seleciona um tipo). Só o tipo selecionado NÃO cria.
    if (isNew && !contratoId && !temConteudo(form)) return;
    dirtyRef.current = true;                   // há alteração pendente
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 1500);
    return () => clearTimeout(debounceRef.current);
  }, [form]); // eslint-disable-line react-hooks/exhaustive-deps

  /* Flush no unmount: se sair do wizard com alteração pendente, grava antes. */
  useEffect(() => () => { flushSave(); }, [flushSave]);

  /* Flush ao fechar/atualizar a aba (sendBeacon-like via fetch keepalive). */
  useEffect(() => {
    const handler = () => { flushSave(); };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [flushSave]);

  // Mantém o passo no range quando o tipo muda (N de etapas varia por tipo).
  useEffect(() => {
    if (step > etapas.length - 1) setStep(etapas.length - 1);
  }, [etapas.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Troca de tipo: preserva partes compatíveis; descarta as incompatíveis com aviso.
  useEffect(() => {
    const novo = form.tipo_contrato;
    if (!novo || novo === tipoAnteriorRef.current) return;
    tipoAnteriorRef.current = novo;
    const umaParte = ['exclusividade', 'intermediacao'].includes(novo);
    const temFiador = ['locacao_residencial', 'locacao_comercial'].includes(novo);
    const limparComp = umaParte && (form.compradores?.length || 0) > 0;
    const limparFiador = !temFiador && (form.fiadores?.length || 0) > 0;
    if (limparComp || limparFiador) {
      setForm((f) => ({
        ...f,
        ...(limparComp ? { compradores: [] } : {}),
        ...(limparFiador ? { fiadores: [] } : {}),
      }));
      toast({ title: 'Etapas ajustadas ao tipo', description: 'Dados de etapas que este tipo não possui foram descartados.' });
    }
  }, [form.tipo_contrato]); // eslint-disable-line react-hooks/exhaustive-deps

  // Flush ao trocar de etapa: persiste o que foi digitado nesta etapa ANTES de
  // sair dela (BUG 5-B — sem isso o debounce podia ser cancelado e perder o valor).
  const validarEtapaAtual = () => {
    const etapa = etapas[Math.min(step, etapas.length - 1)];
    if (etapa?.kind === 'objeto') {
      const a = form.objeto?.alienacao;
      if (a?.alienado) {
        const cnpjDig = (a.credor?.cnpj || '').replace(/\D/g, '');
        const faltas = [];
        if (!(a.credor?.nome || '').trim()) faltas.push('Banco/Credor');
        if (cnpjDig.length !== 14) faltas.push('CNPJ válido (14 dígitos)');
        if (!(a.valores?.valor_financiado)) faltas.push('Valor Financiado');
        if (!a.saldo_devedor?.obter_apos_assinatura) {
          if (!(a.saldo_devedor?.valor)) faltas.push('Saldo Devedor (ou marque “obter após assinatura”)');
          if (!(a.saldo_devedor?.data_referencia)) faltas.push('Data de Referência do Extrato');
        }
        if (faltas.length) {
          toast({ title: 'Complete os dados da alienação', description: faltas.join(', '), variant: 'destructive' });
          return false;
        }
      }
    }
    if (etapa?.kind === 'procuracao') {
      const proc = form.procuracao;
      if (proc?.gerar) {
        const temPoder = (proc.poderes || []).some(p => p.ativo) || (proc.poderes_adicionais || '').trim();
        if (!temPoder) {
          toast({ title: 'Selecione ao menos um poder para a procuração', variant: 'destructive' });
          return false;
        }
        const outOk = (form.vendedores || []).length > 0 && (form.vendedores || []).every(v => (v.nome || v.razao_social) && (v.cpf || v.cnpj));
        if (!outOk) {
          toast({ title: 'Outorgantes incompletos', description: 'Cada proprietário precisa de nome e CPF/CNPJ (etapa Contratante).', variant: 'destructive' });
          return false;
        }
        const cor = form.corretor || {};
        if (!cor.nome || !(cor.creci || cor.cpf_cnpj)) {
          toast({ title: 'Outorgado incompleto', description: 'O corretor precisa de nome e CRECI ou CPF/CNPJ (etapa Corretor).', variant: 'destructive' });
          return false;
        }
      }
    }
    return true;
  };

  const goNext = () => { if (!validarEtapaAtual()) return; flushSave(); if (step < etapas.length - 1) setStep(s => s + 1); };
  const goPrev = () => { flushSave(); if (step > 0) setStep(s => s - 1); };

  // Marca/desmarca a etapa como concluída, carimba data/hora e salva na hora (auditoria).
  const toggleEtapaConcluida = (stepIndex, checked) => {
    setForm((prev) => ({
      ...prev,
      etapas_concluidas: { ...(prev.etapas_concluidas || {}), [stepIndex]: checked },
      etapas_concluidas_em: {
        ...(prev.etapas_concluidas_em || {}),
        [stepIndex]: checked ? new Date().toISOString() : null,
      },
    }));
    setTimeout(() => save(false), 60);
  };

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <Loader2 className="w-6 h-6 animate-spin text-emerald-800" />
    </div>
  );

  const renderStep = () => {
    const etapa = etapas[Math.min(step, etapas.length - 1)];
    if (!etapa) return null;
    switch (etapa.kind) {
      case 'tipo': return <Step1Tipo form={form} setForm={setForm} />;
      case 'partes': return <StepParte form={form} setForm={setForm} papel={etapa.papel} />;
      case 'corretor': return <Step4Corretor form={form} setForm={setForm} perfil={perfil} corretorLabel={etapa.label} />;
      case 'objeto': return <Step5Objeto form={form} setForm={setForm} />;
      case 'condicoes': return <Step6Pagamento form={form} setForm={setForm} contratoId={contratoId} />;
      case 'clausulas': return <Step7Clausulas form={form} setForm={setForm} contratoId={contratoId} />;
      case 'validacao': return <Step8Validacao contratoId={contratoId} onGoToStep={setStep} />;
      case 'testemunhas': return <Step9Testemunhas form={form} setForm={setForm} />;
      case 'procuracao': return <Step9Procuracao form={form} setForm={setForm} contratoId={contratoId}
        irParaEtapa={(kind) => { const idx = etapas.findIndex(e => e.kind === kind); if (idx >= 0) setStep(idx); }} />;
      case 'revisao': return <Step10Revisao form={form} contratoId={contratoId} />;
      case 'exportar': return <Step11Exportar form={form} setForm={setForm} contratoId={contratoId} user={user} />;
      default: return null;
    }
  };

  // Fonte ÚNICA de labels: barra, chips e conteúdo derivam do registry.
  const stepIdx = Math.min(step, etapas.length - 1);
  const dynamicStepLabels = etapas.map(etapaLabel);
  const progressPct = Math.round(((stepIdx + 1) / etapas.length) * 100);

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => nav('/dashboard/contratos')}
          className="w-9 h-9 rounded-xl border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition"
        >
          <ArrowLeft className="w-4 h-4 text-gray-600" />
        </button>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FileSignature className="w-5 h-5 text-emerald-800" />
          <h1 className="text-lg font-bold text-gray-900 truncate">
            {form.tipo_contrato ? config.tituloHeader : 'Novo Contrato'}
            {form.numero ? <span className="text-gray-400 font-normal"> · {form.numero}</span> : ''}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {lastSaved && (
            <span className="text-xs text-gray-400 hidden sm:block">
              Salvo {lastSaved.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          <Button
            size="sm"
            onClick={() => save(false)}
            disabled={saving}
            className="bg-emerald-900 hover:bg-emerald-800 text-white"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            <span className="ml-1.5 hidden sm:inline">Salvar</span>
          </Button>
        </div>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-500 font-medium">
            Etapa {stepIdx + 1} de {etapas.length} — {dynamicStepLabels[stepIdx]}
          </span>
          <span className="text-xs text-gray-400">{progressPct}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-700 rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Step tabs (desktop) — mesma fonte da barra (corrige off-by-one) */}
      <div className="hidden lg:flex gap-1 flex-wrap">
        {dynamicStepLabels.map((label, i) => (
          <button
            key={i}
            onClick={() => { flushSave(); setStep(i); }}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1 ${
              i === stepIdx
                ? 'bg-emerald-800 text-white'
                : i < stepIdx
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {i < stepIdx && <Check className="w-3 h-3" />}
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        {renderStep()}
        {form.tipo_contrato === 'exclusividade' && (
          <EtapaConcluidaBox
            stepIndex={stepIdx}
            label={dynamicStepLabels[stepIdx]}
            form={form}
            onToggle={toggleEtapaConcluida}
            entidade="contrato"
          />
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={goPrev}
          disabled={step === 0}
        >
          <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
        </Button>
        <Button
          onClick={goNext}
          disabled={step >= etapas.length - 1}
          className="bg-emerald-900 hover:bg-emerald-800 text-white"
        >
          Próxima <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>
    </div>
  );
};

export default ContratoWizard;
