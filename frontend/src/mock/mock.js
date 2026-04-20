// Mock data for RomaTec AvalieImob

export const BRAND = {
  name: 'RomaTec AvalieImob',
  tagline: 'Avalie com precisão. Decida com confiança.',
  subtitle: 'PTAM · LAUDOS · AVALIAÇÕES IMOBILIÁRIAS E GARANTIAS',
  logo: '/brand/logo_principal.png',
  banner: '/brand/banner.png',
  faixa: '/brand/faixa.png',
  address: 'Rua São Raimundo, nº 10 - Centro - Açailândia/MA',
  location: 'Açailândia · Maranhão · Brasil',
  whatsapp: '(99) 99181-1246',
  email: 'contato@romatecavalieimob.com.br',
  email_legacy: 'contato@consultoriaromatec.com.br',
  website: 'www.romatecavalieimob.com.br',
  website_parent: 'www.romatecconsult.com.br',
};

export const FEATURES = [
  { id: 1, icon: 'FileText', title: 'PTAM e Laudos', desc: 'Gere pareceres técnicos e laudos de avaliação com todos os requisitos legais da ABNT NBR 14.653.' },
  { id: 2, icon: 'Brain', title: 'IA para Laudos', desc: 'Aperfeiçoe textos, fundamente decisões e gere análises automáticas com inteligência artificial.' },
  { id: 3, icon: 'Cloud', title: 'Armazenamento na Nuvem', desc: 'Mantenha todas suas avaliações, clientes e documentos em um só lugar, com acesso de qualquer dispositivo.' },
  { id: 4, icon: 'Edit3', title: 'Editor de Laudos', desc: 'Adapte os laudos ao seu estilo e às necessidades específicas de cada trabalho.' },
  { id: 5, icon: 'BadgeCheck', title: 'Laudos Personalizados', desc: 'Personalize laudos com sua marca, logotipo, currículo e assinatura digital.' },
  { id: 6, icon: 'Users', title: 'Cadastro de Clientes', desc: 'Organize seus clientes, imóveis, garantias e histórico em uma base centralizada.' },
  { id: 7, icon: 'ShieldCheck', title: 'Segurança e Privacidade', desc: 'Dados criptografados, conformidade LGPD e níveis de certificação de segurança.' },
  { id: 8, icon: 'Headphones', title: 'Suporte Técnico', desc: 'Equipe especializada pronta para ajudar com dúvidas técnicas e operacionais.' },
];

export const SERVICES = [
  { id: 1, icon: 'Building2', title: 'Imóveis Urbanos', desc: 'Apartamentos, casas, salas comerciais, terrenos urbanos, galpões industriais.', img: 'https://images.pexels.com/photos/14465329/pexels-photo-14465329.jpeg' },
  { id: 2, icon: 'Trees', title: 'Imóveis Rurais', desc: 'Fazendas, sítios, chácaras, glebas, propriedades agropecuárias com benfeitorias.', img: 'https://images.unsplash.com/photo-1742825715166-f23f9ed20e24' },
  { id: 3, icon: 'Wheat', title: 'Grãos e Safra', desc: 'Avaliação de safra agrícola (soja, milho, café) como garantia de crédito rural.', img: 'https://images.unsplash.com/photo-1671308819531-1097d5ab5dcc' },
  { id: 4, icon: 'Beef', title: 'Bovinos e Semoventes', desc: 'Avaliação de rebanho bovino, equino e outros semoventes para garantia bancária.', img: 'https://images.pexels.com/photos/3831159/pexels-photo-3831159.jpeg' },
  { id: 5, icon: 'Factory', title: 'Máquinas e Equipamentos', desc: 'Avaliação de maquinário agrícola, industrial e equipamentos como garantia.', img: 'https://images.pexels.com/photos/7578906/pexels-photo-7578906.jpeg' },
  { id: 6, icon: 'Landmark', title: 'Perícias Judiciais', desc: 'Laudos periciais para ações judiciais, assistência técnica e arbitragens.', img: 'https://images.pexels.com/photos/8469999/pexels-photo-8469999.jpeg' },
];

