import React from 'react';
import ServicoTemplate from './ServicoTemplate';

export default function ServicoAvaliacaoGarantia() {
  return (
    <ServicoTemplate
      slug="avaliacao-garantia"
      titulo="Avaliação de Garantias Bancárias"
      subtitulo="Laudos de avaliação para garantias hipotecárias, alienação fiduciária e penhor"
      meta="Sistema online para avaliação de garantias bancárias: hipoteca, alienação fiduciária e penhor. Conforme NBR 14.653 e exigências bancárias. Teste grátis 7 dias."
      palavrasChave="avaliação garantia bancária, laudo garantia hipotecária, alienação fiduciária avaliação, penhor avaliação, avaliação para banco, laudo banco do brasil, laudo caixa econômica, avaliador credenciado banco"
      hero="Plataforma profissional para emissão de laudos de avaliação de garantias bancárias. Compatível com exigências de Banco do Brasil, Caixa, Itaú, Bradesco, Santander, Sicredi e cooperativas. Conformidade NBR 14.653 garantida."
      intro={[
        'A avaliação de garantias bancárias é uma das atividades mais demandadas do mercado de avaliação imobiliária. Bancos e instituições financeiras exigem laudos técnicos rigorosos para conceder crédito hipotecário, financiamento imobiliário com alienação fiduciária (Lei 9.514/97), refinanciamento (home equity), capital de giro com garantia real, crédito rural com penhor, e operações estruturadas. O laudo de avaliação é o documento que estabelece o valor do bem dado em garantia e protege tanto o banco quanto o tomador do crédito.',
        'Diferente de uma avaliação comum, a avaliação de garantias bancárias possui particularidades que o AvalieImob trata de forma específica: cálculo do Valor de Mercado e do Valor de Liquidação Forçada (VLF), análise de liquidez e atratividade do imóvel, verificação de matrícula atualizada, certidões negativas (CND), regularidade fundiária, situação cadastral municipal (IPTU/ITR) e ambiental (CAR para imóveis rurais). Tudo organizado em um wizard que cobre exatamente o que cada banco pede.',
        'Nossa plataforma é compatível com os principais bancos do Brasil, com formatos de laudo específicos para Banco do Brasil, Caixa Econômica Federal, Itaú, Bradesco, Santander, Sicredi, Banco do Nordeste, BASA e BNDES. Avaliadores cadastrados em PCA (Programa de Credenciamento de Avaliadores) ou em sistemas próprios dos bancos podem usar nossos modelos como base e personalizar conforme necessário. Cada laudo é assinado digitalmente com validade jurídica plena.',
      ]}
      beneficios={[
        { titulo: 'Modelos por banco', descricao: 'Templates compatíveis com BB, Caixa, Itaú, Bradesco, Santander, Sicredi e demais. Cada modelo segue o formato exigido pela instituição.' },
        { titulo: 'Valor de Liquidação Forçada', descricao: 'Cálculo automático do VLF com base em fatores de liquidez, atratividade e prazo de venda forçada — conforme exigência bancária.' },
        { titulo: 'Análise de regularidade', descricao: 'Checklist de matrícula, certidões, IPTU/ITR, CAR, situação ambiental e jurídica da garantia.' },
        { titulo: 'Reavaliação periódica', descricao: 'Sistema mantém histórico de avaliações para reavaliação de garantias durante a vigência do contrato.' },
        { titulo: 'Hipoteca e alienação fiduciária', descricao: 'Suporte completo para garantia hipotecária (Lei 4.380/64) e alienação fiduciária de imóvel (Lei 9.514/97).' },
        { titulo: 'Assinatura digital ICP-Brasil', descricao: 'Laudo assinado com certificado digital ICP-Brasil ou via D4Sign, com validade jurídica plena.' },
      ]}
      comoFunciona={[
        { titulo: 'Cadastre-se grátis', descricao: 'Acesso ao módulo de avaliação de garantias durante 7 dias de teste. Sem cartão de crédito.' },
        { titulo: 'Selecione o banco/finalidade', descricao: 'Escolha o modelo bancário (BB, Caixa, Itaú, etc.) e o tipo de garantia (hipoteca, alienação, penhor).' },
        { titulo: 'Identifique o imóvel-garantia', descricao: 'Matrícula, IPTU, CAR, dados do proprietário, características físicas e fotos.' },
        { titulo: 'Levante o mercado', descricao: 'Cadastre amostras comparáveis. Sistema calcula valor de mercado pelo método comparativo direto.' },
        { titulo: 'Calcule VLF', descricao: 'Sistema calcula automaticamente o Valor de Liquidação Forçada com base na liquidez do bem.' },
        { titulo: 'Entregue ao banco', descricao: 'Laudo final em PDF assinado digitalmente, pronto para upload no sistema do banco ou envio por e-mail.' },
      ]}
      publicoAlvo={[
        'Avaliadores credenciados PCA — Banco do Brasil',
        'Engenheiros e arquitetos cadastrados em bancos',
        'Corretores credenciados para avaliação bancária',
        'Cooperativas de crédito (Sicredi, Sicoob, Cresol, Unicred)',
        'Bancos de médio porte e financeiras',
        'Empresas de consultoria patrimonial e crédito',
      ]}
      faq={[
        { q: 'O que é Valor de Liquidação Forçada (VLF)?', a: 'É o valor estimado de venda do imóvel em situação de execução forçada (leilão judicial ou extrajudicial), considerando prazo curto de venda e desconto de liquidez. Geralmente representa 60% a 80% do valor de mercado, dependendo do tipo de bem e da região. Bancos usam o VLF como base para calcular o LTV (loan-to-value) máximo do crédito.' },
        { q: 'Sou avaliador credenciado do Banco do Brasil. Posso usar?', a: 'Sim! Nosso modelo BB segue o formato exigido pelo Programa de Credenciamento de Avaliadores (PCA) e pelo sistema interno do banco. Você gera o laudo no AvalieImob e depois faz upload no sistema do BB. Muitos avaliadores PCA usam nossa plataforma para agilizar o trabalho.' },
        { q: 'Tem modelo específico para Caixa Econômica?', a: 'Sim. Temos modelo compatível com as exigências da Caixa para SBPE (financiamento imobiliário) e FGTS, incluindo Mútuo, Apoio à Produção e PMCMV. O laudo segue o padrão Caixa com todos os campos obrigatórios.' },
        { q: 'Avalia para alienação fiduciária?', a: 'Sim. Cobrimos ambas as modalidades: garantia hipotecária (regime tradicional, Lei 4.380/64) e alienação fiduciária de imóvel (Lei 9.514/97 — mais usada em financiamentos imobiliários atuais).' },
        { q: 'Posso usar para garantia rural (penhor agrícola)?', a: 'Sim. Combine este módulo com o módulo de Avaliação Rural para emitir laudos de penhor agrícola (semoventes, safras pendentes, equipamentos), aceitos por BB, Sicredi, Banco do Nordeste e BASA para Pronaf, Pronamp e custeio.' },
        { q: 'O laudo precisa de assinatura digital?', a: 'A maioria dos bancos exige assinatura digital com certificado ICP-Brasil. O AvalieImob integra com D4Sign e suporta certificados A1/A3 do avaliador, garantindo validade jurídica plena e aceitação por todos os bancos.' },
      ]}
      ctaTitulo="Emita laudos de garantia bancária com agilidade"
      ctaTexto="7 dias grátis. Modelos compatíveis com BB, Caixa, Itaú, Bradesco, Santander e cooperativas."
    />
  );
}
