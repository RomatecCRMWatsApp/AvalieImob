import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ChevronLeft, ChevronRight, Save, Loader2, Check,
  Tractor, Wheat, Beef, Wrench, Car, Package,
  User, MapPin, BarChart2, ClipboardList, DollarSign, Award
} from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { garantiasAPI } from '../../../lib/api';

// ── Default empty form ──────────────────────────────────────────────────────
const EMPTY = {
  numero: '',
  tipo_garantia: 'imovel_rural',
  finalidade: 'credito_rural',
  solicitante: { nome: '', cpf_cnpj: '', instituicao_financeira: '', telefone: '', email: '' },
  descricao_bem: '',
  endereco: '', municipio: '', uf: '', cep: '', gps_lat: '', gps_lng: '',
  matricula: '', cartorio: '', data_vistoria: '',
  // rural
  area_total_ha: 0, area_construida_m2: 0, uso_atual: '', benfeitorias: '', topografia: '', solo_vegetacao: '',
  // graos
  cultura: '', quantidade_toneladas: 0, sacas: 0, produtividade_sc_ha: 0, local_armazenagem: '', safra_referencia: '',
  // bovinos
  raca_tipo: '', quantidade_cabecas: 0, categoria: '', peso_medio_kg: 0, aptidao: '', local_rebanho: '',
  // equip/veic
  marca: '', modelo: '', ano_fabricacao: 0, numero_serie: '', potencia: '', horimetro_hodometro: '',
  // avaliacao
  estado_conservacao: 'bom', valor_unitario: 0, valor_total: 0,
  data_avaliacao: '', data_validade: '',
  metodologia: '', fundamentacao_legal: 'NBR 14.653', mercado_referencia: '', fatores_depreciacao: '', grau_fundamentacao: '',
  resultado_intervalo_inf: 0, resultado_intervalo_sup: 0, resultado_em_extenso: '',
  // conclusao
  consideracoes: '', ressalvas: '',
  responsavel: { nome: '', creci: '', cnai: '', registro: '' },
  fotos: [], observacoes: '',
  status: 'rascunho',
};

// ── Step definitions ─────────────────────────────────────────────────────────
const STEPS = [
  { id: 'tipo',        label: 'Tipo',          icon: ClipboardList },
  { id: 'solicitante', label: 'Solicitante',   icon: User },
  { id: 'bem',         label: 'Descrição',     icon: Package },
  { id: 'localizacao', label: 'Localização',   icon: MapPin },
  { id: 'avaliacao',   label: 'Avaliação',     icon: BarChart2 },
  { id: 'resultado',   label: 'Resultado',     icon: DollarSign },
  { id: 'conclusao',   label: 'Conclusão',     icon: Award },
];

const TIPO_OPTIONS = [
  { value: 'imovel_rural', label: 'Imóvel Rural',   desc: 'Terras, fazendas, sítios, gleba',     icon: Tractor },
  { value: 'graos_safra',  label: 'Grãos / Safra',  desc: 'Soja, milho, café, cana, etc.',       icon: Wheat },
  { value: 'bovinos',      label: 'Bovinos',         desc: 'Rebanho bovino, pecuária de corte/leite', icon: Beef },
  { value: 'equipamentos', label: 'Equipamentos',   desc: 'Maquinário agrícola, implementos',    icon: Wrench },
  { value: 'veiculos',     label: 'Veículos',        desc: 'Caminhões, tratores, utilitários',    icon: Car },
  { value: 'outros',       label: 'Outros',          desc: 'Demais bens dados em garantia',       icon: Package },
];

const FINALIDADE_OPTIONS = [
  { value: 'credito_rural',        label: 'Crédito Rural' },
  { value: 'financiamento',        label: 'Financiamento' },
  { value: 'penhor',               label: 'Penhor' },
  { value: 'alienacao_fiduciaria', label: 'Alienação Fiduciária' },
  { value: 'outros',               label: 'Outros' },
];

const UF_OPTIONS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
  'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
];