export const PLANS = [
  { id: 'monthly', name: 'Mensal', price: 89.90, period: 'mês', desc: 'Ideal para testar', features: ['Laudos ilimitados', 'IA para textos (50 usos/mês)', 'Suporte por email', '1 usuário', 'Armazenamento 5GB'], highlight: false },
  { id: 'quarterly', name: 'Trimestral', price: 239.90, period: 'trimestre', saving: 'Economize 11%', desc: 'Mais popular', features: ['Laudos ilimitados', 'IA para textos (200 usos/mês)', 'Suporte prioritário', '3 usuários', 'Armazenamento 25GB', 'Personalização com logo'], highlight: true },
  { id: 'annual', name: 'Anual', price: 849.90, period: 'ano', saving: 'Economize 21%', desc: 'Melhor custo-benefício', features: ['Laudos ilimitados', 'IA para textos (ilimitado)', 'Suporte VIP WhatsApp', 'Até 10 usuários', 'Armazenamento 100GB', 'Personalização total', 'Certificação técnica inclusa', 'Consultoria mensal'], highlight: false },
];

export const TESTIMONIALS = [
  { id: 1, name: 'Carlos Mendes', role: 'Engenheiro Avaliador', crea: 'CREA-MA 12345', text: 'Reduzi o tempo de emissão de laudos em 70%. A IA ajuda muito na fundamentação técnica.', avatar: 'https://images.pexels.com/photos/3831159/pexels-photo-3831159.jpeg' },
  { id: 2, name: 'Ana Paula Santos', role: 'Perita Judicial', crea: 'CRECI-MA 8910', text: 'A organização dos clientes e amostras é excelente. Agora atendo o dobro de trabalhos.', avatar: 'https://images.unsplash.com/photo-1580983218547-8333cb1d76b9' },
  { id: 3, name: 'Roberto Almeida', role: 'Corretor e Avaliador', crea: 'CRECI-MA 4567', text: 'O módulo rural é diferencial. Avalio fazendas e safras com a mesma plataforma.', avatar: 'https://images.pexels.com/photos/7578906/pexels-photo-7578906.jpeg' },
];

export const PARTNERS = ['CASA+ IMÓVEIS', 'SKILL LAUDOS', 'CONSULTRE MA', 'ENG. MARANHÃO', 'CRECI-MA', 'IBAPE'];

// Dashboard mock data
export const MOCK_CLIENTS = [
  { id: 'c1', name: 'Banco do Brasil', type: 'Pessoa Jurídica', doc: '00.000.000/0001-91', phone: '(98) 3221-8000', email: 'pj@bb.com.br', city: 'São Luís', createdAt: '2026-01-15' },
  { id: 'c2', name: 'José da Silva', type: 'Pessoa Física', doc: '123.456.789-00', phone: '(98) 99876-5432', email: 'jose@email.com', city: 'Imperatriz', createdAt: '2026-02-10' },
  { id: 'c3', name: 'Fazenda Três Irmãos Ltda', type: 'Pessoa Jurídica', doc: '11.222.333/0001-44', phone: '(99) 98765-1111', email: 'contato@3irmaos.com', city: 'Balsas', createdAt: '2026-03-05' },
  { id: 'c4', name: 'Maria Oliveira', type: 'Pessoa Física', doc: '987.654.321-00', phone: '(98) 98888-7777', email: 'maria@email.com', city: 'São Luís', createdAt: '2026-04-20' },
];

