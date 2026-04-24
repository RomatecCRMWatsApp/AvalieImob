// @module contratos/ContratoWizard — Wizard de 11 etapas para criacao/edicao de contratos
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
import { contratosAPI, perfilAPI } from '../../../lib/api';
import ImovelMap from '../../maps/ImovelMap';
import RomaIAAvatar from '../../common/RomaIAAvatar';

/* ─── Step labels ────────────────────────────────────────── */
const STEP_LABELS = [
  'Tipo',
  'Vendedor(es)',
  'Comprador(es)',
  'Corretor',
  'Objeto',
  'Pagamento',
  'Cláusulas',
  'Validação',
  'Testemunhas',
  'Revisão',
  'Exportar',
];

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
      { value: 'usufruto',             label: 'Usufruto',            desc: 'Direito real de uso e gozo de bem alheio.' },
      { value: 'compra_venda_veiculo', label: 'C&V Veículo',         desc: 'Compra e venda de veículo automotor.' },
      { value: 'distrato',             label: 'Distrato',            desc: 'Desfazimento de contrato anterior entre as partes.' },
    ],
  },
];

/* ─── Empty form ─────────────────────────────────────────── */
const EMPTY = {
  tipo: '',
  status: 'MINUTA',
  cidade_assinatura: '',
  data_assinatura: '',
  foro_eleito: '',
  vendedores: [],
  compradores: [],
  corretor: { incluir: false, nome: '', cpf_cnpj: '', creci: '', email: '', telefone: '', comissao_percentual: 6, exclusividade: false, prazo_exclusividade: '' },
  objeto: { tipo_bem: 'imovel_urbano', endereco: '', bairro: '', cidade: '', uf: '', cep: '', registro_imovel: '', matricula: '', area_total: '', area_construida: '', situacao_ocupacao: '', onus: '', benfeitorias: '', ccir: '', car: '', modulos_fiscais: '', descricao_veiculo: '', placa: '', renavam: '', chassi: '', ano_fabricacao: '', cor: '' },
  pagamento: { valor_total: '', arras_valor: '', arras_data: '', arras_tipo: 'confirmatorias', formas: [], penalidades: null },
};

const EMPTY_PESSOA = { tipo: 'pf', nome: '', cpf: '', rg: '', rg_orgao: '', nascimento: '', estado_civil: '', profissao: '', nacionalidade: 'brasileiro(a)', email: '', telefone: '', endereco: '', cidade: '', uf: '', cep: '', conjuge_nome: '', conjuge_cpf: '', conjuge_rg: '', conjuge_nascimento: '', conjuge_profissao: '', conjuge_nacionalidade: 'brasileiro(a)', procurador: false, procurador_nome: '', procurador_cpf: '', procurador_instrumento: '', cnpj: '', razao_social: '', nome_fantasia: '', inscricao_estadual: '', representante_nome: '', representante_cpf: '', representante_cargo: '' };

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

    {TIPOS.map((grupo) => (
      <div key={grupo.categoria}>
        <div className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-2">{grupo.categoria}</div>
        <div className="grid sm:grid-cols-2 gap-3">
          {grupo.items.map((t) => (
            <button
              key={t.value}
              onClick={() => setForm({ ...form, tipo: t.value })}
              className={`text-left p-4 rounded-xl border-2 transition-all ${
                form.tipo === t.value
                  ? 'border-emerald-600 bg-emerald-50 shadow-sm'
                  : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
              }`}
            >
              <div className="font-semibold text-gray-900 text-sm">{t.label}</div>
              <div className="text-xs text-gray-500 mt-0.5 leading-snug">{t.desc}</div>
            </button>
          ))}
        </div>
      </div>
    ))}

    <div className="bg-gray-50 rounded-xl p-4 grid sm:grid-cols-3 gap-4">
      <Input label="Cidade de Assinatura" value={form.cidade_assinatura} onChange={(v) => setForm({ ...form, cidade_assinatura: v })} placeholder="Ex: Cuiabá/MT" />
      <Input label="Data de Assinatura" value={form.data_assinatura} onChange={(v) => setForm({ ...form, data_assinatura: v })} type="date" />
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
                <Input label="Nascimento" value={pessoa.conjuge_nascimento} onChange={(v) => upd('conjuge_nascimento', v)} type="date" />
                <Input label="Profissão" value={pessoa.conjuge_profissao} onChange={(v) => upd('conjuge_profissao', v)} />
                <Input label="Nacionalidade" value={pessoa.conjuge_nacionalidade} onChange={(v) => upd('conjuge_nacionalidade', v)} />
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
   STEP 2 — Vendedor(es)
