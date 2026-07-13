import React, { useState, useEffect, useCallback } from 'react';
import { instagramAPI } from '../../../lib/api';
import InstagramArt, { gerarPngsDoPost } from './InstagramArt';

const PILARES = [
  { v: 'recursos', label: 'Recursos do sistema' },
  { v: 'autoridade', label: 'Autoridade / educação' },
  { v: 'quanto_vale', label: 'Quanto vale meu imóvel' },
  { v: 'novidades', label: 'Novidades e ofertas' },
];
const FORMATOS = [
  { v: 'post_unico', label: 'Post único' },
  { v: 'carrossel', label: 'Carrossel' },
  { v: 'reel_roteiro', label: 'Roteiro de Reel' },
];
const STATUS_META = {
  ideia:     { label: '💡 Ideia',     cls: 'bg-gray-100 text-gray-700' },
  aprovado:  { label: '✅ Aprovado',  cls: 'bg-blue-100 text-blue-700' },
  publicado: { label: '📤 Publicado', cls: 'bg-green-100 text-green-700' },
};

export default function InstagramStudio() {
  const [pilar, setPilar] = useState('recursos');
  const [formato, setFormato] = useState('post_unico');
  const [assunto, setAssunto] = useState('');
  const [gerando, setGerando] = useState(false);
  const [post, setPost] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [posts, setPosts] = useState([]);
  const [filtroStatus, setFiltroStatus] = useState('');
  const [telefone, setTelefone] = useState(() => {
    try { return localStorage.getItem('ig_wpp') || ''; } catch (e) { return ''; }
  });
  const [enviando, setEnviando] = useState(false);
  const [msgOk, setMsgOk] = useState('');

  const carregar = useCallback(async () => {
    const params = {};
    if (filtroStatus) params.status = filtroStatus;
    setPosts(await instagramAPI.listar(params));
  }, [filtroStatus]);

  useEffect(() => { carregar(); }, [carregar]);

  const gerar = async () => {
    setErro(''); setGerando(true);
    try {
      const out = await instagramAPI.gerar(pilar, assunto, formato);
      setPost({ ...out, template_arte: 'impacto', status: 'ideia' });
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Falha ao gerar. Tente novamente.');
    } finally { setGerando(false); }
  };

  const salvar = async () => {
    if (!post) return;
    setSalvando(true);
    try {
      const salvo = post.id
        ? await instagramAPI.atualizar(post.id, post)
        : await instagramAPI.criar(post);
      setPost({ ...salvo });
      carregar();
    } finally { setSalvando(false); }
  };

  const mudarStatus = async (id, status) => { await instagramAPI.status(id, status); carregar(); };
  const excluir = async (id) => {
    if (!window.confirm('Excluir este post?')) return;
    await instagramAPI.excluir(id); carregar();
  };

  const upd = (campo, val) => setPost(p => ({ ...p, [campo]: val }));

  const enviarWhatsapp = async (alvo, imagensPre) => {
    if (!alvo) return;
    if (!alvo.id) { setErro('Salve o post antes de enviar pro WhatsApp.'); return; }
    const tel = (telefone || '').trim();
    if (!tel) { setErro('Preencha "Meu WhatsApp" no topo para o envio.'); return; }
    setErro(''); setEnviando(true);
    try {
      const imagens = imagensPre || await gerarPngsDoPost(alvo);
      const r = await instagramAPI.enviarWhatsapp(alvo.id, { phone: tel, imagens });
      setMsgOk(`Enviado pro seu WhatsApp ✓ (${(r && r.enviadas) || imagens.length} imagem/ns)`);
      setTimeout(() => setMsgOk(''), 6000);
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Falha ao enviar pelo WhatsApp.');
    } finally { setEnviando(false); }
  };

  const aprovarEEnviar = async (p) => {
    await instagramAPI.status(p.id, 'aprovado');
    await carregar();
    if ((telefone || '').trim()) await enviarWhatsapp(p);
  };

  return (
    <div className="p-4 md:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0C3320]">Instagram Studio</h1>
        <p className="text-gray-500 mt-1">Gere posts para @avalieimob e organize o calendário.</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <label className="text-sm text-gray-600">Meu WhatsApp (envio automático ao aprovar):</label>
          <input className="border rounded p-1 text-sm w-48"
                 value={telefone}
                 onChange={e => { setTelefone(e.target.value); try { localStorage.setItem('ig_wpp', e.target.value); } catch (err) { /* ignore */ } }}
                 placeholder="5599999999999" />
        </div>
        {msgOk && <p className="text-green-600 text-sm mt-1">{msgOk}</p>}
      </div>

      {/* GERADOR */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <div className="grid md:grid-cols-3 gap-3">
          <label className="text-sm">Pilar
            <select className="w-full border rounded p-2 mt-1" value={pilar} onChange={e => setPilar(e.target.value)}>
              {PILARES.map(p => <option key={p.v} value={p.v}>{p.label}</option>)}
            </select>
          </label>
          <label className="text-sm">Formato
            <select className="w-full border rounded p-2 mt-1" value={formato} onChange={e => setFormato(e.target.value)}>
              {FORMATOS.map(f => <option key={f.v} value={f.v}>{f.label}</option>)}
            </select>
          </label>
          <label className="text-sm">Assunto (opcional)
            <input className="w-full border rounded p-2 mt-1" value={assunto}
                   onChange={e => setAssunto(e.target.value)} placeholder="ex.: assinatura ICP" />
          </label>
        </div>
        <button onClick={gerar} disabled={gerando}
                className="bg-[#0C3320] text-white rounded px-4 py-2 disabled:opacity-50">
          {gerando ? 'Gerando…' : 'Gerar com IA'}
        </button>
        {erro && <p className="text-red-600 text-sm">{erro}</p>}
      </div>

      {/* EDIÇÃO */}
      {post && (
        <div className="bg-white rounded-xl border p-4 space-y-3">
          <input className="w-full border rounded p-2 font-semibold" value={post.titulo || ''}
                 onChange={e => upd('titulo', e.target.value)} placeholder="Título" />
          <textarea className="w-full border rounded p-2 h-40" value={post.legenda || ''}
                    onChange={e => upd('legenda', e.target.value)} placeholder="Legenda" />
          {post.formato === 'reel_roteiro' && (
            <textarea className="w-full border rounded p-2 h-32" value={post.roteiro || ''}
                      onChange={e => upd('roteiro', e.target.value)} placeholder="Roteiro do Reel" />
          )}
          {post.formato === 'carrossel' && (
            <div className="space-y-2">
              {(post.slides || []).map((s, i) => (
                <div key={i} className="border rounded p-2">
                  <input className="w-full border rounded p-1 mb-1 text-sm font-medium"
                         value={s.titulo || ''} placeholder={`Slide ${i + 1} — título`}
                         onChange={e => upd('slides', post.slides.map((x, j) => j === i ? { ...x, titulo: e.target.value } : x))} />
                  <textarea className="w-full border rounded p-1 text-sm"
                            value={s.texto || ''} placeholder="Texto do slide"
                            onChange={e => upd('slides', post.slides.map((x, j) => j === i ? { ...x, texto: e.target.value } : x))} />
                </div>
              ))}
            </div>
          )}
          <input className="w-full border rounded p-2 text-sm" value={(post.hashtags || []).join(' ')}
                 onChange={e => upd('hashtags', e.target.value.split(/\s+/).filter(Boolean))}
                 placeholder="#hashtags separadas por espaço" />
          <button onClick={salvar} disabled={salvando}
                  className="bg-[#C9A84C] text-[#0C3320] font-semibold rounded px-4 py-2 disabled:opacity-50">
            {salvando ? 'Salvando…' : 'Salvar no calendário'}
          </button>
          <InstagramArt post={post} onEnviarWhatsapp={(imgs) => enviarWhatsapp(post, imgs)} enviando={enviando} />
        </div>
      )}

      {/* CALENDÁRIO */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-[#0C3320]">Calendário editorial</h2>
          <select className="border rounded p-1 text-sm" value={filtroStatus}
                  onChange={e => setFiltroStatus(e.target.value)}>
            <option value="">Todos</option>
            <option value="ideia">Ideia</option>
            <option value="aprovado">Aprovado</option>
            <option value="publicado">Publicado</option>
          </select>
        </div>
        {posts.length === 0 && <p className="text-gray-400 text-sm">Nenhum post ainda.</p>}
        {posts.map(p => (
          <div key={p.id} className="border rounded-lg p-3 flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded ${STATUS_META[p.status]?.cls}`}>
                  {STATUS_META[p.status]?.label}
                </span>
                <span className="text-xs text-gray-400">{p.pilar}</span>
              </div>
              <p className="font-medium truncate mt-1">{p.titulo || '(sem título)'}</p>
              <p className="text-sm text-gray-500 line-clamp-2">{p.legenda}</p>
            </div>
            <div className="flex flex-col gap-1 shrink-0">
              <button onClick={() => setPost(p)} className="text-xs text-[#0C3320] font-medium">Abrir</button>
              {p.status === 'ideia' &&
                <button onClick={() => aprovarEEnviar(p)} className="text-xs text-blue-600">Aprovar + enviar</button>}
              {p.status === 'aprovado' &&
                <button onClick={() => mudarStatus(p.id, 'publicado')} className="text-xs text-green-600">Marcar publicado</button>}
              <button onClick={() => excluir(p.id)} className="text-xs text-red-500">Excluir</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
