import React from 'react';
import ServicoTemplate from './ServicoTemplate';

export default function ServicoAvaliacaoRural() {
  return (
    <ServicoTemplate
      slug="avaliacao-rural"
      titulo="Avaliação de Imóveis Rurais — NBR 14.653-3"
      subtitulo="Avalie fazendas, sítios, terras nuas, benfeitorias, safras e semoventes (penhor rural)"
      meta="Sistema online para avaliação de imóveis rurais conforme NBR 14.653-3. Avalie fazendas, terras, benfeitorias, semoventes (penhor rural), safras e equipamentos. Teste grátis."
      palavrasChave="avaliação imóvel rural, avaliação fazenda, NBR 14.653-3, avaliação terra nua, penhor rural, avaliação semoventes, laudo agropecuário, avaliação rural online, perícia rural"
      hero="Plataforma especializada em avaliação de imóveis rurais conforme NBR 14.653-3. Da terra nua às benfeitorias, semoventes, safras e equipamentos — tudo em um só lugar, com IA agropecuária integrada."
      intro={[
        'A avaliação de imóveis rurais é uma especialidade que exige conhecimento técnico aprofundado em diversos componentes: terra nua (pastagens, lavouras, reservas legais, áreas de proteção permanente), benfeitorias produtivas (currais, casa-sede, galpões, açudes, cercas), benfeitorias reprodutivas (irrigação, terraços, drenagens), semoventes (gado de corte, leiteiro, equinos, ovinos), safras pendentes e equipamentos agrícolas. Cada elemento tem metodologia própria de avaliação conforme a NBR 14.653-3 da ABNT (Avaliação de Imóveis Rurais).',
        'O AvalieImob é a única plataforma brasileira com módulo completo de avaliação rural seguindo rigorosamente a NBR 14.653-3. Nosso sistema permite avaliar desde uma pequena propriedade familiar até grandes fazendas com milhares de hectares, módulos fiscais, vários tipos de uso do solo (agrícola, pecuário, florestal, extrativista) e centenas de benfeitorias. Tudo organizado em um wizard intuitivo que cobre cada etapa do processo avaliatório.',
        'Recursos exclusivos para avaliação rural incluem: cálculo de valor da terra nua por classes de capacidade de uso (CAR), módulos rurais fiscais por região, depreciação física e funcional de benfeitorias por método Ross-Heidecke, avaliação de rebanhos por categoria animal e função zootécnica (cria, recria, engorda), valoração de safras por produtividade esperada e preços de mercado, e laudo de avaliação para penhor rural conforme exigências do crédito rural bancário (Pronaf, Pronamp, custeio agrícola).',
      ]}
      beneficios={[
        { titulo: 'NBR 14.653-3 completa', descricao: 'Único sistema online que cobre todas as exigências da norma de avaliação rural: terras, benfeitorias, semoventes, safras e equipamentos.' },
        { titulo: 'Múltiplos tipos de uso', descricao: 'Pastagens, lavouras anuais e perenes, reflorestamentos, áreas de preservação, reservas legais, áreas degradadas — tudo contemplado.' },
        { titulo: 'Banco de preços rural', descricao: 'Base de dados regional de preços de terra por estado, com atualização periódica para subsidiar suas avaliações.' },
        { titulo: 'Penhor rural integrado', descricao: 'Módulo específico para garantias do crédito rural bancário (Pronaf, Pronamp, custeio). Compatível com exigências do BB, Sicredi, Banco do Nordeste e BASA.' },
        { titulo: 'IA agropecuária', descricao: 'Assistente especializado em avaliação rural, conhece particularidades de cada bioma, cultura e categoria animal.' },
        { titulo: 'Memorial fotográfico', descricao: 'Organize fotos por benfeitoria, talhão e ponto de referência. Geolocalização integrada para vistoria de campo.' },
      ]}
      comoFunciona={[
        { titulo: 'Cadastro gratuito', descricao: 'Crie sua conta em 30 segundos. Acesso completo ao módulo rural durante o teste grátis.' },
        { titulo: 'Identifique a propriedade', descricao: 'CCIR, CAR, NIRF, área total, módulos fiscais, localização, biomas, classes de capacidade de uso do solo.' },
        { titulo: 'Avalie a terra nua', descricao: 'Sistema calcula valor por hectare conforme uso e capacidade. Use comparáveis regionais ou método de capitalização da renda.' },
        { titulo: 'Cadastre benfeitorias', descricao: 'Casa-sede, galpões, currais, açudes, cercas, irrigação. Cálculo de depreciação física e funcional automático.' },
        { titulo: 'Avalie semoventes/safras', descricao: 'Categorias animais por função, valor unitário e total. Safras por produtividade e preços de mercado.' },
        { titulo: 'Gere o laudo final', descricao: 'PTAM ou laudo simplificado em DOCX/PDF, conforme a finalidade (judicial, bancária, particular, partilha).' },
      ]}
      publicoAlvo={[
        'Engenheiros agrônomos e florestais avaliadores',
        'Engenheiros civis com atuação em meio rural',
        'Peritos judiciais em ações de partilha rural e desapropriação',
        'Corretores de imóveis rurais (CRECI)',
        'Bancos e cooperativas (Pronaf, Pronamp, custeio agrícola)',
        'Empresas de consultoria agropecuária e patrimonial',
      ]}
      faq={[
        { q: 'O que é NBR 14.653-3?', a: 'É a parte 3 da NBR 14.653 da ABNT, que trata especificamente da Avaliação de Imóveis Rurais. Estabelece metodologia para avaliação de terras nuas, benfeitorias, semoventes, safras e equipamentos. É a referência técnica obrigatória para laudos rurais com peso jurídico.' },
        { q: 'Posso avaliar fazendas grandes (mais de 1.000 hectares)?', a: 'Sim. Não há limite de área. Nossa plataforma é usada para avaliação de pequenas propriedades familiares (módulos fiscais únicos) até grandes fazendas com mais de 10 mil hectares, dezenas de talhões e centenas de benfeitorias.' },
        { q: 'O sistema atende exigências de bancos para penhor rural?', a: 'Sim. Temos módulo específico de penhor rural compatível com exigências de Banco do Brasil, Sicredi, Banco do Nordeste, BASA e cooperativas de crédito. O laudo gerado segue o modelo bancário com todos os campos obrigatórios para Pronaf, Pronamp e custeio.' },
        { q: 'Avalia semoventes (gado, equinos)?', a: 'Sim. Módulo completo de avaliação de semoventes com categorias por função zootécnica (cria, recria, engorda, reprodução), faixa etária, raça e valor de mercado. Compatível com penhor rural pecuário.' },
        { q: 'Tem base de preços de terras por região?', a: 'Sim, mantemos uma base de dados regional de preços de terra rural (R$/ha) por estado, classe de uso e capacidade do solo. É um insumo de partida — você sempre deve fazer pesquisa de mercado local para validar.' },
        { q: 'O laudo serve para ações judiciais agrárias?', a: 'Sim. Os laudos do AvalieImob são totalmente compatíveis com perícias judiciais em ações de desapropriação, partilha, divisão, demarcação e indenização rural. Geramos PTAM completo conforme NBR 14.653-3 com toda a fundamentação técnica exigida em juízo.' },
      ]}
      ctaTitulo="Avalie qualquer imóvel rural com precisão técnica"
      ctaTexto="7 dias grátis. NBR 14.653-3 completa. Para engenheiros agrônomos, peritos rurais e bancos."
    />
  );
}