export const MOCK_PROPERTIES = [
  { id: 'p1', ref: 'APT-001', clientId: 'c2', type: 'Urbano', subtype: 'Apartamento', address: 'Rua das Palmeiras, 450 - Apto 302, Calhau', city: 'São Luís/MA', area: 85, builtArea: 85, value: 380000, status: 'Concluído' },
  { id: 'p2', ref: 'FAZ-002', clientId: 'c3', type: 'Rural', subtype: 'Fazenda', address: 'Rodovia BR-230, Km 45, Zona Rural', city: 'Balsas/MA', area: 2500, builtArea: 450, value: 4500000, status: 'Em andamento' },
  { id: 'p3', ref: 'CAS-003', clientId: 'c4', type: 'Urbano', subtype: 'Casa', address: 'Rua do Sol, 123, Centro', city: 'São Luís/MA', area: 300, builtArea: 220, value: 750000, status: 'Concluído' },
  { id: 'p4', ref: 'SAF-004', clientId: 'c1', type: 'Garantia', subtype: 'Safra de Soja', address: 'Fazenda Cerrado Verde - Safra 2025/26', city: 'Balsas/MA', area: 800, builtArea: 0, value: 2400000, status: 'Em andamento' },
  { id: 'p5', ref: 'BOV-005', clientId: 'c1', type: 'Garantia', subtype: 'Rebanho Bovino', address: 'Fazenda Boi Gordo - 1200 cabeças Nelore', city: 'Imperatriz/MA', area: 0, builtArea: 0, value: 4800000, status: 'Rascunho' },
];

export const MOCK_EVALUATIONS = [
  { id: 'e1', code: 'PTAM-2026-001', propertyId: 'p1', clientId: 'c2', type: 'PTAM', method: 'Comparativo Direto', value: 380000, status: 'Emitido', date: '2026-03-20', samples: 6 },
  { id: 'e2', code: 'LAU-2026-002', propertyId: 'p2', clientId: 'c3', type: 'Laudo', method: 'Evolutivo', value: 4500000, status: 'Em revisão', date: '2026-04-02', samples: 0 },
  { id: 'e3', code: 'PTAM-2026-003', propertyId: 'p3', clientId: 'c4', type: 'PTAM', method: 'Comparativo Direto', value: 750000, status: 'Emitido', date: '2026-04-10', samples: 8 },
  { id: 'e4', code: 'GAR-2026-004', propertyId: 'p4', clientId: 'c1', type: 'Garantia Safra', method: 'Avaliação Agronômica', value: 2400000, status: 'Em andamento', date: '2026-04-15', samples: 0 },
];

export const MOCK_SAMPLES = [
  { id: 's1', ref: 'AM-001', type: 'Apartamento', area: 90, value: 420000, pricePerSqm: 4667, source: 'OLX', date: '2026-03-01', neighborhood: 'Calhau' },
  { id: 's2', ref: 'AM-002', type: 'Apartamento', area: 82, value: 370000, pricePerSqm: 4512, source: 'Zap Imóveis', date: '2026-03-05', neighborhood: 'Calhau' },
  { id: 's3', ref: 'AM-003', type: 'Apartamento', area: 95, value: 450000, pricePerSqm: 4736, source: 'Viva Real', date: '2026-03-10', neighborhood: 'Ponta d\'Areia' },
  { id: 's4', ref: 'AM-004', type: 'Apartamento', area: 78, value: 340000, pricePerSqm: 4358, source: 'Corretor local', date: '2026-03-12', neighborhood: 'Calhau' },
  { id: 's5', ref: 'AM-005', type: 'Apartamento', area: 100, value: 490000, pricePerSqm: 4900, source: 'ImovelWeb', date: '2026-03-15', neighborhood: 'Renascença' },
];

export const DASH_STATS = {
  evaluations: 47,
  clients: 23,
  properties: 38,
  revenue: 48700,
  monthly: [
    { month: 'Jan', count: 3 }, { month: 'Fev', count: 5 }, { month: 'Mar', count: 8 },
    { month: 'Abr', count: 12 }, { month: 'Mai', count: 9 }, { month: 'Jun', count: 10 }
  ]
};
