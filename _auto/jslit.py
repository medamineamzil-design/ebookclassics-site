"""Lecture des données JavaScript du site (BOOKS, CATEGORIES, AUTHOR_BIOS) sans Node.
Petit analyseur de littéraux JS : objets, tableaux, chaînes '…' et "…", nombres, true/false/null."""
import json, re


class _P:
    def __init__(self, s):
        self.s, self.i = s, 0

    def ws(self):
        s, n = self.s, len(self.s)
        while self.i < n:
            c = s[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif s.startswith("//", self.i):
                j = s.find("\n", self.i)
                self.i = n if j < 0 else j
            elif s.startswith("/*", self.i):
                self.i = s.index("*/", self.i) + 2
            else:
                break

    def val(self):
        self.ws()
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in "'\"`":
            return self.string()
        m = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?").match(self.s, self.i)
        if m:
            self.i = m.end()
            return float(m.group()) if (m.group(1) or m.group(2)) else int(m.group())
        for w, v in (("true", True), ("false", False), ("null", None), ("undefined", None)):
            if self.s.startswith(w, self.i):
                self.i += len(w)
                return v
        raise ValueError(f"valeur inattendue à {self.i}: {self.s[self.i:self.i + 40]!r}")

    def string(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        while True:
            c = self.s[self.i]
            if c == "\\":
                nx = self.s[self.i + 1]
                if nx == "u":
                    out.append(chr(int(self.s[self.i + 2:self.i + 6], 16)))
                    self.i += 6
                    continue
                out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "0": "\0"}.get(nx, nx))
                self.i += 2
                continue
            if c == q:
                self.i += 1
                return "".join(out)
            out.append(c)
            self.i += 1

    def key(self):
        self.ws()
        if self.s[self.i] in "'\"":
            return self.string()
        m = re.compile(r"[A-Za-z_$][\w$]*|\d+").match(self.s, self.i)
        self.i = m.end()
        return m.group()

    def obj(self):
        self.i += 1
        o = {}
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1
                return o
            k = self.key()
            self.ws()
            assert self.s[self.i] == ":", self.s[self.i:self.i + 30]
            self.i += 1
            o[k] = self.val()
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1

    def arr(self):
        self.i += 1
        a = []
        while True:
            self.ws()
            if self.s[self.i] == "]":
                self.i += 1
                return a
            a.append(self.val())
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1


def parse(src):
    return _P(src).val()


def const_span(site, name):
    """(début de la valeur, fin de la valeur) de `const NAME = <valeur>`."""
    i = site.index(f"const {name} =")
    j = i + len(f"const {name} =")
    p = _P(site)
    p.i = j
    p.ws()
    start = p.i
    p.val()
    return start, p.i


def const(site, name):
    a, b = const_span(site, name)
    return parse(site[a:b])


def slug_file(title):
    import unicodedata
    s = unicodedata.normalize("NFD", title)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")[:60].lower()


def books_json(site):
    """Même contenu que l'ancien extract.js : livres (sans couverture intégrée), biographies, catégories."""
    books = const(site, "BOOKS")
    for b in books:
        b["slug"] = slug_file(b["title"])
        for k in ("coverImg", "price", "rating", "reviews", "badge", "h"):
            b.pop(k, None)
    return {"books": books, "bios": const(site, "AUTHOR_BIOS"), "cats": const(site, "CATEGORIES")}


if __name__ == "__main__":
    import sys
    site = open(sys.argv[1], encoding="utf-8").read()
    d = books_json(site)
    print(len(d["books"]), "livres,", len(d["bios"]), "biographies,", len(d["cats"]), "catégories")
    json.dump(d, open(sys.argv[2], "w"), indent=1, ensure_ascii=False) if len(sys.argv) > 2 else None
