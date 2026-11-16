import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'assinatura-icp-brasil-laudos-contratos-validade-juridica';

export default function BlogPostAssinaturaICP() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Base legal, diferença entre o certificado do profissional e a assinatura do cliente, e como assinar PTAMs, contratos e PDFs avulsos posicionando o carimbo."
      meta={post.meta}
      palavrasChave="assinatura ICP-Brasil, assinatura digital PAdES, MP 2.200-2, Lei 14.063, assinatura eletrônica, certificado digital A1 A3, assinar PTAM, assinar contrato digital, validade jurídica assinatura"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Assinar digitalmente um laudo ou contrato deixou de ser um diferencial e virou requisito de mercado: bancos, cartórios, varas judiciais e clientes esperam documentos com validade jurídica e rastreabilidade. Mas existe muita confusão entre os tipos de assinatura. Neste artigo, explico o que é a assinatura ICP-Brasil, sua base legal e como ela difere da assinatura eletrônica do cliente.' },

        { h2: 'O que é a assinatura ICP-Brasil?' },
        { p: 'É a assinatura digital feita com certificado emitido por uma Autoridade Certificadora credenciada na Infraestrutura de Chaves Públicas Brasileira (ICP-Brasil). Ela usa criptografia para garantir duas coisas: autenticidade (quem assinou é mesmo quem diz ser) e integridade (o documento não foi alterado depois da assinatura).' },
        { p: 'Nos PDFs, o padrão técnico é o PAdES (PDF Advanced Electronic Signatures), que incorpora a assinatura ao próprio arquivo — incluindo o carimbo visual, o hash do documento e a cadeia do certificado.' },

        { h2: 'Base legal' },
        { lista: [
          'MP 2.200-2/2001 — institui a ICP-Brasil e dá presunção de validade às assinaturas feitas com certificado ICP-Brasil (art. 10, §1º)',
          'Lei 14.063/2020 — disciplina o uso de assinaturas eletrônicas (simples, avançada e qualificada) em interações com o poder público',
          'Lei 13.105/2015 (CPC), art. 411 — reconhece a autoria de documento eletrônico assinado digitalmente',
          'Código Civil, art. 219 e 221 — eficácia das declarações de vontade e dos instrumentos particulares',
        ]},
        { callout: 'Pela MP 2.200-2/2001, documentos assinados com certificado ICP-Brasil presumem-se verdadeiros em relação aos signatários. É o nível mais alto de segurança jurídica para um documento eletrônico no Brasil.', calloutTitulo: 'Presunção de autenticidade' },

        { h2: 'ICP-Brasil x assinatura eletrônica do cliente' },
        { p: 'São camadas diferentes e complementares:' },
        { h3: 'Certificado ICP-Brasil (do profissional)' },
        { p: 'É o seu certificado (A1 em arquivo ou A3 em token/cartão). Você o usa para assinar o laudo, o contrato ou a procuração como autor técnico/responsável. Tem presunção legal de autenticidade.' },
        { h3: 'Assinatura eletrônica do cliente (Lei 14.063/2020)' },
        { p: 'É a assinatura do comprador, vendedor ou anuente, coletada por meios eletrônicos — por exemplo, desenhando o traço em um link enviado por WhatsApp, com registro de IP, geolocalização, data/hora e hash do documento (folha de autoria). É uma assinatura eletrônica avançada, válida entre as partes.' },
        { p: 'A ordem importa: primeiro coleta-se a assinatura dos clientes (que carimba o traço no documento) e, por último, o profissional aplica a assinatura ICP-Brasil — que sela o arquivo. Assim a camada ICP-Brasil é a final e não é invalidada por edições posteriores.' },

        { h2: 'O que entra no carimbo de assinatura' },
        { lista: [
          'Nome e CPF do titular do certificado',
          'Autoridade Certificadora emissora e validade do certificado',
          'Data e hora da assinatura',
          'Hash (resumo criptográfico) do documento',
          'QR Code / chave de autenticação para verificação',
        ]},

        { h2: 'Como assinar no AvalieImob' },
        { p: 'O fluxo é o mesmo para PTAMs, contratos, procurações e PDFs avulsos (ART, TRT, ofícios, declarações):' },
        { lista: [
          'Envie ou gere o documento',
          'Abra o assinador e arraste o carimbo para a posição desejada na página',
          'Selecione seu certificado ICP-Brasil (A1) e confirme',
          'O sistema gera o PDF assinado (PAdES) com o carimbo, o hash e o QR de verificação',
          'Baixe, visualize ou reenvie o documento assinado',
        ]},
        { p: 'O módulo de Assinatura de Documentos aceita qualquer PDF — útil para assinar ART/TRT, certidões, declarações e ofícios sem sair da plataforma.' },
        { cta: 'Assine PTAMs, contratos e PDFs avulsos com ICP-Brasil. Teste 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'A assinatura ICP-Brasil dá ao seu laudo ou contrato o maior grau de segurança jurídica disponível no país (MP 2.200-2/2001), enquanto a assinatura eletrônica do cliente (Lei 14.063/2020) formaliza a vontade das partes com rastreabilidade. Usar as duas camadas, na ordem correta, entrega documentos profissionais, verificáveis e prontos para banco, cartório e juízo.' },
      ]}
      servicosRelacionados={[
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'laudo-tecnico', titulo: 'Laudo Técnico de Avaliação' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
