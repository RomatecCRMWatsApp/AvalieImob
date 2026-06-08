// @module ptam/steps/BciIptuSection — Subseção Cadastro Imobiliário Municipal (BCI / IPTU)
// Exclusiva para imóvel urbano. Os dados vão impressos no PDF do laudo (Seções 3.2 e 3.3).
import React, { useState } from 'react';
import { Input } from '../../../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { Field } from '../shared/primitives';
import { isRural } from '../shared/RuralDocSection';

// Máscara CPF/CNPJ progressiva (11 dígitos -> CPF, 14 -> CNPJ)
function mascaraDoc(v) {
  const n = (v || '').replace(/\D/g, '').slice(0, 14);
  if (n.length <= 11) {
    return n
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/(\d{3})\.(\d{3})\.(\d{3})(\d)/, '$1.$2.$3-$4');
  }
  return n
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2');
}

// Card colapsável simples (sem dependência de accordion externo)
function Card({ icon, title, alerta, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2.5 bg-gray-50 hover:bg-gray-100 text-sm font-semibold text-gray-800 transition-colors"
      >
        <span>{icon}</span>
        <span>{title}</span>
        {alerta && (
          <span className="ml-2 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-xs font-semibold">
            {alerta}
          </span>
        )}
        <span className="ml-auto text-gray-400">{open ? '▾' : '▸'}</span>
      </button>
      {open && <div className="p-3 grid grid-cols-2 gap-4">{children}</div>}
    </div>
  );
}

