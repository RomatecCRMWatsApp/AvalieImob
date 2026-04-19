import { z } from "zod";
import { router, protectedProcedure } from "../lib/trpc";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq } from "drizzle-orm";
import { ptam_emitidos, avaliacoes, imoveis, clientes, calculos } from "@avaliemob/db/schema";
import { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType, BorderStyle, WidthType, ShadingType } from "docx";
import fs from "fs";
import path from "path";

const border = { style: BorderStyle.SINGLE, size: 1, color: "228B22" };
const borders = { top: border, bottom: border, left: border, right: border };

export const ptamRouter = router({
  gerar: protectedProcedure
    .input(z.object({ avaliacao_id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Buscar avaliação
      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, input.avaliacao_id))
        .limit(1);

      if (avaliacao.length === 0 || avaliacao[0].avaliador_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Avaliação não encontrada ou acesso negado",
        });
      }

      // Buscar imóvel
      const imovel = await db
        .select()
        .from(imoveis)
        .where(eq(imoveis.id, avaliacao[0].imovel_id))
        .limit(1);

      if (imovel.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Imóvel não encontrado",
        });
      }

      // Buscar cálculos
      const resultadoCalculos = await db
        .select()
        .from(calculos)
        .where(eq(calculos.avaliacao_id, input.avaliacao_id));

      if (resultadoCalculos.length === 0) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "Nenhum cálculo encontrado para gerar PTAM",
        });
      }

      const calculo = resultadoCalculos[0];

      try {
        // Gerar DOCX
        const doc = new Document({
          sections: [
            {
              properties: {
                page: {
                  size: {
                    width: 11906,  // A4
                    height: 16838,
                  },
                  margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
                },
              },
              children: [
                // Cabeçalho
                new Paragraph({
                  text: "PARECER TÉCNICO DE AVALIAÇÃO MERCADOLÓGICA",
                  bold: true,
                  alignment: AlignmentType.CENTER,
                  spacing: { after: 200 },
                }),
                new Paragraph({
                  text: `PTAM Nº ${avaliacao[0].numero_ptam}`,
                  bold: true,
                  alignment: AlignmentType.CENTER,
                  spacing: { after: 400 },
                }),

                // Identificação do imóvel
                new Paragraph({
                  text: "IDENTIFICAÇÃO DO IMÓVEL",
                  bold: true,
                  spacing: { before: 200, after: 100 },
                }),
                new Paragraph({
                  children: [
                    new TextRun({
                      text: "Localização: ",
                      bold: true,
                    }),
                    new TextRun(imovel[0].endereco || "Não informado"),
                  ],
                  spacing: { after: 80 },
                }),
                new Paragraph({
                  children: [
                    new TextRun({ text: "Cidade: ", bold: true }),
                    new TextRun(`${imovel[0].cidade} - ${imovel[0].estado}`),
                  ],
                  spacing: { after: 80 },
                }),
                new Paragraph({
                  children: [
                    new TextRun({ text: "Tipo: ", bold: true }),
                    new TextRun(imovel[0].tipo || "Não informado"),
                  ],
                  spacing: { after: 400 },
                }),

                // Finalidade
                new Paragraph({
                  text: "FINALIDADE",
                  bold: true,
                  spacing: { before: 200, after: 100 },
                }),
                new Paragraph({
                  text: avaliacao[0].finalidade || "Parecer técnico de avaliação imobiliária conforme ABNT NBR 14.653",
                  spacing: { after: 400 },
                }),

                // Resultados dos cálculos
                new Paragraph({
                  text: "ANÁLISE MERCADOLÓGICA",
                  bold: true,
                  spacing: { before: 200, after: 100 },
                }),
                new Paragraph({
                  text: `Metodologia: ${avaliacao[0].metodologia?.toUpperCase() || "COMPARATIVO"}`,
                  spacing: { after: 200 },
                }),

                // Tabela de resultados
                new Table({
                  width: { size: 9026, type: WidthType.DXA },
                  columnWidths: [4513, 4513],
                  rows: [
                    new TableRow({
                      children: [
                        new TableCell({
                          borders,
                          shading: { fill: "228B22", type: ShadingType.CLEAR },
                          margins: { top: 80, bottom: 80, left: 120, right: 120 },
                          children: [new Paragraph({ text: "Descrição", bold: true, color: "FFFFFF" })],
                        }),
                        new TableCell({
                          borders,
                          shading: { fill: "228B22", type: ShadingType.CLEAR },
                          margins: { top: 80, bottom: 80, left: 120, right: 120 },
                          children: [new Paragraph({ text: "Valor", bold: true, color: "FFFFFF" })],
                        }),
                      ],
                    }),
                    new TableRow({
                      children: [
                        new TableCell({
                          borders,
                          margins: { top: 80, bottom: 80, left: 120, right: 120 },
                          children: [new Paragraph("Valor Unitário")],
                        }),
                        new TableCell({
                          borders,
                          margins: { top: 80, bottom: 80, left: 120, right: 120 },
                          children: [
                            new Paragraph(
                              `R$ ${parseFloat(calculo.valor_unitario || "0").toLocaleString("pt-BR", {
                                minimumFractionDigits: 2,
                              })}`
                            ),
                          ],
                        }),
                      ],
                    }),
                    new TableRow({
                      children: [
                        new TableCell({
                          borders,
                          margins: { top: 80, bottom: 80, left: 120, right: 120 },
                          children: [new Paragraph("Valor Total Indenizatório")],
                        }),
                        new TableCell({
                          borders,
                          margins: { top: 80, bottom: 80, left: 120, right: 120 },
                          children: [
                            new Paragraph(
                              `R$ ${parseFloat(calculo.valor_total).toLocaleString("pt-BR", {
                                minimumFractionDigits: 2,
                              })}`
                            ),
                          ],
                        }),
                      ],
                    }),
                    ...(calculo.tipo === "comparativo"
                      ? [
                          new TableRow({
                            children: [
                              new TableCell({
                                borders,
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph("Margem de Erro")],
                              }),
                              new TableCell({
                                borders,
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [
                                  new Paragraph(
                                    `${parseFloat(calculo.margem_erro || "0").toFixed(2)}%`
                                  ),
                                ],
                              }),
                            ],
                          }),
                        ]
                      : []),
                  ],
                }),

                new Paragraph({ text: "", spacing: { after: 400 } }),

                // Conclusões
                new Paragraph({
                  text: "CONCLUSÕES",
                  bold: true,
                  spacing: { before: 200, after: 100 },
                }),
                new Paragraph({
                  text: `Conforme análise técnica realizada em conformidade com a Norma Técnica ABNT NBR 14.653, o presente parecer técnico de avaliação mercadológica conclui que o valor do imóvel avaliado é de R$ ${parseFloat(calculo.valor_total).toLocaleString("pt-BR", {
                    minimumFractionDigits: 2,
                  })}.`,
                  spacing: { after: 200 },
                }),

                // Rodapé com data
                new Paragraph({
                  text: `Data da Emissão: ${new Date().toLocaleDateString("pt-BR")}`,
                  spacing: { before: 400, after: 100 },
                }),
                new Paragraph({
                  text: `Avaliador: ${ctx.user!.userId}`,
                }),
              ],
            },
          ],
        });

        // Gerar buffer DOCX
        const buffer = await Packer.toBuffer(doc);

        // Salvar temporariamente
        const ptamId = uuid();
        const docxPath = path.join("/tmp", `ptam-${ptamId}.docx`);
        fs.writeFileSync(docxPath, buffer);

        // Salvar no banco
        await db.insert(ptam_emitidos).values({
          id: ptamId,
          avaliacao_id: input.avaliacao_id,
          numero_ptam: avaliacao[0].numero_ptam!,
          url_docx: `file://${docxPath}`, // Em produção seria S3/Cloudinary
          hash_docx: "hash_placeholder",
          data_emissao: new Date(),
        });

        // Atualizar status da avaliação para emitido
        await db
          .update(avaliacoes)
          .set({ status: "emitido", data_conclusao: new Date() })
          .where(eq(avaliacoes.id, input.avaliacao_id));

        return {
          id: ptamId,
          numero_ptam: avaliacao[0].numero_ptam,
          status: "emitido",
          url_docx: docxPath,
        };
      } catch (error) {
        console.error("Erro ao gerar PTAM:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Erro ao gerar PTAM",
        });
      }
    }),

  listar: protectedProcedure.query(async ({ ctx }) => {
    const db = ctx.req.app.locals.db;

    const result = await db
      .select()
      .from(ptam_emitidos)
      .innerJoin(avaliacoes, eq(ptam_emitidos.avaliacao_id, avaliacoes.id))
      .where(eq(avaliacoes.avaliador_id, ctx.user!.userId));

    return result;
  }),

  obter: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const result = await db
        .select()
        .from(ptam_emitidos)
        .innerJoin(avaliacoes, eq(ptam_emitidos.avaliacao_id, avaliacoes.id))
        .where(eq(ptam_emitidos.id, input.id))
        .limit(1);

      if (result.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "PTAM não encontrado",
        });
      }

      if (result[0].avaliacoes.avaliador_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      return result[0];
    }),
});