// ── Helpers ──────────────────────────────────────────────────────────────────
const Field = ({ label, children, required }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
    {children}
  </div>
);

const Input = ({ value, onChange, ...props }) => (
  <input
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  />
);

const Textarea = ({ value, onChange, rows = 3, ...props }) => (
  <textarea
    value={value ?? ''}
    onChange={onChange}
    rows={rows}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white resize-none"
  />
);

const Select = ({ value, onChange, children, ...props }) => (
  <select
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  >
    {children}
  </select>
);

const SectionTitle = ({ children }) => (
  <h3 className="text-sm font-semibold text-emerald-800 uppercase tracking-wider mb-4 pb-2 border-b border-emerald-100">
    {children}
  </h3>
);

// ── Steps ─────────────────────────────────────────────────────────────────────

// Step 1: Tipo de garantia + finalidade
const StepTipo = ({ form, set }) => {
  const tipo = form.tipo_garantia;
  return (
    <div className="space-y-6">
      <SectionTitle>Tipo de Garantia</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {TIPO_OPTIONS.map(({ value, label, desc, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('tipo_garantia', value)}
            className={`flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition ${
              tipo === value
                ? 'border-emerald-700 bg-emerald-50'
                : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
            }`}
          >
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${tipo === value ? 'bg-emerald-900' : 'bg-gray-100'}`}>
              <Icon className={`w-5 h-5 ${tipo === value ? 'text-white' : 'text-gray-600'}`} />
            </div>
            <div>
              <div className="font-semibold text-sm text-gray-900">{label}</div>
              <div className="text-[11px] text-gray-500 leading-tight mt-0.5">{desc}</div>
            </div>
          </button>
        ))}
      </div>

      <SectionTitle>Finalidade</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {FINALIDADE_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('finalidade', value)}
            className={`px-4 py-2.5 rounded-lg border-2 text-sm font-medium transition ${
              form.finalidade === value
                ? 'border-emerald-700 bg-emerald-50 text-emerald-900'
                : 'border-gray-200 text-gray-700 hover:border-emerald-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
};

// Step 2: Solicitante
const StepSolicitante = ({ form, setNested }) => {
  const s = form.solicitante || {};
  return (
    <div className="space-y-6">
      <SectionTitle>Dados do Solicitante</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Nome / Razão Social" required>
          <Input value={s.nome} onChange={(e) => setNested('solicitante', 'nome', e.target.value)} placeholder="Ex.: João da Silva" />
        </Field>
        <Field label="CPF / CNPJ">
          <Input value={s.cpf_cnpj} onChange={(e) => setNested('solicitante', 'cpf_cnpj', e.target.value)} placeholder="000.000.000-00" />
        </Field>
        <Field label="Instituição Financeira">
          <Input value={s.instituicao_financeira} onChange={(e) => setNested('solicitante', 'instituicao_financeira', e.target.value)} placeholder="Ex.: Banco do Brasil S.A." />
        </Field>
        <Field label="Telefone">
          <Input value={s.telefone} onChange={(e) => setNested('solicitante', 'telefone', e.target.value)} placeholder="(00) 00000-0000" />
        </Field>
        <Field label="E-mail" className="md:col-span-2">
          <Input value={s.email} onChange={(e) => setNested('solicitante', 'email', e.target.value)} placeholder="email@exemplo.com" type="email" />
        </Field>
      </div>
    </div>
  );
};

// Step 3: Descrição do bem (campos dinâmicos por tipo)
const StepBem = ({ form, set }) => {
  const tipo = form.tipo_garantia;
  return (
    <div className="space-y-6">
      <SectionTitle>Descrição do Bem</SectionTitle>
      <Field label="Descrição Geral" required>
        <Textarea
          value={form.descricao_bem}
          onChange={(e) => set('descricao_bem', e.target.value)}
          rows={4}
          placeholder="Descreva detalhadamente o bem dado em garantia..."
        />
      </Field>

      {/* IMÓVEL RURAL */}
      {tipo === 'imovel_rural' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Imóvel Rural</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Área Total (ha)">
              <Input type="number" value={form.area_total_ha} onChange={(e) => set('area_total_ha', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Área Construída (m²)">
              <Input type="number" value={form.area_construida_m2} onChange={(e) => set('area_construida_m2', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Uso Atual">
              <Select value={form.uso_atual} onChange={(e) => set('uso_atual', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="pastagem">Pastagem</option>
                <option value="lavoura">Lavoura</option>
                <option value="floresta">Floresta</option>
                <option value="misto">Misto</option>
                <option value="outros">Outros</option>
              </Select>
            </Field>
          </div>
          <Field label="Benfeitorias">
            <Textarea value={form.benfeitorias} onChange={(e) => set('benfeitorias', e.target.value)} placeholder="Casas, currais, armazéns, poços, cercas, etc." />
          </Field>
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Topografia">
              <Input value={form.topografia} onChange={(e) => set('topografia', e.target.value)} placeholder="Plana, ondulada, montanhosa..." />
            </Field>
            <Field label="Solo / Vegetação">
              <Input value={form.solo_vegetacao} onChange={(e) => set('solo_vegetacao', e.target.value)} placeholder="Latossolo vermelho, cerrado..." />
            </Field>
          </div>
        </div>
      )}

      {/* GRÃOS / SAFRA */}
      {tipo === 'graos_safra' && (
        <div className="space-y-4">
          <SectionTitle>Dados dos Grãos / Safra</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Cultura">
              <Select value={form.cultura} onChange={(e) => set('cultura', e.target.value)}>
                <option value="">Selecionar...</option>
                {['Soja','Milho','Café','Cana-de-açúcar','Algodão','Arroz','Feijão','Trigo','Sorgo','Outros'].map((c) => (
                  <option key={c} value={c.toLowerCase()}>{c}</option>
                ))}
              </Select>
            </Field>
            <Field label="Quantidade (toneladas)">
              <Input type="number" value={form.quantidade_toneladas} onChange={(e) => set('quantidade_toneladas', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Sacas (60 kg)">
              <Input type="number" value={form.sacas} onChange={(e) => set('sacas', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Produtividade (sc/ha)">
              <Input type="number" value={form.produtividade_sc_ha} onChange={(e) => set('produtividade_sc_ha', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Safra Referência">
              <Input value={form.safra_referencia} onChange={(e) => set('safra_referencia', e.target.value)} placeholder="Ex.: 2024/2025" />
            </Field>
            <Field label="Local de Armazenagem">
              <Input value={form.local_armazenagem} onChange={(e) => set('local_armazenagem', e.target.value)} placeholder="Armazém, silo, fazenda..." />
            </Field>
          </div>
        </div>
      )}

      {/* BOVINOS */}
      {tipo === 'bovinos' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Rebanho Bovino</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Raça / Tipo">
              <Input value={form.raca_tipo} onChange={(e) => set('raca_tipo', e.target.value)} placeholder="Ex.: Nelore, Angus, Girolando..." />
            </Field>
            <Field label="Quantidade (cabeças)">
              <Input type="number" value={form.quantidade_cabecas} onChange={(e) => set('quantidade_cabecas', parseInt(e.target.value) || 0)} />
            </Field>
            <Field label="Categoria">
              <Select value={form.categoria} onChange={(e) => set('categoria', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="boi_gordo">Boi Gordo</option>
                <option value="vaca">Vaca</option>
                <option value="novilha">Novilha</option>
                <option value="bezerro">Bezerro</option>
                <option value="touro">Touro</option>
                <option value="misto">Misto</option>
              </Select>
            </Field>
            <Field label="Peso Médio (kg)">
              <Input type="number" value={form.peso_medio_kg} onChange={(e) => set('peso_medio_kg', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Aptidão">
              <Select value={form.aptidao} onChange={(e) => set('aptidao', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="corte">Corte</option>
                <option value="leite">Leite</option>
                <option value="misto">Misto</option>
              </Select>
            </Field>
            <Field label="Local do Rebanho">
              <Input value={form.local_rebanho} onChange={(e) => set('local_rebanho', e.target.value)} placeholder="Fazenda, município..." />
            </Field>
          </div>
        </div>
      )}

      {/* EQUIPAMENTOS */}
      {tipo === 'equipamentos' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Equipamento</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Marca">
              <Input value={form.marca} onChange={(e) => set('marca', e.target.value)} placeholder="Ex.: John Deere, Massey Ferguson..." />
            </Field>
            <Field label="Modelo">
              <Input value={form.modelo} onChange={(e) => set('modelo', e.target.value)} placeholder="Ex.: 7500 Turbo" />
            </Field>
            <Field label="Ano de Fabricação">
              <Input type="number" value={form.ano_fabricacao} onChange={(e) => set('ano_fabricacao', parseInt(e.target.value) || 0)} placeholder="Ex.: 2020" />
            </Field>
            <Field label="Número de Série / Chassi">
              <Input value={form.numero_serie} onChange={(e) => set('numero_serie', e.target.value)} />
            </Field>
            <Field label="Potência">
              <Input value={form.potencia} onChange={(e) => set('potencia', e.target.value)} placeholder="Ex.: 150 cv" />
            </Field>
            <Field label="Horímetro / Hodômetro">
              <Input value={form.horimetro_hodometro} onChange={(e) => set('horimetro_hodometro', e.target.value)} placeholder="Ex.: 1.200 h" />
            </Field>
          </div>
        </div>
      )}

      {/* VEÍCULOS */}
      {tipo === 'veiculos' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Veículo</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Marca">
              <Input value={form.marca} onChange={(e) => set('marca', e.target.value)} placeholder="Ex.: Mercedes-Benz, Volvo..." />
            </Field>
            <Field label="Modelo">
              <Input value={form.modelo} onChange={(e) => set('modelo', e.target.value)} placeholder="Ex.: Actros 2646" />
            </Field>
            <Field label="Ano de Fabricação">
              <Input type="number" value={form.ano_fabricacao} onChange={(e) => set('ano_fabricacao', parseInt(e.target.value) || 0)} />
            </Field>
            <Field label="Número de Série / Chassi / Placa">
              <Input value={form.numero_serie} onChange={(e) => set('numero_serie', e.target.value)} />
            </Field>
            <Field label="Hodômetro">
              <Input value={form.horimetro_hodometro} onChange={(e) => set('horimetro_hodometro', e.target.value)} placeholder="Ex.: 120.000 km" />
            </Field>
          </div>
        </div>
      )}

      {/* OUTROS */}
      {tipo === 'outros' && (
        <div className="space-y-4">
          <SectionTitle>Identificação do Bem</SectionTitle>
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Marca / Fabricante">
              <Input value={form.marca} onChange={(e) => set('marca', e.target.value)} />
            </Field>
            <Field label="Modelo / Referência">
              <Input value={form.modelo} onChange={(e) => set('modelo', e.target.value)} />
            </Field>
            <Field label="Número de Série">
              <Input value={form.numero_serie} onChange={(e) => set('numero_serie', e.target.value)} />
            </Field>
            <Field label="Ano de Fabricação">
              <Input type="number" value={form.ano_fabricacao} onChange={(e) => set('ano_fabricacao', parseInt(e.target.value) || 0)} />
            </Field>
          </div>
        </div>
      )}
    </div>
  );
};

// Step 4: Localização e Vistoria
const StepLocalizacao = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Localização</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Endereço" className="md:col-span-2">
        <Input value={form.endereco} onChange={(e) => set('endereco', e.target.value)} placeholder="Rua, número, complemento..." />
      </Field>
      <Field label="Município" required>
        <Input value={form.municipio} onChange={(e) => set('municipio', e.target.value)} placeholder="Ex.: Sorriso" />
      </Field>
      <Field label="UF">
        <Select value={form.uf} onChange={(e) => set('uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Select>
      </Field>
      <Field label="CEP">
        <Input value={form.cep} onChange={(e) => set('cep', e.target.value)} placeholder="00000-000" />
      </Field>
      <Field label="Matrícula / NIRF">
        <Input value={form.matricula} onChange={(e) => set('matricula', e.target.value)} />
      </Field>
      <Field label="Cartório de Registro">
        <Input value={form.cartorio} onChange={(e) => set('cartorio', e.target.value)} />
      </Field>
    </div>

    <SectionTitle>Coordenadas GPS</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Latitude">
        <Input value={form.gps_lat} onChange={(e) => set('gps_lat', e.target.value)} placeholder="-12.345678" />
      </Field>
      <Field label="Longitude">
        <Input value={form.gps_lng} onChange={(e) => set('gps_lng', e.target.value)} placeholder="-55.123456" />
      </Field>
    </div>

    <SectionTitle>Vistoria</SectionTitle>
    <Field label="Data da Vistoria">
      <Input type="date" value={form.data_vistoria} onChange={(e) => set('data_vistoria', e.target.value)} />
    </Field>
    <Field label="Observações da Vistoria">
      <Textarea value={form.observacoes} onChange={(e) => set('observacoes', e.target.value)} rows={3} placeholder="Condições observadas durante a vistoria..." />
    </Field>
  </div>
);

// Step 5: Avaliação e Metodologia
const StepAvaliacao = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Metodologia (NBR 14.653)</SectionTitle>
    <Field label="Metodologia Utilizada" required>
      <Select value={form.metodologia} onChange={(e) => set('metodologia', e.target.value)}>
        <option value="">Selecionar...</option>
        <option value="comparativo_direto">Método Comparativo Direto de Dados de Mercado</option>
        <option value="renda">Método da Renda</option>
        <option value="involutivo">Método Involutivo</option>
        <option value="evolutivo">Método Evolutivo / Custo de Reprodução</option>
        <option value="producao">Método da Capitalização da Renda (Agropecuária)</option>
        <option value="cotacao_mercado">Cotação de Mercado (grãos/bovinos)</option>
        <option value="outros">Outros</option>
      </Select>
    </Field>
    <Field label="Fundamentação Legal">
      <Input value={form.fundamentacao_legal} onChange={(e) => set('fundamentacao_legal', e.target.value)} />
    </Field>
    <Field label="Mercado de Referência">
      <Textarea value={form.mercado_referencia} onChange={(e) => set('mercado_referencia', e.target.value)} rows={3} placeholder="Descreva as fontes e referências de mercado utilizadas..." />
    </Field>
    <Field label="Fatores de Depreciação / Homogeneização">
      <Textarea value={form.fatores_depreciacao} onChange={(e) => set('fatores_depreciacao', e.target.value)} rows={3} placeholder="Descreva os fatores aplicados..." />
    </Field>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Grau de Fundamentação">
        <Select value={form.grau_fundamentacao} onChange={(e) => set('grau_fundamentacao', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="I">Grau I</option>
          <option value="II">Grau II</option>
          <option value="III">Grau III</option>
        </Select>
      </Field>
      <Field label="Estado de Conservação">
        <Select value={form.estado_conservacao} onChange={(e) => set('estado_conservacao', e.target.value)}>
          <option value="otimo">Ótimo</option>
          <option value="bom">Bom</option>
          <option value="regular">Regular</option>
          <option value="precario">Precário</option>
        </Select>
      </Field>
      <Field label="Data de Avaliação">
        <Input type="date" value={form.data_avaliacao} onChange={(e) => set('data_avaliacao', e.target.value)} />
      </Field>
      <Field label="Data de Validade">
        <Input type="date" value={form.data_validade} onChange={(e) => set('data_validade', e.target.value)} />
      </Field>
    </div>
  </div>
);

// Step 6: Resultado e Valor
const StepResultado = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Resultado da Avaliação</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Valor Unitário (R$)">
        <Input
          type="number"
          value={form.valor_unitario}
          onChange={(e) => set('valor_unitario', parseFloat(e.target.value) || 0)}
          placeholder="0,00"
        />
      </Field>
      <Field label="Valor Total (R$)" required>
        <Input
          type="number"
          value={form.valor_total}
          onChange={(e) => set('valor_total', parseFloat(e.target.value) || 0)}
          placeholder="0,00"
        />
      </Field>
      <Field label="Status">
        <Select value={form.status} onChange={(e) => set('status', e.target.value)}>
          <option value="rascunho">Rascunho</option>
          <option value="em_andamento">Em Andamento</option>
          <option value="concluido">Concluído</option>
        </Select>
      </Field>
      <Field label="Intervalo Inferior (R$)">
        <Input type="number" value={form.resultado_intervalo_inf} onChange={(e) => set('resultado_intervalo_inf', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Intervalo Superior (R$)">
        <Input type="number" value={form.resultado_intervalo_sup} onChange={(e) => set('resultado_intervalo_sup', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>

    <Field label="Valor por Extenso">
      <Input value={form.resultado_em_extenso} onChange={(e) => set('resultado_em_extenso', e.target.value)} placeholder="Ex.: Um milhão e duzentos mil reais" />
    </Field>

    {form.valor_total > 0 && (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
        <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider mb-1">Valor Total Avaliado</div>
        <div className="text-3xl font-bold text-emerald-900">
          {Number(form.valor_total).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
        </div>
      </div>
    )}
  </div>
);

// Step 7: Conclusão e Responsável Técnico
const StepConclusao = ({ form, set, setNested }) => {
  const r = form.responsavel || {};
  return (
    <div className="space-y-6">
      <SectionTitle>Considerações Finais</SectionTitle>
      <Field label="Considerações">
        <Textarea value={form.consideracoes} onChange={(e) => set('consideracoes', e.target.value)} rows={4} placeholder="Pressupostos, limitações e considerações finais da avaliação..." />
      </Field>
      <Field label="Ressalvas">
        <Textarea value={form.ressalvas} onChange={(e) => set('ressalvas', e.target.value)} rows={3} placeholder="Ressalvas aplicáveis conforme NBR 14.653..." />
      </Field>

      <SectionTitle>Responsável Técnico</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Nome do Responsável" required>
          <Input value={r.nome} onChange={(e) => setNested('responsavel', 'nome', e.target.value)} placeholder="Nome completo" />
        </Field>
        <Field label="CRECI">
          <Input value={r.creci} onChange={(e) => setNested('responsavel', 'creci', e.target.value)} placeholder="CRECI-UF 000000" />
        </Field>
        <Field label="CNAI">
          <Input value={r.cnai} onChange={(e) => setNested('responsavel', 'cnai', e.target.value)} placeholder="Número CNAI" />
        </Field>
        <Field label="Registro Complementar (CREA/CAU)">
          <Input value={r.registro} onChange={(e) => setNested('responsavel', 'registro', e.target.value)} placeholder="CREA/CAU número" />
        </Field>
      </div>
    </div>
  );
};

// ── Main Wizard ───────────────────────────────────────────────────────────────
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

  // Auto-save every 30s
  useEffect(() => {
    if (!garantiaId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [form, garantiaId, save]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const setNested = (obj, key, value) =>
    setForm((f) => ({ ...f, [obj]: { ...(f[obj] || {}), [key]: value } }));

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
      case 0: return <StepTipo form={form} set={set} />;
      case 1: return <StepSolicitante form={form} setNested={setNested} />;
      case 2: return <StepBem form={form} set={set} />;
      case 3: return <StepLocalizacao form={form} set={set} />;
      case 4: return <StepAvaliacao form={form} set={set} />;
      case 5: return <StepResultado form={form} set={set} />;
      case 6: return <StepConclusao form={form} set={set} setNested={setNested} />;
      default: return null;
    }
  };

  return (
    <div className="max-w-5xl mx-auto pb-20">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={() => nav('/dashboard/garantias')}>
          <ArrowLeft className="w-4 h-4 mr-1" />Voltar
        </Button>
        <div className="flex items-center gap-2">
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
            const active = i === step;
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
              <Check className="w-4 h-4 mr-1" />Concluir Avaliação
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default GarantiaWizard;
