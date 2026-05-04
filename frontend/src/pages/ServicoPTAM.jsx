import React from 'react';
import ServicoTemplate from './ServicoTemplate';

export default function ServicoPTAM() {
  return (
    <ServicoTemplate
      slug="ptam"
      titulo="PTAM — Parecer Técnico de Avaliação Mercadológica"
      subtitulo="Sistema completo para emissão de PTAM conforme NBR 14.653 com IA integrada"
      meta="Emita PTAM (Parecer Técnico de Avaliação Mercadológica) online conforme NBR 14.653 da ABNT. Wizard de 6 etapas, IA especializada e exportação DOCX/PDF. Teste grátis."
      palavrasChave="PTAM, parecer técnico avaliação mercadológica, NBR 14.653, software PTAM online, emitir PTAM, modelo PTAM, PTAM imobiliário"
      hero="Crie PTAMs profissionais em minutos com nosso wizard de 6 etapas, totalmente conforme NBR 14.653 da ABNT. Substitua planilhas e modelos manuais por um sistema inteligente."
      intro={[
        'O Parecer Técnico de Avaliação Mercadológica (PTAM) é o documento oficial que estabelece o valor de mercado de um imóvel, exigido em transações bancárias, ações judiciais, partilhas, divórcios, inventários e operações imobiliárias estratégicas. A emissão correta segue rigorosamente a NBR 14.653 da ABNT, com 7 partes que cobrem desde imóveis urbanos até rurais, semoventes e equipamentos.',
        'O AvalieImob é a plataforma online mais completa do Brasil para emissão de PTAMs. Nosso sistema guia o avaliador através de um wizard de 6 etapas que organiza dados do imóvel, amostras comparativas de mercado, métodos avaliatórios (comparativo direto, da renda, evolutivo, involutivo, capitalização da renda e custo de reprodução) e gera automaticamente um documento profissional em formato DOCX (editável no Microsoft Word) ou PDF, pronto para entrega ao cliente.',
        'Diferente de planilhas Excel ou softwares desktop antigos, o AvalieImob roda 100% no navegador, com sincronização automática, backup em nuvem e integração com IA especializada em NBR 14.653 que ajuda você a tomar decisões em pontos críticos da avaliação — como escolha do método mais adequado, tratamento estatístico de amostras e justificativas técnicas.',
      ]}
      beneficios={[
        { titulo: 'Conformidade total NBR 14.653', descricao: 'Sistema desenvolvido por engenheiro avaliador. Todos os campos seguem a norma ABNT, incluindo grau de fundamentação e precisão.' },
        { titulo: 'IA especializada em avaliação', descricao: 'Assistente de IA treinado na NBR 14.653 ajuda a escolher métodos, justificar escolhas técnicas e revisar o laudo final.' },
        { titulo: 'Wizard guiado de 6 etapas', descricao: 'Da identificação do imóvel até as conclusões finais. Sem deixar nenhum campo crítico de fora.' },
        { titulo: 'Exporta DOCX editável', descricao: 'Receba o PTAM em formato Microsoft Word para personalização final antes de entregar ao cliente. PDF também disponível.' },
        { titulo: 'Múltiplas amostras comparativas', descricao: 'Cadastre quantas amostras de mercado quiser, com homogeneização automática e tratamento estatístico.' },
        { titulo: 'ART/RRT integrada', descricao: 'Campos específicos para Anotação de Responsabilidade Técnica do CREA ou Registro de Responsabilidade Técnica do CAU.' },
      ]}
      comoFunciona={[
        { titulo: 'Crie sua conta gratuita', descricao: 'Cadastro em 30 segundos sem cartão de crédito. Acesso imediato ao sistema.' },
        { titulo: 'Cadastre o imóvel a avaliar', descricao: 'Endereço completo, características físicas, área, padrão construtivo, idade aparente e fotos.' },
        { titulo: 'Adicione amostras de mercado', descricao: 'Imóveis comparáveis com valores e características. O sistema homogeneíza automaticamente seguindo a NBR.' },
        { titulo: 'Escolha o método avaliatório', descricao: 'Sistema sugere o método mais adequado e a IA ajuda a justificar a escolha tecnicamente.' },
        { titulo: 'Gere e exporte o PTAM', descricao: 'Documento DOCX ou PDF profissional pronto para assinatura e entrega ao cliente.' },
        { titulo: 'Assinatura digital opcional', descricao: 'Integração com D4Sign para assinatura digital com validade jurídica plena.' },
      ]}
      publicoAlvo={[
        'Engenheiros civis e arquitetos avaliadores (CREA/CAU)',
        'Corretores de imóveis credenciados (CRECI) que precisam emitir PTAM',
        'Peritos judiciais em ações de avaliação e partilha',
        'Imobiliárias que querem profissionalizar laudos',
        'Bancos e financeiras (avaliação de imóveis-garantia)',
        'Consultores imobiliários e técnicos de avaliação',
      ]}
      faq={[
        { q: 'O que é PTAM exatamente?', a: 'PTAM é a sigla de Parecer Técnico de Avaliação Mercadológica — documento técnico que estabelece o valor de mercado de um bem (geralmente um imóvel) seguindo a metodologia da NBR 14.653 da ABNT. É amplamente aceito por bancos, juízes, cartórios e órgãos públicos.' },
        { q: 'Quem pode emitir um PTAM?', a: 'Engenheiros civis, arquitetos e corretores de imóveis credenciados. Cada categoria tem suas atribuições específicas — engenheiros e arquitetos via ART/RRT no CREA/CAU, corretores via CRECI conforme Resolução COFECI 1.066/2007.' },
        { q: 'PTAM e laudo de avaliação são a mesma coisa?', a: 'São documentos similares mas com finalidades distintas. PTAM é mais técnico, segue rigorosamente a NBR 14.653 e tem maior peso jurídico. Laudo simplificado é uma versão reduzida usada em situações menos formais. Nosso sistema emite ambos.' },
        { q: 'Quanto custa emitir um PTAM no AvalieImob?', a: 'Os planos começam em R$ 49,00/mês (Mensal) com PTAMs ilimitados. Trimestral R$ 139,00 e Anual R$ 499,00. Teste 7 dias grátis sem cartão de crédito.' },
        { q: 'O sistema atende imóveis rurais?', a: 'Sim. Além de imóveis urbanos, temos módulos específicos para imóveis rurais (NBR 14.653-3), semoventes (penhor rural), safras e equipamentos.' },
        { q: 'O PTAM gerado tem validade jurídica?', a: 'Sim, desde que assinado por profissional habilitado (engenheiro/arquiteto com ART/RRT ou corretor com CRECI ativo). Para validade plena recomendamos assinatura digital com certificado ICP-Brasil ou D4Sign integrado.' },
      ]}
      ctaTitulo="Comece a emitir PTAMs profissionais hoje"
      ctaTexto="7 dias grátis. Sem cartão de crédito. Cancele quando quiser. Sistema completo conforme NBR 14.653."
    />
  );
}
