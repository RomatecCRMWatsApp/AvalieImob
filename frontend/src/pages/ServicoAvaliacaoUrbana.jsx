import React from 'react';
import ServicoTemplate from './ServicoTemplate';

export default function ServicoAvaliacaoUrbana() {
  return (
    <ServicoTemplate
      slug="avaliacao-urbana"
      titulo="Avaliação de Imóveis Urbanos"
      subtitulo="Avalie casas, apartamentos, terrenos, salas comerciais e galpões conforme NBR 14.653-2"
      meta="Sistema online para avaliação de imóveis urbanos: casas, apartamentos, terrenos, salas comerciais e galpões. Conforme NBR 14.653-2. Wizard, IA e exportação DOCX/PDF. Teste grátis."
      palavrasChave="avaliação imóvel urbano, avaliação casa, avaliação apartamento, avaliação terreno, avaliação sala comercial, NBR 14.653-2, software avaliação imobiliária urbana, valor de mercado imóvel, perícia imobiliária"
      hero="Avalie qualquer imóvel urbano — residencial, comercial ou industrial — com precisão técnica e em conformidade total com a NBR 14.653-2. Wizard guiado, IA especializada e modelos profissionais."
      intro={[
        'A avaliação de imóveis urbanos é a especialidade mais comum entre engenheiros, arquitetos e corretores de imóveis. Ela cobre uma diversidade enorme de tipologias: residenciais (casas, apartamentos, sobrados, kitnets, coberturas), comerciais (lojas, salas, conjuntos comerciais), corporativos (lajes corporativas, andares de edifícios), industriais (galpões, barracões, edifícios industriais), terrenos urbanos (lotes residenciais, comerciais, industriais, glebas para incorporação) e edificações especiais (clínicas, escolas, hotéis, postos de combustível).',
        'O AvalieImob é a plataforma completa para avaliação de imóveis urbanos seguindo rigorosamente a NBR 14.653-2 (parte 2 da norma, específica para Imóveis Urbanos). Nosso sistema cobre todos os métodos avaliatórios previstos na norma: comparativo direto de dados de mercado (o mais usado), capitalização da renda (para imóveis locados), evolutivo (terreno + benfeitorias), involutivo (incorporação imobiliária), custo de reprodução e quantificação de custos. A IA integrada sugere o método mais adequado caso a caso e ajuda na fundamentação técnica.',
        'Nosso wizard cobre toda a metodologia: identificação completa do imóvel (cartorial, fiscal, físico-construtiva), pesquisa de mercado com homogeneização automática de amostras (fatores de transposição, área, padrão, idade, oferta), análise estatística (média, mediana, intervalo de confiança), grau de fundamentação e precisão conforme NBR, e conclusão técnica embasada. Tudo gera um laudo profissional pronto em DOCX (Word) ou PDF — agilidade que multiplica sua produtividade sem comprometer a qualidade técnica.',
      ]}
      beneficios={[
        { titulo: 'NBR 14.653-2 completa', descricao: 'Sistema desenvolvido em conformidade total com a norma de avaliação urbana, incluindo todos os 6 métodos previstos.' },
        { titulo: 'Múltiplas tipologias', descricao: 'Casas, apartamentos, terrenos, salas comerciais, galpões industriais, edifícios corporativos — todas as tipologias urbanas cobertas.' },
        { titulo: 'Homogeneização automática', descricao: 'Aplicação de fatores de transposição, área, padrão, idade, conservação e oferta de forma automatizada e auditável.' },
        { titulo: 'Análise estatística', descricao: 'Cálculo de média, mediana, desvio padrão, intervalo de confiança e saneamento de outliers conforme NBR 14.653.' },
        { titulo: 'Grau de fundamentação', descricao: 'Sistema enquadra automaticamente seu laudo nos graus I, II ou III de fundamentação e precisão da NBR.' },
        { titulo: 'IA especializada', descricao: 'Assistente sugere método mais adequado, fundamenta escolhas técnicas e revisa pontos críticos do laudo.' },
      ]}
      comoFunciona={[
        { titulo: 'Cadastro grátis', descricao: 'Crie sua conta em 30 segundos. Acesso completo durante 7 dias de teste sem cartão.' },
        { titulo: 'Identifique o imóvel', descricao: 'Endereço completo, matrícula, IPTU, áreas (terreno/construída/privativa), padrão, idade, conservação, fotos.' },
        { titulo: 'Pesquise o mercado', descricao: 'Cadastre amostras comparáveis. Sistema homogeneíza valores aplicando fatores conforme NBR 14.653-2.' },
        { titulo: 'Aplique o método', descricao: 'Comparativo direto, capitalização da renda, evolutivo, involutivo, custo de reprodução. IA sugere o melhor.' },
        { titulo: 'Calcule e fundamente', descricao: 'Análise estatística automática, intervalo de confiança, grau de fundamentação e precisão conforme norma.' },
        { titulo: 'Exporte o laudo', descricao: 'DOCX editável (Word) ou PDF profissional, pronto para entrega ao cliente, banco, juiz ou órgão público.' },
      ]}
      publicoAlvo={[
        'Engenheiros civis e arquitetos avaliadores (CREA/CAU)',
        'Corretores de imóveis credenciados (CRECI)',
        'Peritos judiciais em avaliação urbana',
        'Imobiliárias e construtoras',
        'Empresas de avaliação patrimonial e consultoria imobiliária',
        'Profissionais autônomos e técnicos em transações imobiliárias',
      ]}
      faq={[
        { q: 'O que é NBR 14.653-2?', a: 'É a parte 2 da NBR 14.653 da ABNT, dedicada à Avaliação de Imóveis Urbanos. Estabelece a metodologia técnica para avaliar casas, apartamentos, terrenos, salas comerciais, galpões e demais tipologias urbanas. Define os métodos avaliatórios, exigências de pesquisa de mercado, tratamento estatístico e graus de fundamentação e precisão.' },
        { q: 'Quais métodos avaliatórios o sistema cobre?', a: 'Todos os 6 métodos previstos na NBR 14.653-2: (1) comparativo direto de dados de mercado, (2) capitalização da renda, (3) evolutivo, (4) involutivo, (5) custo de reprodução e (6) quantificação de custo. A IA sugere o método mais adequado para cada caso conforme finalidade da avaliação.' },
        { q: 'O que é homogeneização de amostras?', a: 'É o tratamento aplicado às amostras de mercado para torná-las comparáveis ao imóvel avaliando. Inclui fatores como transposição (atualização temporal), oferta (negociação), área, padrão construtivo, idade aparente, conservação, localização e topografia. Nosso sistema aplica todos os fatores automaticamente conforme NBR 14.653-2.' },
        { q: 'O que é grau de fundamentação e precisão?', a: 'A NBR 14.653 classifica os laudos em três graus (I, II e III) conforme a profundidade da pesquisa de mercado, número de variáveis, qualidade das amostras e precisão estatística. Grau III é o mais rigoroso (exigido em ações judiciais complexas) e Grau I é mais simples (uso interno). Nosso sistema enquadra seu laudo automaticamente.' },
        { q: 'Avalia imóveis comerciais grandes (lajes corporativas)?', a: 'Sim. Sistema atende desde uma kitnet até lajes corporativas inteiras, edifícios industriais, shoppings e empreendimentos de grande porte. Para grandes imóveis, geralmente o método mais adequado é a capitalização da renda (com base no fluxo de caixa) ou o evolutivo (terreno + benfeitorias).' },
        { q: 'Posso usar para avaliação judicial?', a: 'Sim. Os laudos do AvalieImob seguem rigorosamente a NBR 14.653-2 e são amplamente aceitos em ações judiciais (partilha, divórcio, inventário, ações possessórias, desapropriação urbana). Para perícia judicial, recomendamos emitir como PTAM completo, com Grau II ou III de fundamentação.' },
      ]}
      ctaTitulo="Avalie qualquer imóvel urbano com precisão"
      ctaTexto="7 dias grátis. NBR 14.653-2 completa. Para casas, apartamentos, terrenos, salas e galpões."
    />
  );
}
