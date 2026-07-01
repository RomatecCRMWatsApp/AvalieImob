// @page ComoAssinar — guia didático público (/como-assinar) enviado junto do link
// de assinatura no WhatsApp. GENÉRICO: sem nome/CPF/dados reais (é cacheável e vai em
// aberto pelo WhatsApp). Identidade herdada do sistema: BrandMark (o "A"), verde/dourado
// da marca e as fontes globais (Playfair via .font-display, Inter no corpo); fontes
// manuscritas self-hosted (/fonts/assinatura).
import React, { useEffect } from 'react';
import { BrandMark } from '../components/brand/BrandMark';

const GREEN = '#0C3320';   // verde da marca (mesma constante usada em todo o app)
const GOLD = '#C9A84C';    // dourado da marca
const FONTES = [
  { id: 'DancingScript', label: 'Dancing Script' },
  { id: 'GreatVibes', label: 'Great Vibes' },
  { id: 'Allura', label: 'Allura' },
];
const FONT_FACE_CSS = ['DancingScript', 'GreatVibes', 'Allura', 'Sacramento', 'Pacifico', 'HomemadeApple']
  .map((f) => `@font-face{font-family:'${f}';src:url('/fonts/assinatura/${f}-Regular.ttf') format('truetype');font-display:swap;}`).join('');

const PASSOS = [
  { n: '1', titulo: 'Abra o link', texto: 'Você recebe uma mensagem no WhatsApp. Toque no link em azul para abrir a página de assinatura.' },
  { n: '2', titulo: 'Confira o documento', texto: 'A página abre mostrando o documento. Leia e confira se o seu nome e os dados do imóvel estão certos.' },
  { n: '3', titulo: 'Digite seu nome', texto: 'Escreva seu nome completo, do jeito que consta no seu documento.' },
  { n: '4', titulo: 'Digite seu CPF', texto: 'Informe seu CPF. O sistema confere na hora — quando aparecer o ✓ verde, está certo.' },
  { n: '5', titulo: 'Escolha como assinar', texto: 'Você decide: Digitar seu nome e escolher um estilo de letra, ou Desenhar a assinatura com o dedo.' },
  { n: '6', titulo: 'Escolha o estilo da letra', texto: 'No modo Digitar, toque em um dos estilos. Seu nome aparece na hora — escolha o que mais parece com a sua assinatura.' },
  { n: '7', titulo: 'Toque em assinar', texto: 'Confira tudo e toque no botão Assinar documento. Sua assinatura é registrada com segurança.' },
];

// Mock visual por passo (genérico, sem dados reais)
function Mock({ n }) {
  const box = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 12, boxShadow: '0 1px 2px rgba(0,0,0,.05)' };
  if (n === '1') return (
    <div style={{ ...box, background: '#dcf8c6', border: 'none', borderRadius: '14px 14px 14px 4px', maxWidth: 280 }}>
      <div style={{ fontSize: 13, color: '#111' }}>Olá! Segue o link para você assinar seu documento:</div>
      <div style={{ fontSize: 13, color: '#1d70b8', textDecoration: 'underline', wordBreak: 'break-all', marginTop: 4 }}>romatecavalieimob.com.br/assinar‑geo/…</div>
    </div>
  );
  if (n === '2') return (
    <div style={box}>
      <div style={{ fontWeight: 700, color: GREEN, fontSize: 13 }}>REQUERIMENTO DE USUCAPIÃO</div>
      <div style={{ height: 6, background: '#f1f5f9', borderRadius: 4, margin: '8px 0' }} />
      <div style={{ height: 6, background: '#f1f5f9', borderRadius: 4, width: '80%', marginBottom: 8 }} />
      <div style={{ fontSize: 11, color: '#64748b' }}>Responsável Técnico — CFT/MA 01209185369</div>
    </div>
  );
  if (n === '3') return (
    <div style={box}>
      <div style={{ fontSize: 12, color: '#334155', fontWeight: 600, marginBottom: 4 }}>Nome completo</div>
      <div style={{ border: '1px solid #cbd5e1', borderRadius: 8, padding: '8px 10px', color: '#94a3b8', fontSize: 14 }}>seu nome completo</div>
    </div>
  );
  if (n === '4') return (
    <div style={box}>
      <div style={{ fontSize: 12, color: '#334155', fontWeight: 600, marginBottom: 4 }}>CPF</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, border: `1px solid ${GREEN}`, borderRadius: 8, padding: '8px 10px' }}>
        <span style={{ color: '#334155', fontSize: 14 }}>000.000.000-00</span>
        <span style={{ marginLeft: 'auto', color: '#16a34a', fontWeight: 800 }}>✓</span>
      </div>
    </div>
  );
  if (n === '5') return (
    <div style={{ display: 'flex', border: `1px solid ${GREEN}33`, borderRadius: 10, overflow: 'hidden', maxWidth: 260 }}>
      <div style={{ flex: 1, textAlign: 'center', padding: 10, background: GREEN, color: '#fff', fontWeight: 700, fontSize: 13 }}>Digitar</div>
      <div style={{ flex: 1, textAlign: 'center', padding: 10, background: '#fff', color: GREEN, fontWeight: 600, fontSize: 13 }}>Desenhar</div>
    </div>
  );
  if (n === '6') return (
    <div style={{ display: 'grid', gap: 8 }}>
      {FONTES.map((f, i) => (
        <div key={f.id} style={{ padding: '6px 14px', borderRadius: 10, background: '#fff', border: i === 0 ? `2px solid ${GOLD}` : '1px solid #e2e8f0', boxShadow: i === 0 ? `0 0 0 3px ${GOLD}33` : 'none' }}>
          <span style={{ fontFamily: f.id, fontSize: 26, color: GREEN }}>Sua Assinatura</span>
        </div>
      ))}
    </div>
  );
  if (n === '7') return (
    <div style={{ background: GREEN, color: '#fff', textAlign: 'center', padding: '12px', borderRadius: 10, fontWeight: 700, maxWidth: 260 }}>Assinar documento</div>
  );
  return null;
}

