# @module tests.privacidade_fake — Mongo em memória (subconjunto) p/ os testes de privacidade.
# Dados 100% sintéticos. Suporta os operadores usados em services/privacidade e nas rotas
# exercitadas: $in/$ne/$gte/$lt/$exists, $set/$inc/$push($each)/$unset, upsert.
import copy


def _bate(doc, filtro):
    for k, v in (filtro or {}).items():
        atual = doc.get(k)
        if isinstance(v, dict) and any(str(x).startswith("$") for x in v):
            if "$in" in v and atual not in v["$in"]:
                return False
            if "$ne" in v and atual == v["$ne"]:
                return False
            if "$gte" in v and not (atual is not None and atual >= v["$gte"]):
                return False
            if "$lt" in v and not (atual is not None and atual < v["$lt"]):
                return False
            if "$exists" in v and (k in doc) != bool(v["$exists"]):
                return False
        elif atual != v:
            return False
    return True


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, campo, direcao=1):
        if isinstance(campo, list):
            campo, direcao = campo[0]
        self._docs.sort(key=lambda d: (d.get(campo) is None, d.get(campo)), reverse=direcao == -1)
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, n=None):
        return [copy.deepcopy(d) for d in (self._docs if n is None else self._docs[:n])]

    def __aiter__(self):
        self._it = iter(list(self._docs))
        return self

    async def __anext__(self):
        try:
            return copy.deepcopy(next(self._it))
        except StopIteration:
            raise StopAsyncIteration


class _R:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Coll:
    def __init__(self):
        self.docs = []

    def find(self, filtro=None, projecao=None):
        return _Cursor([d for d in self.docs if _bate(d, filtro)])

    async def find_one(self, filtro=None, *a, **kw):
        for d in self.docs:
            if _bate(d, filtro):
                return copy.deepcopy(d)
        return None

    async def insert_one(self, doc):
        self.docs.append(copy.deepcopy(doc))
        return _R(inserted_id=doc.get("id"))

    async def count_documents(self, filtro=None):
        return sum(1 for d in self.docs if _bate(d, filtro))

    async def delete_many(self, filtro):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not _bate(d, filtro)]
        return _R(deleted_count=antes - len(self.docs))

    async def delete_one(self, filtro):
        for i, d in enumerate(self.docs):
            if _bate(d, filtro):
                del self.docs[i]
                return _R(deleted_count=1)
        return _R(deleted_count=0)

    async def update_one(self, filtro, upd, upsert=False):
        alvo = next((d for d in self.docs if _bate(d, filtro)), None)
        if alvo is None:
            if not upsert:
                return _R(matched_count=0, modified_count=0)
            alvo = {k: v for k, v in filtro.items() if not isinstance(v, dict)}
            self.docs.append(alvo)
        for k, v in (upd.get("$set") or {}).items():
            alvo[k] = copy.deepcopy(v)
        for k in (upd.get("$unset") or {}):
            alvo.pop(k, None)
        for k, v in (upd.get("$inc") or {}).items():
            alvo[k] = (alvo.get(k) or 0) + v
        for k, v in (upd.get("$push") or {}).items():
            lista = alvo.setdefault(k, [])
            if isinstance(v, dict) and "$each" in v:
                lista.extend(copy.deepcopy(v["$each"]))
            else:
                lista.append(copy.deepcopy(v))
        return _R(matched_count=1, modified_count=1)


class FakeDB:
    """Qualquer atributo vira uma coleção vazia (como o Motor)."""

    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        c = Coll()
        setattr(self, nome, c)
        return c

    def __getitem__(self, nome):
        return getattr(self, nome)
