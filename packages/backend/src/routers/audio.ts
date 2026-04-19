import { z } from "zod";
import { router, protectedProcedure } from "../lib/trpc";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq } from "drizzle-orm";
import { audio_transcricoes, avaliacoes } from "@avaliemob/db/schema";
import { OpenAI } from "openai";
import fs from "fs";
import path from "path";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export const audioRouter = router({
  transcrever: protectedProcedure
    .input(
      z.object({
        avaliacao_id: z.string(),
        arquivo_base64: z.string(),
        tipo: z
          .enum(["descricao_imovel", "condicoes_mercado", "observacoes"])
          .default("descricao_imovel"),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Verificar se avaliação pertence ao usuário
      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, input.avaliacao_id))
        .limit(1);

      if (
        avaliacao.length === 0 ||
        avaliacao[0].avaliador_id !== ctx.user!.userId
      ) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Avaliação não encontrada ou acesso negado",
        });
      }

      try {
        // Decodificar base64 e salvar temporariamente
        const buffer = Buffer.from(input.arquivo_base64, "base64");
        const tempPath = path.join("/tmp", `audio-${uuid()}.webm`);
        fs.writeFileSync(tempPath, buffer);

        // Transcrever com Whisper
        const transcript = await openai.audio.transcriptions.create({
          file: fs.createReadStream(tempPath),
          model: "whisper-1",
          language: "pt",
        });

        // Deletar arquivo temporário
        fs.unlinkSync(tempPath);

        const audioId = uuid();

        // Salvar transcrição no banco
        await db.insert(audio_transcricoes).values({
          id: audioId,
          avaliacao_id: input.avaliacao_id,
          arquivo_url: null, // Você pode adicionar S3 depois
          duracao_segundos: null,
          transcricao_texto: transcript.text,
          confianca: "0.95", // Whisper não retorna confiança, usar padrão
          idioma: "pt-BR",
          tipo: input.tipo,
        });

        return {
          id: audioId,
          transcricao: transcript.text,
        };
      } catch (error) {
        console.error("Erro ao transcrever áudio:", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Erro ao transcrever áudio",
        });
      }
    }),

  listarPorAvaliacao: protectedProcedure
    .input(z.object({ avaliacao_id: z.string() }))
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, input.avaliacao_id))
        .limit(1);

      if (
        avaliacao.length === 0 ||
        avaliacao[0].avaliador_id !== ctx.user!.userId
      ) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      const result = await db
        .select()
        .from(audio_transcricoes)
        .where(eq(audio_transcricoes.avaliacao_id, input.avaliacao_id));

      return result;
    }),

  deletar: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const audio = await db
        .select()
        .from(audio_transcricoes)
        .where(eq(audio_transcricoes.id, input.id))
        .limit(1);

      if (audio.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Áudio não encontrado",
        });
      }

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, audio[0].avaliacao_id!))
        .limit(1);

      if (
        avaliacao.length === 0 ||
        avaliacao[0].avaliador_id !== ctx.user!.userId
      ) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db
        .delete(audio_transcricoes)
        .where(eq(audio_transcricoes.id, input.id));

      return { success: true };
    }),
});
