import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Search, Loader2, Check, MapPin, Home, Maximize, DollarSign, ExternalLink } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';

const TIPOS_IMOVEL = [
  { value: 'casa', label: 'Casa' },
  { value: 'apartamento', label: 'Apartamento' },
  { value: 'terreno', label: 'Terreno' },
  { value: 'sala_comercial', label: 'Sala Comercial' },
  { value: 'galpao', label: 'Galpão' },
  { value: 'chacara', label: 'Chácara' },
  { value: 'fazenda', label: 'Fazenda' },
];

const ESTADOS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
  'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

const LIMITES = [
  { value: 10, label: '10 amostras' },
  { value: 20, label: '20 amostras' },
  { value: 30, label: '30 amostras' },
];

export function BuscaAmostras({ open, onClose, onImport, cidadeDefault = '', estadoDefault = '' }) {
  const [form, setForm] = useState({
    cidade: cidadeDefault,
    estado: estadoDefault,
    tipo_imovel: 'casa',
    area_min: 80,
    area_max: 200,
    valor_max: 500000,
    bairro: '',
    limite: 20,
  });
  
  const [loading, setLoading] = useState(false);
  const [resultados, setResultados] = useState([]);
  const [selecionadas, setSelecionadas] = useState(new Set());
  const { toast } = useToast();

  useEffect(() => {
    if (open) {
      setForm(prev => ({
        ...prev,
        cidade: cidadeDefault || prev.cidade,
        estado: estadoDefault || prev.estado,
      }));
    }
  }, [open, cidadeDefault, estadoDefault]);

  const handleBuscar = async () => {
    if (!form.cidade || !form.estado) {
      toast({ title: 'Preencha cidade e estado', variant: 'destructive' });
      return;
    }

    setLoading(true);
    setResultados([]);
    setSelecionadas(new Set());

    try {
      const response = await api.post('/scraper/amostras', form);
      const data = response.data;
      
      if (data.amostras && data.amostras.length > 0) {
        setResultados(data.amostras);
        toast({ 
          title: `${data.total} amostras encontradas`, 
          description: `Fonte: ${data.fonte}` 
        });
      } else {
        toast({ 
          title: 'Nenhuma amostra encontrada', 
          description: 'Tente ajustar os filtros de busca.',
          variant: 'destructive' 
        });
      }
    } catch (error) {
      console.error('Erro na busca:', error);
      toast({ 
        title: 'Erro na busca', 
        description: error.response?.data?.detail || 'Tente novamente mais tarde.',
        variant: 'destructive' 
      });
    } finally {
      setLoading(false);
    }
  };

  const toggleSelecao = (index) => {
    const novo = new Set(selecionadas);
    if (novo.has(index)) {
      novo.delete(index);
    } else {
      novo.add(index);
    }
    setSelecionadas(novo);
  };

  const selecionarTodas = () => {
    if (selecionadas.size === resultados.length) {
      setSelecionadas(new Set());
    } else {
      setSelecionadas(new Set(resultados.map((_, i) => i)));
    }
  };

  const handleImportar = () => {
    const amostrasSelecionadas = resultados.filter((_, i) => selecionadas.has(i));
    onImport(amostrasSelecionadas);
    toast({ title: `${amostrasSelecionadas.length} amostras importadas!` });
  };

  const getBadgeColor = (fonte) => {
    if (fonte.includes('ZAP')) return 'bg-blue-600 hover:bg-blue-700';
    if (fonte.includes('VivaReal')) return 'bg-purple-600 hover:bg-purple-700';
    if (fonte.includes('OLX')) return 'bg-orange-600 hover:bg-orange-700';
    return 'bg-emerald-600 hover:bg-emerald-700';
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto bg-slate-900 border-slate-700 text-slate-100">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl text-emerald-400">
            <Search className="w-5 h-5" />
            Buscar Amostras Automaticamente
          </DialogTitle>
        </DialogHeader>

        {/* Formulário de busca */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4">
          <div className="space-y-2">
            <Label className="text-slate-300">Cidade</Label>
            <div className="relative">
              <MapPin className="absolute left-2 top-2.5 w-4 h-4 text-slate-400" />
              <Input
                value={form.cidade}
                onChange={(e) => setForm({ ...form, cidade: e.target.value })}
                placeholder="Ex: São Luís"
                className="pl-8 bg-slate-800 border-slate-600 text-slate-100"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Estado</Label>
            <Select value={form.estado} onValueChange={(v) => setForm({ ...form, estado: v })}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-slate-100">
                <SelectValue placeholder="UF" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                {ESTADOS.map(uf => (
                  <SelectItem key={uf} value={uf} className="text-slate-100">{uf}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Tipo de Imóvel</Label>
            <Select value={form.tipo_imovel} onValueChange={(v) => setForm({ ...form, tipo_imovel: v })}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-slate-100">
                <Home className="w-4 h-4 mr-2 text-slate-400" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                {TIPOS_IMOVEL.map(tipo => (
                  <SelectItem key={tipo.value} value={tipo.value} className="text-slate-100">
                    {tipo.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Limite</Label>
            <Select value={String(form.limite)} onValueChange={(v) => setForm({ ...form, limite: Number(v) })}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-slate-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-600">
                {LIMITES.map(lim => (
                  <SelectItem key={lim.value} value={String(lim.value)} className="text-slate-100">
                    {lim.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Área Mínima (m²)</Label>
            <div className="relative">
              <Maximize className="absolute left-2 top-2.5 w-4 h-4 text-slate-400" />
              <Input
                type="number"
                value={form.area_min}
                onChange={(e) => setForm({ ...form, area_min: Number(e.target.value) })}
                className="pl-8 bg-slate-800 border-slate-600 text-slate-100"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Área Máxima (m²)</Label>
            <div className="relative">
              <Maximize className="absolute left-2 top-2.5 w-4 h-4 text-slate-400" />
              <Input
                type="number"
                value={form.area_max}
                onChange={(e) => setForm({ ...form, area_max: Number(e.target.value) })}
                className="pl-8 bg-slate-800 border-slate-600 text-slate-100"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Valor Máximo (R$)</Label>
            <div className="relative">
              <DollarSign className="absolute left-2 top-2.5 w-4 h-4 text-slate-400" />
              <Input
                type="number"
                value={form.valor_max}
                onChange={(e) => setForm({ ...form, valor_max: Number(e.target.value) })}
                className="pl-8 bg-slate-800 border-slate-600 text-slate-100"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Bairro (opcional)</Label>
            <Input
              value={form.bairro}
              onChange={(e) => setForm({ ...form, bairro: e.target.value })}
              placeholder="Ex: Centro"
              className="bg-slate-800 border-slate-600 text-slate-100"
            />
          </div>
        </div>

        {/* Botão de busca */}
        <div className="flex justify-center pb-4">
          <Button
            onClick={handleBuscar}
            disabled={loading}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-8"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Buscando...
              </>
            ) : (
              <>
                <Search className="w-4 h-4 mr-2" />
                Buscar no ZAP / VivaReal
              </>
            )}
          </Button>
        </div>

        {/* Resultados */}
        {resultados.length > 0 && (
          <div className="border-t border-slate-700 pt-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-emerald-400">
                Resultados ({resultados.length})
              </h3>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={selecionarTodas}
                  className="border-slate-600 text-slate-300 hover:bg-slate-800"
                >
                  {selecionadas.size === resultados.length ? 'Limpar seleção' : 'Selecionar tudo'}
                </Button>
              </div>
            </div>

            <div className="grid gap-3 max-h-[400px] overflow-y-auto pr-2">
              {resultados.map((amostra, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-lg border transition-all cursor-pointer ${
                    selecionadas.has(idx)
                      ? 'border-emerald-500 bg-emerald-900/20'
                      : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                  }`}
                  onClick={() => toggleSelecao(idx)}
                >
                  <div className="flex items-start gap-3">
                    <Checkbox
                      checked={selecionadas.has(idx)}
                      onCheckedChange={() => toggleSelecao(idx)}
                      className="mt-1 border-emerald-500 data-[state=checked]:bg-emerald-600"
                    />
                    
                    {amostra.thumbnail && (
                      <img
                        src={amostra.thumbnail}
                        alt=""
                        className="w-20 h-16 object-cover rounded bg-slate-700"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    )}
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className={`${getBadgeColor(amostra.source)} text-white text-xs`}>
                          {amostra.source}
                        </Badge>
                        <span className="text-xs text-slate-400">
                          {amostra.collection_date}
                        </span>
                      </div>
                      
                      <p className="text-sm font-medium text-slate-100 truncate">
                        {amostra.address}
                      </p>
                      <p className="text-xs text-slate-400">
                        {amostra.neighborhood}
                      </p>
                      
                      <div className="flex items-center gap-4 mt-2 text-sm">
                        {amostra.area > 0 && (
                          <span className="text-slate-300">
                            {amostra.area.toFixed(0)} m²
                          </span>
                        )}
                        <span className="text-emerald-400 font-semibold">
                          {formatCurrency(amostra.value)}
                        </span>
                        {amostra.value_per_sqm > 0 && (
                          <span className="text-slate-400">
                            {formatCurrency(amostra.value_per_sqm)}/m²
                          </span>
                        )}
                      </div>
                      
                      {amostra.notes && (
                        <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                          {amostra.notes}
                        </p>
                      )}
                      
                      {amostra.source_url && (
                        <a
                          href={amostra.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 mt-2"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink className="w-3 h-3" />
                          Ver no site
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <DialogFooter className="border-t border-slate-700 pt-4">
          <Button variant="outline" onClick={onClose} className="border-slate-600 text-slate-300">
            Cancelar
          </Button>
          {selecionadas.size > 0 && (
            <Button
              onClick={handleImportar}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              <Check className="w-4 h-4 mr-2" />
              Importar Selecionadas ({selecionadas.size})
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
