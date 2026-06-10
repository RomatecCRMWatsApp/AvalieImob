// @module pages/admin/CuponsAdmin — Kit Promocional de Captação (cupons + WhatsApp Z-API).
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Tag, Plus, Loader2, Trash2, Copy, Send, Check, X, MessageCircle, Pencil, RefreshCw } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { useToast } from '../../hooks/use-toast';
import { cuponsAPI } from '../../lib/api';

const fmtBRL = (v) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const fmtData = (v) => (v ? String(v).slice(0, 10).split('-').reverse().join('/') : '—');

const STATUS_BADGE = {
  ativo: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  utilizado: 'bg-blue-50 text-blue-700 border-blue-200',
  expirado: 'bg-amber-50 text-amber-700 border-amber-200',
  cancelado: 'bg-gray-100 text-gray-500 border-gray-200',
};

const emptyForm = () => ({
  codigo: '', prefixo_codigo: 'ROMATEC',
  valor_desconto: 20, valor_plano_normal: 89.9,
  nome_destinatario: '', telefone_destinatario: '', email_destinatario: '',
  validade: '', limite_usos: 1,
  usar_padrao: true, mensagem_customizada: '',
});

// Monta o texto do WhatsApp (espelha o template do backend) para o preview ao vivo.
const buildMensagem = (f) => {
  const nome = (f.nome_destinatario || '').trim();
  const saud = nome ? `Olá, ${nome}! 👋\n\n` : 'Olá! 👋\n\n';
  const link = `${window.location.origin}/cadastro?promo=SEU-LINK`;
  const vnorm = Number(f.valor_plano_normal || 89.9);
  const vdesc = Math.max(0, vnorm - Number(f.valor_desconto || 0));
  const val = f.validade ? `\n⏰ *Oferta válida até:* ${fmtData(f.validade)}` : '';
  if (!f.usar_padrao && (f.mensagem_customizada || '').trim()) {
    return `${saud}${f.mensagem_customizada.trim()}\n\n🔗 *Acesse agora:*\n${link}`;
  }
  return `${saud}🎉 *Promoção especial AvalieImob!*\n\nTemos uma oferta exclusiva para você:\n\n` +
    `✅ Sistema profissional de avaliação de imóveis\n✅ Geração de PTAM em PDF\n✅ Banco de amostras de mercado\n✅ Laudos, contratos e muito mais\n\n` +
    `💰 *Plano normal:* ${fmtBRL(vnorm)}/mês\n🏷️ *Sua 1ª mensalidade:* ~${fmtBRL(vnorm)}~ *${fmtBRL(vdesc)}*\n` +
    `💚 *Economia de ${fmtBRL(f.valor_desconto)} na primeira cobrança!*\n(a partir do 2º mês volta ao valor normal)${val}\n\n` +
    `👇 *Cadastre-se agora com seu desconto garantido:*\n${link}\n\n_RomaTec Consultoria Total — Açailândia/MA_`;
};

// Formata *negrito* e ~tachado~ + quebras para o balão.
const renderWa = (texto) => texto.split('\n').map((linha, i) => {
  const parts = [];
  let rest = linha;
  const re = /(\*[^*]+\*|~[^~]+~)/g;
  let last = 0, m;
  while ((m = re.exec(linha))) {
    if (m.index > last) parts.push(linha.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('*')) parts.push(<strong key={`${i}-${m.index}`}>{tok.slice(1, -1)}</strong>);
    else parts.push(<span key={`${i}-${m.index}`} style={{ textDecoration: 'line-through' }}>{tok.slice(1, -1)}</span>);
    last = m.index + tok.length;
  }
  if (last < linha.length) parts.push(linha.slice(last));
  rest = parts.length ? parts : linha;
  return <div key={i} style={{ minHeight: linha === '' ? 8 : undefined }}>{rest}</div>;
});

const WhatsAppPreview = ({ mensagem }) => (
  <div className="rounded-xl overflow-hidden border border-gray-200" style={{ background: '#ECE5DD' }}>
    <div className="flex items-center gap-2 px-3 py-2" style={{ background: '#075E54' }}>
      <span className="w-6 h-6 rounded-full bg-emerald-300 flex items-center justify-center text-emerald-900 text-xs font-bold">R</span>
      <span className="text-white text-sm font-medium">RomaTec AvalieImob</span>
    </div>
    <div className="p-3">
      <div className="bg-white rounded-lg p-3 text-[13px] text-gray-800 shadow-sm max-w-[88%] leading-snug whitespace-pre-wrap break-words">
        {renderWa(mensagem)}
        <div className="text-[10px] text-gray-400 text-right mt-1">14:30 ✓✓</div>
      </div>
    </div>
  </div>
);

