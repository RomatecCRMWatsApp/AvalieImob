import React, { useState } from 'react';
import { Facebook, Instagram, Youtube, Mail, Phone, MapPin, Send } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { useToast } from '../../hooks/use-toast';
import { BRAND } from '../../mock/mock';

const Footer = () => {
  const { toast } = useToast();
  const [form, setForm] = useState({ name: '', email: '', message: '' });

  const submit = (e) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.message) {
      toast({ title: 'Preencha todos os campos', variant: 'destructive' });
      return;
    }
    toast({ title: 'Mensagem enviada!', description: 'Retornaremos em breve.' });
    setForm({ name: '', email: '', message: '' });
  };

  return (
    <footer id="contato" className="bg-emerald-950 text-emerald-50">
      <div className="max-w-7xl mx-auto px-6 py-20">
        <div className="grid lg:grid-cols-2 gap-16 mb-16">
          <div>
            <div className="text-xs font-semibold tracking-[0.2em] text-amber-400 mb-3">CONTATO</div>
            <h2 className="font-display text-4xl md:text-5xl font-bold text-white leading-tight mb-6">
              Fale com a nossa equipe
            </h2>
            <p className="text-emerald-200/90 mb-8 leading-relaxed">
              Tem dúvidas sobre a plataforma? Precisa de um plano personalizado? Entre em contato.
            </p>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center"><Phone className="w-4 h-4" /></div>
                <div>
                  <div className="text-xs text-emerald-300">WhatsApp</div>
                  <div className="text-sm font-semibold text-white">{BRAND.whatsapp}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center"><Mail className="w-4 h-4" /></div>
                <div>
                  <div className="text-xs text-emerald-300">E-mail</div>
                  <div className="text-sm font-semibold text-white">{BRAND.email}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center"><MapPin className="w-4 h-4" /></div>
                <div>
                  <div className="text-xs text-emerald-300">Localização</div>
                  <div className="text-sm font-semibold text-white">{BRAND.location}</div>
                </div>
              </div>
            </div>
          </div>

          <form onSubmit={submit} className="bg-white/5 backdrop-blur rounded-2xl p-8 border border-white/10">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-emerald-100 mb-1.5">Nome</label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-white/10 border-white/20 text-white placeholder:text-emerald-200/50" placeholder="Seu nome" />
              </div>
              <div>
                <label className="block text-sm font-medium text-emerald-100 mb-1.5">E-mail</label>
                <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="bg-white/10 border-white/20 text-white placeholder:text-emerald-200/50" placeholder="voce@email.com" />
              </div>
              <div>
                <label className="block text-sm font-medium text-emerald-100 mb-1.5">Mensagem</label>
                <Textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="bg-white/10 border-white/20 text-white placeholder:text-emerald-200/50 min-h-[120px]" placeholder="Como podemos ajudar?" />
              </div>
              <Button type="submit" className="w-full bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold">
                Enviar mensagem
                <Send className="ml-2 w-4 h-4" />
              </Button>
            </div>
          </form>
        </div>

        <div className="pt-8 border-t border-white/10 flex flex-col md:flex-row gap-6 items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={BRAND.logo} alt="RomaTec" className="h-10 w-10 object-contain bg-white/10 rounded p-1" />
            <div>
              <div className="font-display text-lg font-bold text-white">RomaTec AvalieImob</div>
              <div className="text-xs text-emerald-300">© 2026 — Todos os direitos reservados</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a href="#" className="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"><Facebook className="w-4 h-4" /></a>
            <a href="#" className="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"><Instagram className="w-4 h-4" /></a>
            <a href="#" className="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"><Youtube className="w-4 h-4" /></a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