export default function BciIptuSection({ form, setForm }) {
  const rural = isRural(form.property_type);
  // Só exibe para imóvel urbano com tipo selecionado.
  if (rural || !form.property_type) return null;

  const bci = form.bci || {};
  const iptu = form.iptu || {};

  const setBci = (patch) => setForm({ ...form, bci: { ...bci, ...patch } });
  const setIptu = (patch) => setForm({ ...form, iptu: { ...iptu, ...patch } });

  // Sincroniza área da edificação (BCI) com o campo principal da etapa 5, se vazio.
  const setAreaEdificacao = (val) => {
    const patch = { bci: { ...bci, area_edificacao: val } };
    if (!form.imovel_area_construida) patch.imovel_area_construida = val;
    setForm({ ...form, ...patch });
  };

  const num = (e) => (e.target.value === '' ? null : Number(e.target.value));
  const emDebito = ['Em aberto', 'Parcelado'].includes(iptu.situacao || '');
  const parcelado = iptu.situacao === 'Parcelado';

  return (
    <div className="mt-8 border-t border-gray-100 pt-6 space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="text-sm font-semibold text-gray-900">
          Cadastro Imobiliário Municipal (BCI / IPTU)
        </div>
        <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-xs font-medium">
          Dados obtidos junto à Prefeitura Municipal
        </span>
      </div>
      <p className="text-xs text-gray-400 -mt-1">
        Conforme Boletim do Cadastro Imobiliário emitido pela Prefeitura. Campos opcionais —
        os preenchidos são impressos no PDF do laudo (Seções 3.2 e 3.3).
      </p>

      {/* 🏛️ Identificação Cadastral */}
      <Card icon="🏛️" title="Identificação Cadastral">
        <Field label="Código do Imóvel (CTI)">
          <Input value={bci.codigo_imovel || ''} onChange={(e) => setBci({ codigo_imovel: e.target.value })} placeholder="0001002224" />
        </Field>
        <Field label="Inscrição Cadastral (Loc. Cartográfica)">
          <Input value={bci.inscricao_cadastral || ''} onChange={(e) => setBci({ inscricao_cadastral: e.target.value })} placeholder="00.95.021.0006.00001" />
        </Field>
        <Field label="Setor">
          <Input value={bci.setor || ''} onChange={(e) => setBci({ setor: e.target.value })} placeholder="95" />
        </Field>
        <Field label="Quadra">
          <Input value={bci.quadra || ''} onChange={(e) => setBci({ quadra: e.target.value })} placeholder="021" />
        </Field>
        <Field label="Lote">
          <Input value={bci.lote || ''} onChange={(e) => setBci({ lote: e.target.value })} placeholder="006C" />
        </Field>
        <Field label="Unidade">
          <Input value={bci.unidade || ''} onChange={(e) => setBci({ unidade: e.target.value })} placeholder="00001" />
        </Field>
        <Field label="Situação Cadastral">
          <Select value={bci.situacao || ''} onValueChange={(v) => setBci({ situacao: v })}>
            <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Ativo">Ativo</SelectItem>
              <SelectItem value="Inativo">Inativo</SelectItem>
              <SelectItem value="Cancelado">Cancelado</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="Natureza">
          <Select value={bci.natureza || ''} onValueChange={(v) => setBci({ natureza: v })}>
            <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Prédio">Prédio</SelectItem>
              <SelectItem value="Terreno">Terreno</SelectItem>
              <SelectItem value="Loja">Loja</SelectItem>
              <SelectItem value="Sala">Sala</SelectItem>
              <SelectItem value="Apartamento">Apartamento</SelectItem>
              <SelectItem value="Galpão">Galpão</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="Data de Cadastro">
          <Input type="date" value={bci.data_cadastro || ''} onChange={(e) => setBci({ data_cadastro: e.target.value })} />
        </Field>
        <Field label="Data de Construção">
          <Input type="date" value={bci.data_construcao || ''} onChange={(e) => setBci({ data_construcao: e.target.value })} />
        </Field>
      </Card>

      {/* 👤 Proprietário (BCI) */}
      <Card icon="👤" title="Proprietário / Detentor (BCI)">
        <Field label="Nome do Proprietário ou Detentor" full>
          <Input value={bci.proprietario_nome || ''} onChange={(e) => setBci({ proprietario_nome: e.target.value })} placeholder="Conforme BCI" />
        </Field>
        <Field label="CPF / CNPJ" full>
          <Input value={bci.proprietario_doc || ''} onChange={(e) => setBci({ proprietario_doc: mascaraDoc(e.target.value) })} placeholder="00.000.000/0000-00" />
        </Field>
      </Card>

      {/* 📐 Medidas do Imóvel */}
      <Card icon="📐" title="Medidas do Imóvel (BCI)">
        <Field label="Testada Principal (m)">
          <Input type="number" step="0.01" value={bci.testada_principal ?? ''} onChange={(e) => setBci({ testada_principal: num(e) })} placeholder="0,00" />
        </Field>
        <Field label="Profundidade do Lote (m)">
          <Input type="number" step="0.01" value={bci.prof_lote ?? ''} onChange={(e) => setBci({ prof_lote: num(e) })} placeholder="0,00" />
        </Field>
        <Field label="Área do Terreno (m²)">
          <Input type="number" step="0.01" value={bci.area_terreno ?? ''} onChange={(e) => setBci({ area_terreno: num(e) })} placeholder="187,50" />
        </Field>
        <Field label="Área da Edificação (m²)">
          <Input type="number" step="0.01" value={bci.area_edificacao ?? ''} onChange={(e) => setAreaEdificacao(num(e))} placeholder="53,64" />
        </Field>
        <Field label="Área Total da Edificação (m²)" full>
          <Input type="number" step="0.01" value={bci.area_total_edificacao ?? ''} onChange={(e) => setBci({ area_total_edificacao: num(e) })} placeholder="53,64" />
        </Field>
      </Card>

      {/* 💰 IPTU */}
      <Card icon="💰" title="IPTU" alerta={emDebito ? '⚠️ Em débito' : null}>
        <Field label="Inscrição do Contribuinte">
          <Input value={iptu.inscricao_contribuinte || ''} onChange={(e) => setIptu({ inscricao_contribuinte: e.target.value })} placeholder="7377" />
        </Field>
        <Field label="Exercício de Referência">
          <Input type="number" value={iptu.exercicio ?? ''} onChange={(e) => setIptu({ exercicio: num(e) })} placeholder="2026" />
        </Field>
        <Field label="Valor Anual do IPTU (R$)">
          <Input type="number" step="0.01" value={iptu.valor_anual ?? ''} onChange={(e) => setIptu({ valor_anual: num(e) })} placeholder="0,00" />
        </Field>
        <Field label="Situação do IPTU">
          <Select value={iptu.situacao || ''} onValueChange={(v) => setIptu({ situacao: v })}>
            <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Em dia">Em dia</SelectItem>
              <SelectItem value="Em aberto">Em aberto</SelectItem>
              <SelectItem value="Parcelado">Parcelado</SelectItem>
              <SelectItem value="Isento">Isento</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        {parcelado && (
          <Field label="Nº do Acordo de Parcelamento">
            <Input value={iptu.acordo || ''} onChange={(e) => setIptu({ acordo: e.target.value })} placeholder="2026000987" />
          </Field>
        )}
        <Field label="Vencimento">
          <Input type="date" value={iptu.vencimento || ''} onChange={(e) => setIptu({ vencimento: e.target.value })} />
        </Field>
        <Field label="Débito Total / Valor em Aberto (R$)">
          <Input type="number" step="0.01" value={iptu.debito_total ?? ''} onChange={(e) => setIptu({ debito_total: num(e) })} placeholder="308,24" />
        </Field>
        <Field label="Desconto Concedido (R$)">
          <Input type="number" step="0.01" value={iptu.desconto ?? ''} onChange={(e) => setIptu({ desconto: num(e) })} placeholder="45,58" />
        </Field>
        <Field label="Valor Cobrado / a Pagar (R$)">
          <Input type="number" step="0.01" value={iptu.valor_cobrado ?? ''} onChange={(e) => setIptu({ valor_cobrado: num(e) })} placeholder="262,66" />
        </Field>
        {emDebito && (
          <Field label="Exercícios com Débito" full>
            <Input value={iptu.exercicios_debito || ''} onChange={(e) => setIptu({ exercicios_debito: e.target.value })} placeholder="2021, 2022, 2023, 2024, 2025" />
          </Field>
        )}
      </Card>
    </div>
  );
}
