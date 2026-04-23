// @module ptam/HistoricoVersoes — Drawer de histórico de versões com diff, lacre e QR Code
import React, { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../../ui/sheet';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Badge } from '../../ui/badge';
import { ptamAPI } from '../../../services/api';
import { useToast } from '../../../hooks/use-toast';
import { QRCodeSVG } from 'qrcode.react';
import {
  History,
  Lock,
  Unlock,
  Download,
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  X,
  Eye,
  Copy,
  ExternalLink
} from 'lucide-react';

const formatDate = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatHash = (hash) => {
  if (!hash) return '';
  return `${hash.substring(0, 12)}...${hash.substring(hash.length - 8)}`;
};

const DiffModal = ({ versao, onClose }) => {
  if (!versao) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Diff Completo — Versão {versao.numero_versao}
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-4 overflow-y-auto flex-1">
          {versao.diffs?.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Nenhuma alteração registrada nesta versão.</p>
          ) : (
            <div className="space-y-3">
              {versao.diffs.map((diff, idx) => (
                <div key={idx} className="border rounded-lg p-3 bg-gray-50">
                  <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
                    {diff.campo}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-red-50 border border-red-200 rounded p-2">
                      <div className="text-xs text-red-600 mb-1">Anterior</div>
                      <div className="text-sm text-red-800 break-all">
                        {diff.valor_anterior !== null && diff.valor_anterior !== undefined
                          ? String(diff.valor_anterior)
                          : '(vazio)'}
                      </div>
                    </div>
                    <div className="bg-emerald-50 border border-emerald-200 rounded p-2">
                      <div className="text-xs text-emerald-600 mb-1">Novo</div>
                      <div className="text-sm text-emerald-800 break-all">
                        {diff.valor_novo !== null && diff.valor_novo !== undefined
                          ? String(diff.valor_novo)
                          : '(vazio)'}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="p-4 border-t flex justify-end">
          <Button variant="outline" onClick={onClose}>Fechar</Button>
        </div>
      </div>
    </div>
  );
};

const LacreModal = ({ ptamId, numeroPtam, onClose, onLacreCriado }) => {
  const [observacao, setObservacao] = useState('');
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const { toast } = useToast();
  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  const handleLacrar = async () => {
    setLoading(true);
    try {
      const res = await ptamAPI.lacrarVersao(ptamId, observacao);
      setResultado(res.data);
      onLacreCriado?.();
      toast({ title: 'Versão lacrada com sucesso', description: `Número: ${res.data.numero_lacre}` });
    } catch (err) {
      toast({ 
        title: 'Erro ao lacrar versão', 
        description: err.response?.data?.detail || err.message,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast({ title: 'Copiado para a área de transferência' });
  };

  if (resultado) {
    const qrUrl = `${backendUrl}/ptam/${ptamId}/versoes/${resultado.versao.id}?publico=1`;
    
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl max-w-md w-full p-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Lock className="w-8 h-8 text-emerald-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900">Versão Lacrada</h3>
            <p className="text-sm text-gray-500 mt-1">
              O laudo foi lacrado e está pronto para entrega oficial.
            </p>
          </div>

          <div className="space-y-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Número de Lacre</div>
              <div className="flex items-center gap-2">
                <code className="text-lg font-bold text-emerald-800">{resultado.numero_lacre}</code>
                <button onClick={() => copyToClipboard(resultado.numero_lacre)} className="p-1 hover:bg-gray-200 rounded">
                  <Copy className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Hash SHA-256</div>
              <div className="flex items-center gap-2">
                <code className="text-xs font-mono text-gray-700 break-all">{resultado.hash_sha256}</code>
                <button onClick={() => copyToClipboard(resultado.hash_sha256)} className="p-1 hover:bg-gray-200 rounded flex-shrink-0">
                  <Copy className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>

            <div className="flex flex-col items-center p-4 bg-white border rounded-lg">
              <QRCodeSVG value={qrUrl} size={180} level="H" />
              <p className="text-xs text-gray-500 mt-3 text-center">
                Apresente este QR Code junto ao laudo impresso<br />para verificação de autenticidade
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>
              Fechar
            </Button>
            <Button 
              className="flex-1 bg-emerald-700 hover:bg-emerald-800"
              onClick={() => window.open(qrUrl, '_blank')}
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Abrir Link
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold mb-2">Lacrar Versão Atual</h3>
        <p className="text-sm text-gray-500 mb-4">
          O lacre cria uma versão imutável do laudo com hash SHA-256 para fins de autenticidade.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Observação (opcional)
            </label>
            <Input
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
              placeholder="Ex: Entregue ao Banco do Brasil em 23/04/2026"
            />
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
              <p className="text-xs text-amber-700">
                Após o lacre, você poderá continuar editando o laudo. 
                O lacre preserva o estado atual para referência futura.
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          <Button variant="outline" className="flex-1" onClick={onClose}>
            Cancelar
          </Button>
          <Button 
            className="flex-1 bg-emerald-700 hover:bg-emerald-800"
            onClick={handleLacrar}
            disabled={loading}
          >
            {loading ? 'Lacrando...' : <><Lock className="w-4 h-4 mr-2" /> Lacrar Versão</>}
          </Button>
        </div>
      </div>
    </div>
  );
};

const VerificarIntegridadeModal = ({ ptamId, versao, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [resultado, setResultado] = useState(null);
  const { toast } = useToast();

  useEffect(() => {
    const verificar = async () => {
      try {
        const res = await ptamAPI.verificarIntegridade(ptamId, versao.id);
        setResultado(res.data);
      } catch (err) {
        toast({
          title: 'Erro na verificação',
          description: err.response?.data?.detail || err.message,
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };
    verificar();
  }, [ptamId, versao.id, toast]);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold mb-4">Verificação de Integridade</h3>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-sm text-gray-500">Verificando hash SHA-256...</p>
          </div>
        ) : resultado ? (
          <div className="space-y-4">
            <div className={`p-4 rounded-lg ${resultado.integro ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-center gap-2 mb-2">
                {resultado.integro ? (
                  <CheckCircle className="w-6 h-6 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                )}
                <span className={`font-semibold ${resultado.integro ? 'text-emerald-800' : 'text-red-800'}`}>
                  {resultado.integro ? 'Documento Íntegro' : 'Integridade Comprometida'}
                </span>
              </div>
              <p className="text-xs text-gray-600">
                {resultado.integro 
                  ? 'O hash SHA-256 calculado corresponde ao hash armazenado. O documento não foi alterado desde o lacre.'
                  : 'O hash calculado difere do armazenado. O documento pode ter sido alterado.'}
              </p>
            </div>

            <div className="space-y-2">
              <div className="bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-500">Hash Armazenado</div>
                <code className="text-xs font-mono break-all">{resultado.hash_armazenado}</code>
              </div>
              <div className="bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-500">Hash Calculado</div>
                <code className="text-xs font-mono break-all">{resultado.hash_calculado}</code>
              </div>
            </div>
          </div>
        ) : null}

        <Button className="w-full mt-4" onClick={onClose}>
          Fechar
        </Button>
      </div>
    </div>
  );
};

export const HistoricoVersoes = ({ ptamId, numeroPtam, open, onClose, versaoAtual }) => {
  const [versoes, setVersoes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [versaoSelecionada, setVersaoSelecionada] = useState(null);
  const [showDiff, setShowDiff] = useState(false);
  const [showLacre, setShowLacre] = useState(false);
  const [showVerificar, setShowVerificar] = useState(false);
  const { toast } = useToast();

  const fetchVersoes = async () => {
    if (!ptamId) return;
    setLoading(true);
    try {
      const res = await ptamAPI.listVersoes(ptamId);
      setVersoes(res.data);
    } catch (err) {
      toast({
        title: 'Erro ao carregar versões',
        description: err.response?.data?.detail || err.message,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchVersoes();
    }
  }, [open, ptamId]);

  const handleDownloadSnapshot = (versao) => {
    if (!versao.snapshot) {
      toast({ title: 'Snapshot não disponível', description: 'Apenas versões lacradas possuem snapshot completo.' });
      return;
    }
    const blob = new Blob([JSON.stringify(versao.snapshot, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PTAM-${numeroPtam}-v${versao.numero_versao}-snapshot.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getDiffSummary = (versao) => {
    if (!versao.diffs || versao.diffs.length === 0) return 'Sem alterações';
    const count = versao.diffs.length;
    const firstThree = versao.diffs.slice(0, 3).map(d => {
      const campo = d.campo.split('.').pop();
      const de = d.valor_anterior !== null ? String(d.valor_anterior).substring(0, 15) : 'vazio';
      const para = d.valor_novo !== null ? String(d.valor_novo).substring(0, 15) : 'vazio';
      return `${campo}: ${de} → ${para}`;
    });
    if (count <= 3) return firstThree.join(', ');
    return `${firstThree.join(', ')} e mais ${count - 3} campos`;
  };

  return (
    <>
      <Sheet open={open} onOpenChange={onClose}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <History className="w-5 h-5" />
              Histórico de Versões
            </SheetTitle>
            <p className="text-sm text-gray-500">
              PTAM {numeroPtam}
            </p>
          </SheetHeader>

          <div className="mt-6 space-y-4">
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full mx-auto mb-3" />
                <p className="text-sm text-gray-500">Carregando versões...</p>
              </div>
            ) : versoes.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <History className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Nenhuma versão registrada ainda.</p>
                <p className="text-sm">As versões são criadas automaticamente ao salvar.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {versoes.map((versao) => (
                  <div
                    key={versao.id}
                    className={`border rounded-lg p-4 ${
                      versao.tipo === 'lacrado' 
                        ? 'bg-blue-50 border-blue-200' 
                        : 'bg-white border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge 
                          variant={versao.tipo === 'lacrado' ? 'default' : 'secondary'}
                          className={versao.tipo === 'lacrado' ? 'bg-blue-600' : ''}
                        >
                          {versao.tipo === 'lacrado' ? (
                            <><Lock className="w-3 h-3 mr-1" /> LACRADO</>
                          ) : (
                            `v${versao.numero_versao}`
                          )}
                        </Badge>
                        <span className="text-xs text-gray-500">
                          {formatDate(versao.created_at)}
                        </span>
                      </div>
                    </div>

                    {versao.numero_lacre && (
                      <div className="mb-2">
                        <code className="text-xs font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                          {versao.numero_lacre}
                        </code>
                      </div>
                    )}

                    {versao.hash_sha256 && (
                      <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
                        <ShieldCheck className="w-3 h-3" />
                        <code className="font-mono">{formatHash(versao.hash_sha256)}</code>
                      </div>
                    )}

                    {versao.tipo === 'auto' && versao.diffs?.length > 0 && (
                      <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                        {getDiffSummary(versao)}
                      </p>
                    )}

                    {versao.observacao && (
                      <p className="text-xs text-gray-500 mb-3 italic">
                        "{versao.observacao}"
                      </p>
                    )}

                    <div className="flex flex-wrap gap-2">
                      {versao.diffs?.length > 0 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => {
                            setVersaoSelecionada(versao);
                            setShowDiff(true);
                          }}
                        >
                          <Eye className="w-3 h-3 mr-1" />
                          Ver diff
                        </Button>
                      )}

                      {versao.tipo === 'lacrado' && versao.snapshot && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => handleDownloadSnapshot(versao)}
                        >
                          <Download className="w-3 h-3 mr-1" />
                          Baixar snapshot
                        </Button>
                      )}

                      {versao.tipo === 'lacrado' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => {
                            setVersaoSelecionada(versao);
                            setShowVerificar(true);
                          }}
                        >
                          <ShieldCheck className="w-3 h-3 mr-1" />
                          Verificar integridade
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Botão de lacre fixo no footer */}
          <div className="sticky bottom-0 bg-white border-t pt-4 mt-6">
            <Button
              className="w-full bg-emerald-700 hover:bg-emerald-800"
              onClick={() => setShowLacre(true)}
            >
              <Lock className="w-4 h-4 mr-2" />
              Lacrar versão atual
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {showDiff && versaoSelecionada && (
        <DiffModal
          versao={versaoSelecionada}
          onClose={() => {
            setShowDiff(false);
            setVersaoSelecionada(null);
          }}
        />
      )}

      {showLacre && (
        <LacreModal
          ptamId={ptamId}
          numeroPtam={numeroPtam}
          onClose={() => setShowLacre(false)}
          onLacreCriado={() => {
            fetchVersoes();
            onClose();
          }}
        />
      )}

      {showVerificar && versaoSelecionada && (
        <VerificarIntegridadeModal
          ptamId={ptamId}
          versao={versaoSelecionada}
          onClose={() => {
            setShowVerificar(false);
            setVersaoSelecionada(null);
          }}
        />
      )}
    </>
  );
};

export default HistoricoVersoes;
