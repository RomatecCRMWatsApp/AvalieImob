// Middleware de autenticação service-to-service para a integração AvalieImob → ZAYRA.
// O AvalieImob chama o ZAYRA com o header X-API-Key. NÃO usa o JWT do usuário final
// (os dois sistemas têm segredos próprios). A identidade do avaliador vem por query.
//
// Env esperada no ZAYRA:
//   AVALIEIMOB_API_KEY=<mesma chave configurada como ZAYRA_API_KEY no AvalieImob>
import { Request, Response, NextFunction } from 'express'

export function requireApiKey(req: Request, res: Response, next: NextFunction): void {
  const expected = process.env.AVALIEIMOB_API_KEY || ''
  const provided = (req.header('x-api-key') || '').trim()

  if (!expected) {
    res.status(500).json({ error: 'AVALIEIMOB_API_KEY não configurada no ZAYRA' })
    return
  }
  // Comparação de tamanho constante evita timing attack básico.
  if (provided.length !== expected.length || !timingSafeEqual(provided, expected)) {
    res.status(401).json({ error: 'API key inválida' })
    return
  }
  next()
}

function timingSafeEqual(a: string, b: string): boolean {
  let diff = 0
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  return diff === 0
}
