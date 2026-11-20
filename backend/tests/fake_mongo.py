# @module tests.fake_mongo — dublê de MongoDB (Motor) em memória, só para testes.
#
# Cobre o subconjunto que as rotas usam: filtros com igualdade, caminhos com ponto,
# $or/$and e operadores de comparação; find com projeção/sort/skip/limit; update com
# $set/$unset/$inc/$push/$addToSet/$pull/$setOnInsert; find_one_and_*; delete; count.
# Qualquer coleção é criada sob demanda (db.qualquer_nome).
import copy
import re
from datetime import datetime

_FALTA = object()


def _get(doc, caminho):
    atual = doc
    for parte in caminho.split("."):
        if isinstance(atual, dict) and parte in atual:
            atual = atual[parte]
        elif isinstance(atual, list) and parte.isdigit() and int(parte) < len(atual):
            atual = atual[int(parte)]
        else:
            return _FALTA
    return atual


def _set(doc, caminho, valor):
    partes = caminho.split(".")
    alvo = doc
    for p in partes[:-1]:
        alvo = alvo.setdefault(p, {})
    alvo[partes[-1]] = valor


def _unset(doc, caminho):
    partes = caminho.split(".")
    alvo = doc
    for p in partes[:-1]:
        alvo = alvo.get(p) if isinstance(alvo, dict) else None
        if alvo is None:
            return
    if isinstance(alvo, dict):
        alvo.pop(partes[-1], None)


def _cmp(a, b, op):
    try:
        return op(a, b)
    except TypeError:
        return False


def _casa_valor(atual, cond):
    if isinstance(cond, dict) and cond and all(k.startswith("$") for k in cond):
        for op, v in cond.items():
            presente = atual is not _FALTA
            val = None if atual is _FALTA else atual
            if op == "$eq" and not _casa_valor(atual, v):
                return False
            if op == "$ne" and _casa_valor(atual, v):
                return False
            if op == "$in" and not any(_casa_valor(atual, x) for x in v):
                return False
            if op == "$nin" and any(_casa_valor(atual, x) for x in v):
                return False
            if op == "$exists" and presente != bool(v):
                return False
            if op == "$gt" and not (presente and _cmp(val, v, lambda a, b: a > b)):
                return False
            if op == "$gte" and not (presente and _cmp(val, v, lambda a, b: a >= b)):
                return False
            if op == "$lt" and not (presente and _cmp(val, v, lambda a, b: a < b)):
                return False
            if op == "$lte" and not (presente and _cmp(val, v, lambda a, b: a <= b)):
                return False
            if op == "$regex":
                flags = re.I if "i" in (cond.get("$options") or "") else 0
                if not (isinstance(val, str) and re.search(v, val, flags)):
                    return False
            if op == "$elemMatch":
                if not isinstance(val, list) or not any(
                        isinstance(x, dict) and casa(x, v) for x in val):
                    return False
        return True
    if atual is _FALTA:
        return cond is None
    if isinstance(atual, list) and not isinstance(cond, list):
        return cond in atual
    return atual == cond


def casa(doc, filtro):
    for k, v in (filtro or {}).items():
        if k == "$or":
            if not any(casa(doc, f) for f in v):
                return False
        elif k == "$and":
            if not all(casa(doc, f) for f in v):
                return False
        elif k == "$nor":
            if any(casa(doc, f) for f in v):
                return False
        elif not _casa_valor(_get(doc, k), v):
            return False
    return True


def _projetar(doc, proj):
    doc = copy.deepcopy(doc)
    if not proj:
        return doc
    incluir = {k for k, v in proj.items() if v and k != "_id"}
    if incluir:
        out = {k: doc[k] for k in incluir if k in doc}
        if proj.get("_id", 1) and "_id" in doc:
            out["_id"] = doc["_id"]
        return out
    for k, v in proj.items():
        if not v:
            _unset(doc, k)
    return doc


def _chave_sort(valor):
    if valor is _FALTA or valor is None:
        return (0, "")
    if isinstance(valor, (int, float)):
        return (1, valor)
    if isinstance(valor, datetime):
        return (2, valor.isoformat())
    return (3, str(valor))


def _ordenar(docs, sort):
    if not sort:
        return docs
    if isinstance(sort, str):
        sort = [(sort, 1)]
    for campo, direcao in reversed(list(sort)):
        docs = sorted(docs, key=lambda d: _chave_sort(_get(d, campo)), reverse=direcao < 0)
    return docs


