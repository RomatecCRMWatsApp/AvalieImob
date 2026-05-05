import React, { useState } from 'react';
import { Facebook, Instagram, Youtube, Mail, Phone, MapPin, Send, Globe, MessageCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { useToast } from '../../hooks/use-toast';
import { BRAND } from '../../mock/mock';
import LgpdBadge from '../common/LgpdBadge';

const SPECIALISTS = [
  {
    id: 'jr',
    name: 'Jose Romario P. Bezerra',
    role: 'Diretor Comercial / CEO',
    phone: '(99) 9 9181-1246',
    initials: 'JR',
    avatarColor: 'bg-emerald-600',
    whatsappHref: 'https://wa.me/5599991811246?text=Ol%C3%A1!%20Gostaria%20de%20saber%20mais%20sobre%20o%20AvalieImob',
    telHref: 'tel:+5599991811246',
  },
  {
    id: 'dc',
    name: 'Daniele Cavalcante Vieira',
    role: 'Especialista em Imóveis',
    phone: '(99) 9 9206-2871',
    initials: 'DC',
    avatarColor: 'bg-amber-500',
    whatsappHref: 'https://wa.me/5599992062871?text=Ol%C3%A1!%20Gostaria%20de%20saber%20mais%20sobre%20o%20AvalieImob',
    telHref: 'tel:+5599992062871',
  },
];

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
            <h2 className="font-display text-4xl md:text-5xl font-bold text-white leading-tight mb-4">
              Fale com um Especialista
            </h2>
            <p className="text-emerald-200/90 mb-8 leading-relaxed">
              Selecione um especialista e entre em contato. Nossa equipe está pronta para ajudar com dúvidas sobre planos, funcionalidades e personalizações.
            </p>

            {/* Specialists Cards */}
            <div className="space-y-4 mb-8">
              {SPECIALISTS.map((s) => (
                <div
                  key={s.id}
                  className="bg-white/5 border border-white/10 rounded-2xl p-4 hover:border-emerald-500/40 hover:bg-white/8 transition-all group"
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div
                      className={`w-12 h-12 rounded-full ${s.avatarColor} flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-lg`}
                    >
                      {s.initials}
                    </div>
                    <div>
                      <div className="font-bold text-white text-sm">{s.name}</div>
                      <div className="text-emerald-400 text-xs">{s.role}</div>
                      <div className="text-gray-400 text-xs mt-0.5">{s.phone}</div>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <a
                      href={s.whatsappHref}
                      target="_blank"
                      rel="noreferrer"
                      className="flex-1 text-center bg-[#25D366] hover:bg-[#1fb857] text-white font-semibold py-2 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
                    >
                      <MessageCircle className="w-4 h-4" />
                      WhatsApp
                    </a>
                    <a
                      href={s.telHref}
                      className="flex-1 text-center bg-white/10 hover:bg-white/20 text-white font-semibold py-2 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
                    >
                      <Phone className="w-4 h-4" />
                      Ligar
                    </a>
                  </div>
                </div>
              ))}
            </div>

            {/* Other contacts */}
            <div className="space-y-3">
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
                  <div className="text-xs text-emerald-300">Endereço</div>
                  <div className="text-sm font-semibold text-white">{BRAND.address}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center"><Globe className="w-4 h-4" /></div>
                <div>
                  <div className="text-xs text-emerald-300">Website</div>
                  <a href={`https://${BRAND.website}`} target="_blank" rel="noreferrer" className="text-sm font-semibold text-white hover:text-amber-300">{BRAND.website}</a>
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
          <div className="flex flex-col sm:flex-row items-center gap-4">
            {/* v1: badge LGPD — conformidade com a Lei 13.709/2018 */}
            <LgpdBadge size="md" />
            <div className="flex items-center gap-2 text-xs text-emerald-300">
              <Phone className="w-3.5 h-3.5 text-emerald-400" />
              <span>Jose Romario: (99) 9 9181-1246</span>
              <span className="text-emerald-700">|</span>
              <span>Daniele: (99) 9 9206-2871</span>
            </div>
            <div className="flex items-center gap-3">
              <a href="#" className="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"><Facebook className="w-4 h-4" /></a>
              <a href="#" className="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"><Instagram className="w-4 h-4" /></a>
              <a href="#" className="w-9 h-9 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"><Youtube className="w-4 h-4" /></a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
