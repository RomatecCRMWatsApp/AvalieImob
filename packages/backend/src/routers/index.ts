import { router } from "../lib/trpc";
import { authRouter } from "./auth";
import { clienteRouter } from "./cliente";
import { imovelRouter } from "./imovel";
import { amostraRouter } from "./amostra";
import { avaliacaoRouter } from "./avaliacao";
import { audioRouter } from "./audio";
import { calculoRouter } from "./calculo";
import { ptamRouter } from "./ptam";

export const appRouter = router({
  auth: authRouter,
  cliente: clienteRouter,
  imovel: imovelRouter,
  amostra: amostraRouter,
  avaliacao: avaliacaoRouter,
  audio: audioRouter,
  calculo: calculoRouter,
  ptam: ptamRouter,
});

export type AppRouter = typeof appRouter;
