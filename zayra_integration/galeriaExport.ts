// src/routes/galeriaExport.ts  (lado ZAYRA — Node 22 + TS + Express + MySQL2)
//
// Endpoint de exportação da Galeria para o AvalieImob.
// Auth: service-to-service via X-API-Key (requireApiKey), NÃO o JWT do usuário.
// A identidade do avaliador chega pela query `user` (e-mail) e é resolvida no MySQL.
//
// ⚠️ SUPOSIÇÕES DE SCHEMA — confirme com `DESCRIBE` antes de subir:
//    - Tabela de usuários: `users` com colunas `id` e `email`.
//    - Tabela de fotos: `fotos_galeria` com:
//        id, numero, url, latitude, longitude, endereco, data_hora, legenda,
//        sincronizada (TINYINT 1/0), user_id
//   Se os nomes reais diferirem, ajuste o SQL/o mapeamento abaixo.
import { Router, Request, Response } from 'express'
import { pool } from '../database'           // ajuste o caminho ao seu pool MySQL2
import { requireApiKey } from '../middleware/requireApiKey'

const router = Router()

/**
 * GET /api/galeria/export
 * Headers: X-API-Key: <AVALIEIMOB_API_KEY>
 * Query:
 *   user   (obrigatório) — e-mail do avaliador, resolve o user_id no ZAYRA
 *   limit  (default 50, max 200)
 *   offset (default 0)
 *   desde  (ISO date) — apenas fotos após esta data
 */
router.get('/export', requireApiKey, async (req: Request, res: Response) => {
  const userEmail = (req.query.user as string | undefined)?.trim()
  if (!userEmail) {
    return res.status(400).json({ error: 'parâmetro "user" (e-mail) é obrigatório' })
  }

  const limit = Math.min(parseInt(req.query.limit as string) || 50, 200)
  const offset = parseInt(req.query.offset as string) || 0
  const desde = req.query.desde as string | undefined

  try {
    // 1. Resolve o user_id do avaliador a partir do e-mail.
    const [userRows] = await pool.query(
      'SELECT id FROM users WHERE email = ? LIMIT 1',
      [userEmail]
    )
    const users = userRows as Array<{ id: number | string }>
    if (users.length === 0) {
      // Avaliador não tem conta no ZAYRA: devolve lista vazia (não é erro).
      return res.json({ fotos: [], total: 0, limit, offset })
    }
    const userId = users[0].id

    // 2. Busca as fotos sincronizadas desse usuário.
    let sql = `
      SELECT id, numero, url, latitude, longitude, endereco, data_hora, legenda, sincronizada
      FROM fotos_galeria
      WHERE user_id = ? AND sincronizada = 1
    `
    const params: unknown[] = [userId]

    if (desde) {
      sql += ' AND data_hora >= ?'
      params.push(desde)
    }
    sql += ' ORDER BY data_hora DESC LIMIT ? OFFSET ?'
    params.push(limit, offset)

    const [rows] = await pool.query(sql, params)
    const fotos = rows as unknown[]

    return res.json({ fotos, total: fotos.length, limit, offset })
  } catch (err) {
    console.error('[galeriaExport] erro:', err)
    return res.status(500).json({ error: 'falha ao exportar galeria' })
  }
})

export default router