class _Res:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Cursor:
    def __init__(self, docs):
        self._docs = docs
        self._sort = None
        self._skip = 0
        self._limit = 0

    def sort(self, campo, direcao=None):
        self._sort = [(campo, direcao or 1)] if isinstance(campo, str) else campo
        return self

    def skip(self, n):
        self._skip = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _resultado(self):
        docs = _ordenar(self._docs, self._sort)[self._skip:]
        return docs[: self._limit] if self._limit else docs

    async def to_list(self, length=None):
        docs = self._resultado()
        return docs[:length] if length else docs

    def __aiter__(self):
        self._it = iter(self._resultado())
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class Colecao:
    def __init__(self):
        self.docs = []

    # leitura
    def find(self, filtro=None, projecao=None, *a, sort=None, **kw):
        cur = Cursor([_projetar(d, projecao) for d in self.docs if casa(d, filtro)])
        if sort:
            cur.sort(sort)
        return cur

    async def find_one(self, filtro=None, projecao=None, *a, sort=None, **kw):
        docs = _ordenar([d for d in self.docs if casa(d, filtro)], sort)
        return _projetar(docs[0], projecao) if docs else None

    async def count_documents(self, filtro=None, **kw):
        return sum(1 for d in self.docs if casa(d, filtro))

    async def estimated_document_count(self):
        return len(self.docs)

    async def distinct(self, campo, filtro=None):
        vals = []
        for d in self.docs:
            if casa(d, filtro):
                v = _get(d, campo)
                if v is not _FALTA and v not in vals:
                    vals.append(v)
        return vals

    def aggregate(self, *a, **kw):
        return Cursor([])

    # escrita
    async def insert_one(self, doc):
        doc = copy.deepcopy(doc)
        doc.setdefault("_id", f"oid{len(self.docs) + 1}-{id(doc)}")
        self.docs.append(doc)
        return _Res(inserted_id=doc["_id"])

    async def insert_many(self, docs, **kw):
        ids = [(await self.insert_one(d)).inserted_id for d in docs]
        return _Res(inserted_ids=ids)

    @staticmethod
    def _aplicar(doc, upd, inserindo=False):
        if not any(k.startswith("$") for k in upd):
            keep = {k: doc[k] for k in ("_id",) if k in doc}
            doc.clear()
            doc.update(copy.deepcopy(upd))
            doc.update(keep)
            return
        for k, v in (upd.get("$set") or {}).items():
            _set(doc, k, copy.deepcopy(v))
        if inserindo:
            for k, v in (upd.get("$setOnInsert") or {}).items():
                _set(doc, k, copy.deepcopy(v))
        for k in (upd.get("$unset") or {}):
            _unset(doc, k)
        for k, v in (upd.get("$inc") or {}).items():
            atual = _get(doc, k)
            _set(doc, k, (0 if atual is _FALTA or atual is None else atual) + v)
        for k, v in (upd.get("$push") or {}).items():
            lista = _get(doc, k)
            lista = [] if lista is _FALTA or lista is None else lista
            if isinstance(v, dict) and "$each" in v:
                lista.extend(copy.deepcopy(v["$each"]))
            else:
                lista.append(copy.deepcopy(v))
            _set(doc, k, lista)
        for k, v in (upd.get("$addToSet") or {}).items():
            lista = _get(doc, k)
            lista = [] if lista is _FALTA or lista is None else lista
            itens = v["$each"] if isinstance(v, dict) and "$each" in v else [v]
            for it in itens:
                if it not in lista:
                    lista.append(copy.deepcopy(it))
            _set(doc, k, lista)
        for k, v in (upd.get("$pull") or {}).items():
            lista = _get(doc, k)
            if isinstance(lista, list):
                _set(doc, k, [x for x in lista if not (
                    casa(x, v) if isinstance(v, dict) and isinstance(x, dict) else x == v)])

    def _novo_de_filtro(self, filtro):
        return {k: copy.deepcopy(v) for k, v in (filtro or {}).items()
                if not k.startswith("$") and not isinstance(v, dict)}

    async def update_one(self, filtro, upd, upsert=False, **kw):
        alvo = next((d for d in self.docs if casa(d, filtro)), None)
        if alvo is None:
            if not upsert:
                return _Res(matched_count=0, modified_count=0, upserted_id=None)
            alvo = self._novo_de_filtro(filtro)
            self._aplicar(alvo, upd, inserindo=True)
            await self.insert_one(alvo)
            return _Res(matched_count=0, modified_count=0, upserted_id=alvo.get("_id"))
        self._aplicar(alvo, upd)
        return _Res(matched_count=1, modified_count=1, upserted_id=None)

    async def update_many(self, filtro, upd, **kw):
        alvos = [d for d in self.docs if casa(d, filtro)]
        for d in alvos:
            self._aplicar(d, upd)
        return _Res(matched_count=len(alvos), modified_count=len(alvos))

    async def replace_one(self, filtro, novo, upsert=False, **kw):
        return await self.update_one(filtro, novo, upsert=upsert)

    async def find_one_and_update(self, filtro, upd, *a, upsert=False,
                                  return_document=False, projection=None, sort=None, **kw):
        docs = _ordenar([d for d in self.docs if casa(d, filtro)], sort)
        if not docs:
            if not upsert:
                return None
            novo = self._novo_de_filtro(filtro)
            self._aplicar(novo, upd, inserindo=True)
            await self.insert_one(novo)
            return _projetar(self.docs[-1], projection) if return_document else None
        antes = copy.deepcopy(docs[0])
        self._aplicar(docs[0], upd)
        return _projetar(docs[0] if return_document else antes, projection)

    async def find_one_and_delete(self, filtro, **kw):
        alvo = next((d for d in self.docs if casa(d, filtro)), None)
        if alvo is not None:
            self.docs.remove(alvo)
        return alvo

    async def delete_one(self, filtro, **kw):
        alvo = next((d for d in self.docs if casa(d, filtro)), None)
        if alvo is not None:
            self.docs.remove(alvo)
        return _Res(deleted_count=1 if alvo is not None else 0)

    async def delete_many(self, filtro, **kw):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not casa(d, filtro)]
        return _Res(deleted_count=antes - len(self.docs))

    async def create_index(self, *a, **kw):
        return "idx"


class FakeDB:
    def __init__(self):
        self._cols = {}

    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        return self._cols.setdefault(nome, Colecao())

    def __getitem__(self, nome):
        return getattr(self, nome)

    async def list_collection_names(self):
        return list(self._cols)
