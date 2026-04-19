import { createTRPCReact } from "@trpc/react-query";
import type { AppRouter } from "@avaliemob/backend/routers";

export const trpc = createTRPCReact<AppRouter>();