const StatCard = ({ label, value, color }) => (
  <div className="bg-white p-5 rounded-xl border border-gray-200">
    <div className="text-xs text-gray-500 mb-1 uppercase tracking-wider">{label}</div>
    <div className={`font-display text-2xl font-bold ${color || 'text-gray-900'}`}>{value}</div>
  </div>
);

const CuponsAdmin = () => {
  const { toast } = useToast();
  const [cupons, setCupons] = useState([]);
  const [stats, setStats] = useState({ ativo: 0, utilizado: 0, expirado: 0, economia_gerada_rs: 0 });
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState('');
  const [statusFiltro, setStatusFiltro] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [sendingId, setSendingId] = useState('');
  const [editingId, setEditingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [lista, est] = await Promise.all([
        cuponsAPI.list(statusFiltro ? { status: statusFiltro } : {}),
        cuponsAPI.estatisticas(),
      ]);
      setCupons(Array.isArray(lista?.cupons) ? lista.cupons : []);
      setStats(est || {});
    } catch (e) {
      toast({ title: 'Erro ao carregar cupons', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setLoading(false); }
  }, [statusFiltro, toast]);
  useEffect(() => { load(); }, [load]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const valor1a = Math.max(0, Number(form.valor_plano_normal || 0) - Number(form.valor_desconto || 0));
  const mensagemPreview = useMemo(() => buildMensagem(form), [form]);

  const filtrados = cupons.filter((c) =>
    !filtro || (c.codigo || '').toLowerCase().includes(filtro.toLowerCase()) ||
    (c.nome_destinatario || '').toLowerCase().includes(filtro.toLowerCase()));

  const criar = async (enviar = false) => {
    setSaving(true);
    try {
      const payload = {
        codigo: form.codigo || undefined,
        prefixo_codigo: form.prefixo_codigo,
        valor_desconto: Number(form.valor_desconto),
        valor_plano_normal: Number(form.valor_plano_normal),
        nome_destinatario: form.nome_destinatario || null,
        telefone_destinatario: form.telefone_destinatario || null,
        email_destinatario: form.email_destinatario || null,
        validade: form.validade || null,
        limite_usos: Number(form.limite_usos) || 1,
        mensagem_customizada: form.usar_padrao ? null : (form.mensagem_customizada || null),
      };
      const salvo = editingId
        ? await cuponsAPI.atualizar(editingId, payload)
        : await cuponsAPI.criar(payload);
      toast({ title: `Cupom ${salvo.codigo} ${editingId ? 'atualizado' : 'criado'}` });
      if (enviar && salvo.telefone_destinatario) {
        await cuponsAPI.enviarWhatsApp(salvo.id, {});
        toast({ title: 'WhatsApp enviado' });
      }
      setOpen(false); setForm(emptyForm()); setEditingId(null);
      load();
    } catch (e) {
      toast({ title: editingId ? 'Erro ao atualizar cupom' : 'Erro ao criar cupom', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  const abrirEdicao = (c) => {
    setForm({
      codigo: c.codigo || '',
      prefixo_codigo: c.prefixo_codigo || 'ROMATEC',
      valor_desconto: c.valor_desconto ?? 20,
      valor_plano_normal: c.valor_plano_normal ?? 89.9,
      nome_destinatario: c.nome_destinatario || '',
      telefone_destinatario: c.telefone_destinatario || '',
      email_destinatario: c.email_destinatario || '',
      validade: c.validade ? String(c.validade).slice(0, 10) : '',
      limite_usos: c.limite_usos ?? 1,
      usar_padrao: !c.mensagem_customizada,
      mensagem_customizada: c.mensagem_customizada || '',
    });
    setEditingId(c.id);
    setOpen(true);
  };

  const revalidar = async (c) => {
    const def = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
    const nova = window.prompt('Revalidar até qual data? (AAAA-MM-DD)', def);
    if (!nova) return;
    try {
      await cuponsAPI.revalidar(c.id, { validade: nova });
      toast({ title: 'Cupom revalidado', description: `Válido até ${nova}` });
      load();
    } catch (e) {
      toast({ title: 'Erro ao revalidar', description: e.response?.data?.detail, variant: 'destructive' });
    }
  };

  const excluir = async (c) => {
    if (!window.confirm(`Excluir o cupom ${c.codigo}? Esta ação não pode ser desfeita.`)) return;
    try {
      await cuponsAPI.excluir(c.id);
      toast({ title: 'Cupom excluído' });
      load();
    } catch (e) {
      toast({ title: 'Erro ao excluir', description: e.response?.data?.detail, variant: 'destructive' });
    }
  };

  const copiarLink = (c) => {
    const url = `${window.location.origin}/cadastro?promo=${c.slug_unico}`;
    navigator.clipboard?.writeText(url);
    toast({ title: 'Link copiado!', description: url });
  };

  const enviar = async (c) => {
    // Sempre pergunta o número (pré-preenche o do destinatário) — permite enviar
    // para o SEU número e testar antes de mandar para o cliente.
    const atual = c.telefone_destinatario || '55';
    const phone = window.prompt('Enviar para qual WhatsApp? (DDI+DDD — use o SEU número para testar antes)', atual);
    if (!phone) return;
    setSendingId(c.id);
    try {
      await cuponsAPI.enviarWhatsApp(c.id, { telefone: phone });
      toast({ title: 'WhatsApp enviado', description: phone });
      load();
    } catch (e) {
      toast({ title: 'Falha no envio', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSendingId(''); }
  };


  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-[#B8860B] flex items-center gap-2"><Tag className="w-7 h-7" /> Cupons Promocionais</h1>
          <p className="text-gray-600 mt-1">Gerencie descontos e links de captação.</p>
        </div>
        <Button onClick={() => { setForm(emptyForm()); setEditingId(null); setOpen(true); }} className="bg-emerald-900 hover:bg-emerald-800 text-white">
          <Plus className="w-4 h-4 mr-2" /> Novo cupom
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Ativos" value={stats.ativo || 0} color="text-emerald-700" />
        <StatCard label="Utilizados" value={stats.utilizado || 0} color="text-blue-700" />
        <StatCard label="Expirados" value={stats.expirado || 0} color="text-amber-600" />
        <StatCard label="Economia gerada" value={fmtBRL(stats.economia_gerada_rs)} color="text-emerald-700" />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={statusFiltro} onChange={(e) => setStatusFiltro(e.target.value)}>
          <option value="">Todos</option>
          <option value="ativo">Ativos</option>
          <option value="utilizado">Utilizados</option>
          <option value="expirado">Expirados</option>
          <option value="cancelado">Cancelados</option>
        </select>
        <Input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="Buscar código ou destinatário..." className="max-w-xs" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {loading ? (
          <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
        ) : (
          <table className="w-full text-sm min-w-[820px]">
            <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
              <tr>
                <th className="text-left py-3 px-4">Código</th>
                <th className="text-left py-3 px-4">Destinatário</th>
                <th className="text-right py-3 px-4">1ª mensalidade</th>
                <th className="text-left py-3 px-4">Status</th>
                <th className="text-left py-3 px-4">Validade</th>
                <th className="text-center py-3 px-4">WhatsApp</th>
                <th className="text-right py-3 px-4">Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((c) => (
                <tr key={c.id} className="border-t border-gray-100 hover:bg-emerald-50/30">
                  <td className="py-3 px-4 font-semibold text-emerald-800">{c.codigo}</td>
                  <td className="py-3 px-4">{c.nome_destinatario || '—'}<div className="text-xs text-gray-400">{c.telefone_destinatario || ''}</div></td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-gray-400 line-through text-xs mr-1">{fmtBRL(c.valor_plano_normal)}</span>
                    <span className="font-bold text-emerald-700">{fmtBRL(c.valor_com_desconto)}</span>
                  </td>
                  <td className="py-3 px-4"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${STATUS_BADGE[c.status] || ''}`}>{c.status}</span></td>
                  <td className="py-3 px-4 text-xs text-gray-500">{c.validade ? fmtData(c.validade) : 'sem validade'}</td>
                  <td className="py-3 px-4 text-center">{c.whatsapp_enviado ? <Check className="w-4 h-4 text-emerald-600 inline" /> : <span className="text-gray-300">—</span>}</td>
                  <td className="py-3 px-2 text-right whitespace-nowrap">
                    <button onClick={() => enviar(c)} disabled={sendingId === c.id} title="Enviar WhatsApp" className="p-1.5 hover:bg-emerald-50 rounded text-emerald-700">
                      {sendingId === c.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                    <button onClick={() => copiarLink(c)} title="Copiar link" className="p-1.5 hover:bg-blue-50 rounded text-blue-600"><Copy className="w-4 h-4" /></button>
                    <button onClick={() => abrirEdicao(c)} title="Editar" className="p-1.5 hover:bg-amber-50 rounded text-amber-600"><Pencil className="w-4 h-4" /></button>
                    {c.status !== 'ativo' && (
                      <button onClick={() => revalidar(c)} title="Revalidar (reativar)" className="p-1.5 hover:bg-emerald-50 rounded text-emerald-700"><RefreshCw className="w-4 h-4" /></button>
                    )}
                    <button onClick={() => excluir(c)} title="Excluir" className="p-1.5 hover:bg-red-50 rounded text-red-600"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
              {filtrados.length === 0 && <tr><td colSpan={7} className="text-center py-10 text-gray-400">Nenhum cupom encontrado</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditingId(null); }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="text-emerald-900 flex items-center gap-2"><Tag className="w-5 h-5" /> {editingId ? 'Editar Cupom' : 'Novo Cupom'}</DialogTitle></DialogHeader>
          <div className="grid md:grid-cols-2 gap-5">
            {/* Form */}
            <div className="space-y-4">
              <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-100 pb-1">Desconto</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600">Código (vazio = automático)</label>
                  <Input value={form.codigo} onChange={(e) => set('codigo', e.target.value.toUpperCase())} placeholder="ROMATEC-A3F9" className="mt-1" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Prefixo</label>
                  <select className="w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded-lg" value={form.prefixo_codigo} onChange={(e) => set('prefixo_codigo', e.target.value)}>
                    {['ROMATEC', 'PROMO', 'VIP', 'INSTA'].map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Desconto (R$)</label>
                  <Input type="number" value={form.valor_desconto} onChange={(e) => set('valor_desconto', e.target.value)} className="mt-1" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Plano normal (R$)</label>
                  <Input type="number" value={form.valor_plano_normal} onChange={(e) => set('valor_plano_normal', e.target.value)} className="mt-1" />
                </div>
              </div>
              <div className="px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200 text-sm">
                1ª mensalidade: <span className="font-bold text-emerald-700">{fmtBRL(valor1a)}</span>
                <span className="text-gray-400"> (depois {fmtBRL(form.valor_plano_normal)}/mês)</span>
              </div>

              <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-100 pb-1">Destinatário (opcional)</div>
              <Input value={form.nome_destinatario} onChange={(e) => set('nome_destinatario', e.target.value)} placeholder="Nome do destinatário" />
              <div className="grid grid-cols-2 gap-3">
                <Input value={form.telefone_destinatario} onChange={(e) => set('telefone_destinatario', e.target.value)} placeholder="(99) 99999-9999" />
                <Input value={form.email_destinatario} onChange={(e) => set('email_destinatario', e.target.value)} placeholder="E-mail" />
              </div>

              <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-100 pb-1">Validade</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600">Válido até (opcional)</label>
                  <Input type="date" value={form.validade} onChange={(e) => set('validade', e.target.value)} className="mt-1" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Limite de usos</label>
                  <Input type="number" min="1" value={form.limite_usos} onChange={(e) => set('limite_usos', e.target.value)} className="mt-1" />
                </div>
              </div>

              <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-100 pb-1">Mensagem</div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.usar_padrao} onChange={(e) => set('usar_padrao', e.target.checked)} /> Usar mensagem padrão
              </label>
              {!form.usar_padrao && (
                <textarea value={form.mensagem_customizada} onChange={(e) => set('mensagem_customizada', e.target.value)} rows={4}
                  placeholder="Mensagem personalizada (o link é adicionado automaticamente)"
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600" />
              )}
            </div>

            {/* Preview */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-1"><MessageCircle className="w-3.5 h-3.5" /> Prévia do WhatsApp</div>
              <WhatsAppPreview mensagem={mensagemPreview} />
              <p className="text-[11px] text-gray-400 mt-2">O link real (com o slug do cupom) substitui "SEU-LINK" no envio.</p>
            </div>
          </div>

          <DialogFooter className="mt-2 gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}><X className="w-4 h-4 mr-1" /> Cancelar</Button>
            <Button onClick={() => criar(false)} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white">{saving ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : null} {editingId ? 'Salvar alterações' : 'Criar cupom'}</Button>
            {form.telefone_destinatario && (
              <Button onClick={() => criar(true)} disabled={saving} className="bg-[#075E54] hover:bg-[#054c44] text-white"><Send className="w-4 h-4 mr-1" /> {editingId ? 'Salvar e enviar' : 'Criar e enviar'}</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CuponsAdmin;
