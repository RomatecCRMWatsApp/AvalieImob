// @module constants/contratoTipos — Fonte ÚNICA dos tipos de contrato.
// Consumido pela listagem (TypeCardGrid) e pela etapa 1 do wizard. Alterar aqui
// reflete nos dois lugares. status: 'disponivel' | 'em_breve'.
import {
  Home, Landmark, ArrowLeftRight, ScrollText, KeyRound, Store, HandHeart,
  Tractor, Wheat, Gift, HandCoins, Handshake, BadgeCheck, Crown, Car, FileX2,
} from 'lucide-react';

export const CONTRATO_CATEGORIAS = ['COMPRA E VENDA', 'LOCAÇÃO', 'IMÓVEL RURAL', 'OUTROS'];

export const CONTRATO_TIPOS = [
  // COMPRA E VENDA
  { id: 'compra_venda',          nome: 'Compra e Venda',        descricao: 'Imóvel urbano',           categoria: 'COMPRA E VENDA', Icon: Home,           status: 'disponivel', verificado: true },
  { id: 'promessa_compra_venda', nome: 'Promessa de C&V',       descricao: 'Compromisso de venda',    categoria: 'COMPRA E VENDA', Icon: Landmark,       status: 'disponivel', verificado: true },
  { id: 'permuta',               nome: 'Permuta',               descricao: 'Troca de bens',           categoria: 'COMPRA E VENDA', Icon: ArrowLeftRight, status: 'disponivel' },
  { id: 'cessao_direitos',       nome: 'Cessão de Direitos',    descricao: 'Direitos sobre imóvel',   categoria: 'COMPRA E VENDA', Icon: ScrollText,     status: 'disponivel' },
  { id: 'compra_venda_veiculo',  nome: 'C&V de Veículo',        descricao: 'Veículo automotor',       categoria: 'COMPRA E VENDA', Icon: Car,            status: 'disponivel' },
  { id: 'doacao',                nome: 'Doação',                descricao: 'Transferência gratuita',  categoria: 'COMPRA E VENDA', Icon: Gift,           status: 'disponivel' },
  // LOCAÇÃO
  { id: 'locacao_residencial',   nome: 'Locação Residencial',   descricao: 'Aluguel residencial',     categoria: 'LOCAÇÃO',        Icon: KeyRound,       status: 'disponivel' },
  { id: 'locacao_comercial',     nome: 'Locação Comercial',     descricao: 'Aluguel comercial',       categoria: 'LOCAÇÃO',        Icon: Store,          status: 'disponivel' },
  { id: 'comodato',              nome: 'Comodato',              descricao: 'Empréstimo de imóvel',    categoria: 'LOCAÇÃO',        Icon: HandHeart,      status: 'disponivel' },
  // IMÓVEL RURAL
  { id: 'parceria_rural',        nome: 'Parceria Rural',        descricao: 'Parceria agrícola',       categoria: 'IMÓVEL RURAL',   Icon: Tractor,        status: 'disponivel' },
  { id: 'arrendamento_rural',    nome: 'Arrendamento Rural',    descricao: 'Arrendamento de terra',   categoria: 'IMÓVEL RURAL',   Icon: Wheat,          status: 'disponivel' },
  // OUTROS
  { id: 'intermediacao',         nome: 'Intermediação',         descricao: 'Corretagem',              categoria: 'OUTROS',         Icon: Handshake,      status: 'disponivel' },
  { id: 'exclusividade',         nome: 'Exclusividade',         descricao: 'Venda com exclusividade', categoria: 'OUTROS',         Icon: BadgeCheck,     status: 'disponivel', verificado: true },
  { id: 'arras',                 nome: 'Arras / Sinal',         descricao: 'Sinal e princípio',       categoria: 'OUTROS',         Icon: HandCoins,      status: 'disponivel' },
  { id: 'usufruto',              nome: 'Usufruto',              descricao: 'Direito de usufruto',     categoria: 'OUTROS',         Icon: Crown,          status: 'disponivel' },
  { id: 'distrato',              nome: 'Distrato',              descricao: 'Desfazimento de contrato',categoria: 'OUTROS',         Icon: FileX2,         status: 'disponivel' },
];

export const contratoTipoLabel = (id) =>
  (CONTRATO_TIPOS.find((t) => t.id === id)?.nome) || id;