═══════════════════════════════════════════════════════════ */
const Step2Vendedores = ({ form, setForm }) => {
  const addVendedor = () => setForm({ ...form, vendedores: [...form.vendedores, { ...EMPTY_PESSOA }] });
  const removeVendedor = (i) => setForm({ ...form, vendedores: form.vendedores.filter((_, idx) => idx !== i) });
  const updateVendedor = (i, p) => setForm({ ...form, vendedores: form.vendedores.map((v, idx) => idx === i ? p : v) });

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Vendedor(es) / Locador(es)</h2>
        <p className="text-sm text-gray-500">Informe os dados de todas as partes que alienam ou cedem o bem.</p>
      </div>

      {form.vendedores.length === 0 && (
        <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-200">
          <Users className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Nenhum vendedor adicionado ainda.</p>
        </div>
      )}

      {form.vendedores.map((v, i) => (
        <div key={i} className="relative">
          <PessoaForm pessoa={v} onChange={(p) => updateVendedor(i, p)} titulo={`Vendedor ${i + 1}`} />
          {form.vendedores.length > 1 && (
            <button
              onClick={() => removeVendedor(i)}
              className="absolute top-3 right-3 text-red-500 hover:text-red-700 transition"
              title="Remover"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      ))}

      <Button variant="outline" onClick={addVendedor} className="w-full border-dashed border-emerald-300 text-emerald-700 hover:bg-emerald-50">
        <Plus className="w-4 h-4 mr-2" /> Adicionar outro vendedor
      </Button>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 3 — Comprador(es)
═══════════════════════════════════════════════════════════ */
const Step3Compradores = ({ form, setForm }) => {
  const addComprador = () => setForm({ ...form, compradores: [...form.compradores, { ...EMPTY_PESSOA }] });
  const removeComprador = (i) => setForm({ ...form, compradores: form.compradores.filter((_, idx) => idx !== i) });
  const updateComprador = (i, p) => setForm({ ...form, compradores: form.compradores.map((v, idx) => idx === i ? p : v) });

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Comprador(es) / Locatário(s)</h2>
        <p className="text-sm text-gray-500">Informe os dados de todas as partes que adquirem ou tomam o bem.</p>
      </div>

      {form.compradores.length === 0 && (
        <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-200">
          <Users className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Nenhum comprador adicionado ainda.</p>
        </div>
      )}

      {form.compradores.map((c, i) => (
        <div key={i} className="relative">
          <PessoaForm pessoa={c} onChange={(p) => updateComprador(i, p)} titulo={`Comprador ${i + 1}`} />
          {form.compradores.length > 1 && (
            <button
              onClick={() => removeComprador(i)}
              className="absolute top-3 right-3 text-red-500 hover:text-red-700 transition"
              title="Remover"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      ))}

      <Button variant="outline" onClick={addComprador} className="w-full border-dashed border-emerald-300 text-emerald-700 hover:bg-emerald-50">
        <Plus className="w-4 h-4 mr-2" /> Adicionar outro comprador
      </Button>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════
   STEP 4 — Corretor
═══════════════════════════════════════════════════════════ */
const Step4Corretor = ({ form, setForm, perfil }) => {
  const cor = form.corretor;
  const upd = (key, val) => setForm({ ...form, corretor: { ...cor, [key]: val } });

  const valorComissao = cor.comissao_percentual && form.pagamento?.valor_total
    ? (parseFloat(form.pagamento.valor_total) * parseFloat(cor.comissao_percentual)) / 100
    : null;

  const usarMeusDados = () => {
    if (!perfil) return;
    setForm({
      ...form,
      corretor: {
        ...cor,
        nome: perfil.nome_completo || cor.nome,
        email: perfil.email || cor.email,
        telefone: perfil.telefone || cor.telefone,
        creci: (perfil.registros || []).find(r => r.tipo === 'CRECI')?.numero
          ? `CRECI ${(perfil.registros.find(r => r.tipo === 'CRECI')).numero}`
          : cor.creci,
      },
    });
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Corretor de Imóveis</h2>
        <p className="text-sm text-gray-500">Inclua o corretor responsável pela intermediação, se houver.</p>
      </div>

      <label className="flex items-center gap-2 cursor-pointer select-none text-sm font-medium text-gray-700 bg-gray-50 p-3 rounded-xl">
        <input
          type="checkbox"
          checked={!!cor.incluir}
          onChange={(e) => upd('incluir', e.target.checked)}
          className="rounded"
        />
        Incluir corretor neste contrato
      </label>

      {cor.incluir && (
        <div className="space-y-4">
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

          <div className="bg-gray-50 rounded-xl p-4 grid sm:grid-cols-2 gap-3">
            <Input label="Nome do Corretor" value={cor.nome} onChange={(v) => upd('nome', v)} required />
            <Input label="CRECI" value={cor.creci} onChange={(v) => upd('creci', v)} placeholder="CRECI/MT 12345-J" />
            <Input label="CPF / CNPJ" value={cor.cpf_cnpj} onChange={(v) => upd('cpf_cnpj', v)} />
            <Input label="E-mail" value={cor.email} onChange={(v) => upd('email', v)} type="email" />
            <Input label="Telefone" value={cor.telefone} onChange={(v) => upd('telefone', v)} placeholder="(65) 99999-9999" />
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
          </div>

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
              <Input
                label="Prazo de exclusividade"
                value={cor.prazo_exclusividade}
                onChange={(v) => upd('prazo_exclusividade', v)}
                placeholder="Ex: 90 dias a partir de 01/06/2025"
              />
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
            <Input label="Registro de Imóveis" value={obj.registro_imovel} onChange={(v) => upd('registro_imovel', v)} placeholder="Ex: 1º CRI de Cuiabá/MT" />
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ônus / Gravames</label>
              <textarea
                value={obj.onus || ''}
                onChange={(e) => upd('onus', e.target.value)}
                rows={2}
                placeholder="Ex: Livre e desembaraçado de quaisquer ônus ou inscrever gravame específico"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Benfeitorias Incluídas</label>
              <textarea
                value={obj.benfeitorias || ''}
                onChange={(e) => upd('benfeitorias', e.target.value)}
                rows={2}
                placeholder="Ex: Incluídas as instalações elétricas, hidráulicas e etc."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>
          {enderecoCompleto.length > 5 && (
            <ImovelMap endereco={enderecoCompleto} height={260} />
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
          <Input label="Registro de Imóveis" value={obj.registro_imovel} onChange={(v) => upd('registro_imovel', v)} />
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Ônus / Gravames</label>
            <textarea
              value={obj.onus || ''}
              onChange={(e) => upd('onus', e.target.value)}
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
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

  useEffect(() => {
    setForm(f => ({ ...f, clausulas }));
  }, [clausulas]); // eslint-disable-line react-hooks/exhaustive-deps

  const gerarClausulas = async () => {
    if (!contratoId) {
      toast({ title: 'Salve o contrato antes de gerar cláusulas', variant: 'destructive' });
      return;
    }
    setIaState('thinking');
    try {
      const res = await contratosAPI.gerarClausulas(contratoId, { tipo: form.tipo });
      setClausulas(res.clausulas || []);
      setIaState('done');
      toast({ title: `${res.clausulas?.length || 0} cláusulas geradas pela Roma_IA` });
    } catch (err) {
      setIaState('idle');
      toast({ title: 'Erro ao gerar cláusulas', description: err.response?.data?.detail, variant: 'destructive' });
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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-1">Cláusulas do Contrato</h2>
        <p className="text-sm text-gray-500">Gere as cláusulas automaticamente via Roma_IA ou adicione manualmente.</p>
      </div>

      {/* Roma_IA card */}
      <div className="bg-gradient-to-r from-emerald-950 to-emerald-800 rounded-xl p-5 flex items-center gap-5">
        <RomaIAAvatar state={iaState === 'thinking' ? 'thinking' : iaState === 'done' ? 'speaking' : 'idle'} size="md" />
        <div className="flex-1 min-w-0">
          <div className="text-white font-semibold text-sm mb-0.5">Roma_IA — Geração de Cláusulas</div>
          <div className="text-emerald-300 text-xs">
            {iaState === 'thinking' ? 'Analisando tipo de contrato e gerando cláusulas jurídicas...' :
             iaState === 'done' ? `${clausulas.length} cláusulas geradas. Revise e edite conforme necessário.` :
             'Gere cláusulas adequadas ao tipo de contrato selecionado.'}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          {clausulas.length > 0 && (
            <Button size="sm" variant="outline" onClick={gerarClausulas} disabled={iaState === 'thinking'}
              className="border-emerald-400 text-emerald-300 hover:bg-emerald-800 text-xs">
              <RotateCcw className="w-3.5 h-3.5 mr-1" /> Regenerar
            </Button>
          )}
          <Button size="sm" onClick={gerarClausulas} disabled={iaState === 'thinking'}
            className="bg-amber-500 hover:bg-amber-400 text-white text-xs">
            {iaState === 'thinking' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-1" />}
            {iaState === 'thinking' ? 'Gerando...' : 'Gerar Cláusulas via Roma_IA'}
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
                          <label className="block text-sm font-medium text-gray-700 mb-1">Conteúdo</label>
                          <textarea rows={4} value={editBuffer.conteudo || ''} onChange={(e) => setEditBuffer({ ...editBuffer, conteudo: e.target.value })}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none" />
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
                            <p className="text-sm text-gray-600 mt-1.5 leading-relaxed line-clamp-3">{c.conteudo}</p>
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
const EMPTY_TESTEMUNHA = { nome: '', cpf: '', rg: '', profissao: '', endereco: '', cidade: '', uf: '' };

const Step9Testemunhas = ({ form, setForm }) => {
  const testemunhas = form.testemunhas || [{ ...EMPTY_TESTEMUNHA }, { ...EMPTY_TESTEMUNHA }];

  const upd = (i, key, val) => {
    const list = [...testemunhas];
    list[i] = { ...list[i], [key]: val };
    setForm({ ...form, testemunhas: list });
  };

  useEffect(() => {
    if (!form.testemunhas) {
      setForm(f => ({ ...f, testemunhas: [{ ...EMPTY_TESTEMUNHA }, { ...EMPTY_TESTEMUNHA }] }));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
          <div className="font-semibold text-gray-800 text-sm">Testemunha {i + 1}</div>
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
            <Input label="Profissão" value={testemunhas[i]?.profissao} onChange={(v) => upd(i, 'profissao', v)} />
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
          </div>
        )}
      </div>

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
const Step11Exportar = ({ form, contratoId }) => {
  const { toast } = useToast();
  const [loadingDocx, setLoadingDocx] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [loadingArras, setLoadingArras] = useState(false);
  const [loadingLacrar, setLoadingLacrar] = useState(false);
  const [lacrado, setLacrado] = useState(form.lacrado || false);
  const [loadingD4sign, setLoadingD4sign] = useState(false);
  const [linkPublico, setLinkPublico] = useState(form.link_publico || null);
  const [linkCopiado, setLinkCopiado] = useState(false);

  const downloadBlob = (data, filename) => {
    const url = window.URL.createObjectURL(new Blob([data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const baixarDocx = async () => {
    if (!contratoId) return;
    setLoadingDocx(true);
    try {
      const res = await contratosAPI.docx(contratoId);
      downloadBlob(res.data, `contrato_${form.numero || contratoId}.docx`);
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
      const res = await contratosAPI.pdf(contratoId);
      downloadBlob(res.data, `contrato_${form.numero || contratoId}.pdf`);
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
      const res = await contratosAPI.reciboArras(contratoId);
      downloadBlob(res.data, `recibo_arras_${form.numero || contratoId}.docx`);
    } catch {
      toast({ title: 'Erro ao gerar Recibo de Arras', variant: 'destructive' });
    } finally {
      setLoadingArras(false);
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
   MAIN WIZARD
═══════════════════════════════════════════════════════════ */
const ContratoWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();

  const isNew = !id || id === 'novo';
  const [form, setForm] = useState({ ...EMPTY, vendedores: [{ ...EMPTY_PESSOA }], compradores: [{ ...EMPTY_PESSOA }] });
  const [contratoId, setContratoId] = useState(isNew ? null : id);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [perfil, setPerfil] = useState(null);
  const debounceRef = useRef(null);

  /* Load existing */
  const load = useCallback(async () => {
    if (!contratoId) return;
    setLoading(true);
    try {
      const data = await contratosAPI.buscar(contratoId);
      setForm({ ...EMPTY, vendedores: [{ ...EMPTY_PESSOA }], compradores: [{ ...EMPTY_PESSOA }], ...data });
    } catch (err) {
      console.warn(err);
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
    setSaving(true);
    try {
      if (contratoId) {
        await contratosAPI.atualizar(contratoId, form);
      } else {
        const created = await contratosAPI.criar(form);
        setContratoId(created.id);
        nav(`/dashboard/contratos/${created.id}`, { replace: true });
      }
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      console.warn(err);
      if (!silent) toast({ title: 'Erro ao salvar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [form, contratoId, nav, toast]);

  /* Autosave */
  useEffect(() => {
    if (isNew && !contratoId) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 2500);
    return () => clearTimeout(debounceRef.current);
  }, [form]); // eslint-disable-line react-hooks/exhaustive-deps

  const goNext = () => { if (step < STEP_LABELS.length - 1) setStep(s => s + 1); };
  const goPrev = () => { if (step > 0) setStep(s => s - 1); };

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <Loader2 className="w-6 h-6 animate-spin text-emerald-800" />
    </div>
  );

  const renderStep = () => {
    switch (step) {
      case 0: return <Step1Tipo form={form} setForm={setForm} />;
      case 1: return <Step2Vendedores form={form} setForm={setForm} />;
      case 2: return <Step3Compradores form={form} setForm={setForm} />;
      case 3: return <Step4Corretor form={form} setForm={setForm} perfil={perfil} />;
      case 4: return <Step5Objeto form={form} setForm={setForm} />;
      case 5: return <Step6Pagamento form={form} setForm={setForm} contratoId={contratoId} />;
      case 6: return <Step7Clausulas form={form} setForm={setForm} contratoId={contratoId} />;
      case 7: return <Step8Validacao contratoId={contratoId} onGoToStep={setStep} />;
      case 8: return <Step9Testemunhas form={form} setForm={setForm} />;
      case 9: return <Step10Revisao form={form} contratoId={contratoId} />;
      case 10: return <Step11Exportar form={form} contratoId={contratoId} />;
      default: return null;
    }
  };

  const progressPct = Math.round(((step + 1) / STEP_LABELS.length) * 100);

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
            {isNew ? 'Novo Contrato' : `Contrato ${form.numero || ''}`}
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
            Etapa {step + 1} de {STEP_LABELS.length} — {STEP_LABELS[step]}
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

      {/* Step tabs (desktop) */}
      <div className="hidden lg:flex gap-1 flex-wrap">
        {STEP_LABELS.map((label, i) => (
          <button
            key={i}
            onClick={() => setStep(i)}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1 ${
              i === step
                ? 'bg-emerald-800 text-white'
                : i < step
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {i < step && <Check className="w-3 h-3" />}
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        {renderStep()}
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
          disabled={step === STEP_LABELS.length - 1}
          className="bg-emerald-900 hover:bg-emerald-800 text-white"
        >
          Próxima <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>
    </div>
  );
};

export default ContratoWizard;