export default function ComoAssinar() {
  useEffect(() => {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('[data-step]').forEach((s) => s.classList.add('in'));
      return;
    }
    const obs = new IntersectionObserver((es) => {
      es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); obs.unobserve(e.target); } });
    }, { threshold: 0.14 });
    document.querySelectorAll('[data-step]').forEach((s) => obs.observe(s));
    return () => obs.disconnect();
  }, []);

  return (
    <main style={{ maxWidth: 460, margin: '0 auto', padding: '0 20px 64px', color: '#0f172a' }}>
      <style>{`${FONT_FACE_CSS}
        [data-step]{opacity:0;transform:translateY(14px);transition:opacity .5s ease,transform .5s ease;}
        [data-step].in{opacity:1;transform:none;}
        .como-focus:focus-visible{outline:3px solid ${GOLD};outline-offset:2px;border-radius:10px;}
        @media (prefers-reduced-motion: reduce){[data-step]{transition:none;}}`}</style>

      <header style={{ paddingTop: 40, paddingBottom: 24, textAlign: 'center' }}>
        <div style={{ width: 'fit-content', margin: '0 auto 18px' }}><BrandMark size={64} variant="badge" /></div>
        <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#64748b' }}>Romatec · AvalieImob</p>
        <h1 className="font-display" style={{ fontSize: 30, fontWeight: 800, lineHeight: 1.15, margin: '10px 0 0', color: GREEN }}>Como assinar seu documento</h1>
        <p style={{ color: '#475569', fontSize: 14, marginTop: 12 }}>Você recebeu um link para assinar. É rápido, seguro e feito pelo próprio celular.</p>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        {PASSOS.map((p) => (
          <section key={p.n} data-step style={{ background: 'white', borderRadius: 16, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,.06)', border: '1px solid #eef2f6' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ flexShrink: 0, width: 30, height: 30, borderRadius: '50%', background: GREEN, color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 800, fontSize: 14 }}>{p.n}</span>
              <h2 className="font-display" style={{ fontSize: 18, fontWeight: 700, color: GREEN, margin: 0 }}>{p.titulo}</h2>
            </div>
            <p style={{ fontSize: 14, color: '#475569', margin: '0 0 12px', lineHeight: 1.5 }}>{p.texto}</p>
            <Mock n={p.n} />
          </section>
        ))}

        {/* Confirmação — selo */}
        <section data-step style={{ textAlign: 'center', background: GREEN, color: '#fff', borderRadius: 16, padding: 22 }}>
          <div style={{ width: 56, height: 56, margin: '0 auto 10px', borderRadius: '50%', border: `3px solid ${GOLD}`, display: 'grid', placeItems: 'center', fontSize: 30 }}>✓</div>
          <div className="font-display" style={{ fontSize: 20, fontWeight: 800 }}>Pronto! Assinatura registrada</div>
          <p style={{ fontSize: 13, opacity: 0.9, marginTop: 6 }}>Cada assinatura recebe um código de verificação (hash) e um selo de autenticidade. O documento final é enviado a você pelo WhatsApp.</p>
        </section>

        {/* Segurança / validade jurídica */}
        <section data-step style={{ background: '#f8fafc', border: `1px solid ${GOLD}55`, borderRadius: 16, padding: 16 }}>
          <h2 className="font-display" style={{ fontSize: 16, fontWeight: 700, color: GREEN, margin: '0 0 6px' }}>Tem validade jurídica?</h2>
          <p style={{ fontSize: 13.5, color: '#475569', lineHeight: 1.55, margin: 0 }}>
            Sim. É uma <b>assinatura eletrônica avançada</b>: registramos o seu nome, CPF, a data e a hora, o endereço de internet (IP) e um <b>código de integridade (hash)</b> que garante que o documento não foi alterado. Tem respaldo na <b>Lei nº 14.063/2020</b> e na <b>MP nº 2.200‑2/2001</b>.
          </p>
        </section>
      </div>

      <p style={{ textAlign: 'center', fontSize: 11, color: '#94a3b8', marginTop: 24 }}>Dúvidas? Responda a mensagem do WhatsApp que enviou este link.</p>
    </main>
  );
}
