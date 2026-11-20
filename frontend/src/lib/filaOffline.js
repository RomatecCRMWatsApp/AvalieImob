// @module filaOffline — fila de vistorias no aparelho (IndexedDB nativo, sem dependência).
//
// Regra: a vistoria é SEMPRE gravada aqui primeiro; o envio vem depois. Cada envio usa
// chaves geradas no aparelho (client_id da vistoria, da foto e da assinatura), então
// repetir o envio após uma falha de rede não duplica nada no servidor.
// Etapas de um item: criar a vistoria → enviar cada foto → enviar a assinatura.
// O progresso fica gravado no próprio item: retomar continua de onde parou.
import { tviAPI } from './api';

const DB_NAME = 'avalieimob-offline';
const DB_VERSION = 2;
const STORE = 'vistorias-pendentes';

function abrir() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'localId' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function tx(modo, fn) {
  const db = await abrir();
  return new Promise((resolve, reject) => {
    const t = db.transaction(STORE, modo);
    const store = t.objectStore(STORE);
    const req = fn(store);
    t.oncomplete = () => { db.close(); resolve(req ? req.result : undefined); };
    t.onerror = () => { db.close(); reject(t.error); };
  });
}

export const novaChave = (prefixo) =>
  `${prefixo}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;

export const listar = () => tx('readonly', (s) => s.getAll()).then((l) => l || []);
export const obter = (localId) => tx('readonly', (s) => s.get(localId));
export const gravar = (item) => tx('readwrite', (s) => s.put(item));
export const remover = (localId) => tx('readwrite', (s) => s.delete(localId));

function avisar() {
  window.dispatchEvent(new Event('avalieimob:fila-mudou'));
}

/** Grava a vistoria na fila (fotos e assinatura como data-URL) e devolve o localId. */
export async function enfileirar({ dados, fotos = [], assinatura = null, assinante = '', clientId }) {
  const item = {
    localId: clientId || novaChave('vist'),
    status: 'pendente',
    criadoEm: new Date().toISOString(),
    dados,
    fotos: fotos.map((f) => (typeof f === 'string' ? { id: novaChave('foto'), dataUrl: f } : f)),
    assinatura: assinatura ? { id: novaChave('ass'), dataUrl: assinatura, assinante } : null,
    progresso: { vistoriaId: null, fotosEnviadas: [], assinaturaEnviada: false },
    tentativas: 0,
    ultimoErro: null,
  };
  await gravar(item);
  avisar();
  return item.localId;
}

function dataUrlParaBlob(dataUrl) {
  const [cab, b64] = dataUrl.split(',');
  const mime = (cab.match(/data:([^;]+)/) || [])[1] || 'image/jpeg';
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

// Erro definitivo (não adianta repetir): 4xx exceto 401/408/429.
function erroDefinitivo(e) {
  const st = e?.response?.status;
  return st >= 400 && st < 500 && ![401, 408, 429].includes(st);
}

function mensagem(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  return e?.message || 'Falha de rede';
}

/** Envia um item, retomando da etapa em que parou. Grava o progresso a cada etapa. */
export async function enviarItem(localId) {
  let item = await obter(localId);
  if (!item || item.status === 'enviado') return item;
  const salvar = async (mudancas) => {
    item = { ...item, ...mudancas, progresso: { ...item.progresso, ...(mudancas.progresso || {}) } };
    await gravar(item);
  };
  try {
    if (!item.progresso.vistoriaId) {
      const v = await tviAPI.create({ ...item.dados, client_id: item.localId });
      await salvar({ progresso: { vistoriaId: v.id, numeroTvi: v.numero_tvi } });
    }
    const vid = item.progresso.vistoriaId;
    for (const foto of item.fotos) {
      if (item.progresso.fotosEnviadas.includes(foto.id)) continue;
      const fd = new FormData();
      fd.append('files', dataUrlParaBlob(foto.dataUrl), `${foto.id}.jpg`);
      fd.append('client_photo_id', foto.id);
      fd.append('ambiente', foto.ambiente || 'Geral');
      if (item.dados.lat && item.dados.lng) {
        fd.append('gps_lat', String(item.dados.lat));
        fd.append('gps_lng', String(item.dados.lng));
      }
      fd.append('timestamp', item.criadoEm);
      await tviAPI.uploadPhotos(vid, fd);
      await salvar({ progresso: { fotosEnviadas: [...item.progresso.fotosEnviadas, foto.id] } });
    }
    if (item.assinatura && !item.progresso.assinaturaEnviada) {
      await tviAPI.saveSignature(vid, item.assinatura.dataUrl, {
        signatario: item.assinatura.assinante || 'Vistoriado',
        clientId: item.assinatura.id,
      });
      await salvar({ progresso: { assinaturaEnviada: true } });
    }
    // Enviado: libera o espaço das fotos no aparelho, mantém o registro do envio.
    await salvar({ status: 'enviado', enviadoEm: new Date().toISOString(), fotos: [],
                   assinatura: null, ultimoErro: null });
  } catch (e) {
    await salvar({
      status: erroDefinitivo(e) ? 'falhou' : 'pendente',
      tentativas: (item.tentativas || 0) + 1,
      ultimoErro: mensagem(e),
    });
  }
  avisar();
  return item;
}

let sincronizando = false;

/** Envia todos os pendentes, um por vez. Ignora chamadas concorrentes. */
export async function sincronizar() {
  if (sincronizando || !navigator.onLine) return;
  sincronizando = true;
  window.dispatchEvent(new Event('avalieimob:fila-sincronizando'));
  try {
    const itens = (await listar()).filter((i) => i.status === 'pendente');
    for (const i of itens) {
      // eslint-disable-next-line no-await-in-loop
      await enviarItem(i.localId);
    }
  } finally {
    sincronizando = false;
    avisar();
  }
}

/** Devolve um item que falhou de vez para a fila (ex.: depois de corrigir o problema). */
export async function tentarDeNovo(localId) {
  const item = await obter(localId);
  if (item) await gravar({ ...item, status: 'pendente' });
  avisar();
  return sincronizar();
}

export const estaSincronizando = () => sincronizando;
