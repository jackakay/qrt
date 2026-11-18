import math
import random
import re
import time

# ----------------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------------
TIME_BUDGET = 9.4
END_RESERVE = 0.25    # stop searching this long before the budget runs out
SEED = 21

ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PRM = {
    "ORDER": "long",   # greedy order: "long" (longest first) or "mcv" (fewest options first)
    "TOUCH": 0.1,      # tie-break: prefer placements hugging already-filled cells
    "TSAMP": 40,       # max tied candidates scored for touch
    "TEMP": 1.0,       # LNS acceptance temperature (letters)
    "MU": 0.0,         # LNS: value of an empty cell (letters)
    "TABU": 6,
    "TABU_PEN": 25.0,
    "OV_W": 0.3,
    "ESAMP": 48,       # ejection candidates examined per move
    "RR": 1.0,         # share of moves that are ruin & recreate
    "RAD": 0,          # ruin window radius (0 = random 1..3)
}
TRACE = None  # debug hook

_pc = getattr(int, "bit_count", None) or (lambda x: bin(x).count("1"))

_GEOM = {}


class _Geom:
    def __init__(self, n):
        self.n = n
        NN = n * n
        B = 2 * n
        self.lines = [[None] * n for _ in range(4)]     # doubled cell lists
        self.cmask = [[0] * 4 for _ in range(NN)]       # per cell, per axis bitmask (both copies)
        self.where = [[None] * 4 for _ in range(NN)]    # per cell, per axis (line, pos)
        for a, (dr, dc) in enumerate(((0, 1), (1, 0), (1, 1), (1, -1))):
            for l in range(n):
                r, c = (l, 0) if a == 0 else (0, l)
                cells = []
                for t in range(n):
                    cell = r * n + c
                    cells.append(cell)
                    self.cmask[cell][a] = ((1 << n) | 1) << (B * l + t)
                    self.where[cell][a] = (l, t)
                    r, c = (r + dr) % n, (c + dc) % n
                self.lines[a][l] = cells + cells
        st = 0
        for l in range(n):
            st |= ((1 << n) - 1) << (B * l)
        self.starts = st
        self.full = (1 << (B * n)) - 1
        nb = []
        for cell in range(NN):
            r, c = divmod(cell, n)
            m = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr or dc:
                        m |= 1 << (((r + dr) % n) * n + (c + dc) % n)
            nb.append(m)
        self.nb = nb
        # every cell's 4 line ids (a, l) for forbidden checks
        self.cl = [[(a, self.where[c][a][0]) for a in range(4)] for c in range(NN)]


def _geom(n):
    g = _GEOM.get(n)
    if g is None:
        g = _GEOM[n] = _Geom(n)
    return g


def _bits(m):
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def _clean(words):
    out = []
    for w in words or []:
        if isinstance(w, str):
            w = w.strip().upper()
            if w and w.isascii() and w.isalpha():
                out.append(w)
    return out


def _lines_string(rows, ext):
    n = len(rows)
    reps = ext // n + 2
    out = []
    for r in rows:
        out.append((r * reps)[:n + ext])
    for c in range(n):
        out.append(("".join(rows[r][c] for r in range(n)) * reps)[:n + ext])
    for l in range(n):
        out.append(("".join(rows[t][(l + t) % n] for t in range(n)) * reps)[:n + ext])
    for l in range(n):
        out.append(("".join(rows[t][(l - t) % n] for t in range(n)) * reps)[:n + ext])
    return "|".join(out)


class _Ctx:
    pass


def _verify(rows, ctx):
    big = _lines_string(rows, ctx.ext)
    if ctx.forb_re is not None and ctx.forb_re.search(big):
        return False
    for w in ctx.uniq:
        if w not in big and w[::-1] not in big:
            return False
    return True


class _Board:
    """Consistent partial grid on an n x n torus with bitset placement queries."""

    def __init__(self, n, W, ctx, rng):
        self.n = n
        self.G = G = _geom(n)
        self.W = W
        self.ctx = ctx
        self.rng = rng
        self.cells = [-1] * (n * n)
        self.own = [[] for _ in range(n * n)]
        self.vac = [G.full] * 4
        self.let = [[0] * 26 for _ in range(4)]
        self.filled = 0
        self.P = [None] * len(W)      # (axis, bit, rev)
        self.log = None

    # -- low level ------------------------------------------------------------
    def _path(self, a, b, k):
        n = self.n
        l, t = divmod(b, 2 * n)
        return self.G.lines[a][l][t:t + k]

    def put(self, i, a, b, rev, check=True):
        wd = self.W[i]
        s = wd[1] if rev else wd[0]
        path = self._path(a, b, len(s))
        cells, own, cm, vac, let = self.cells, self.own, self.G.cmask, self.vac, self.let
        new = []
        for c, x in zip(path, s):
            if cells[c] < 0:
                cells[c] = x
                new.append(c)
                m = cm[c]
                for ax in range(4):
                    vac[ax] ^= m[ax]
                    let[ax][x] ^= m[ax]
                self.filled |= 1 << c
            own[c].append(i)
        self.P[i] = (a, b, rev)
        if check and new and self.ctx.forb_re is not None and self._forbidden_near(new):
            lg = self.log
            self.log = None
            self.take(i)
            self.log = lg
            return False
        if self.log is not None:
            self.log.append((0, i))
        return True

    def take(self, i):
        a, b, rev = self.P[i]
        wd = self.W[i]
        path = self._path(a, b, wd[2])
        cells, own, cm, vac, let = self.cells, self.own, self.G.cmask, self.vac, self.let
        for c in path:
            o = own[c]
            o.remove(i)
            if not o:
                x = cells[c]
                cells[c] = -1
                m = cm[c]
                for ax in range(4):
                    vac[ax] ^= m[ax]
                    let[ax][x] ^= m[ax]
                self.filled ^= 1 << c
        self.P[i] = None
        if self.log is not None:
            self.log.append((1, i, a, b, rev))

    def _forbidden_near(self, new):
        n = self.n
        G = self.G
        ext = self.ctx.ext
        reps = ext // n + 2
        seen = set()
        cells = self.cells
        for c in new:
            for al in G.cl[c]:
                if al in seen:
                    continue
                seen.add(al)
                a, l = al
                s = "".join([ALPHA[cells[x]] if cells[x] >= 0 else "." for x in G.lines[a][l][:n]])
                if self.ctx.forb_re.search((s * reps)[:n + ext]):
                    return True
        return False

    # -- queries ----------------------------------------------------------------
    def options(self, i):
        """List of (axis, rev, choices_mask) for conflict-free placements."""
        wd = self.W[i]
        out = []
        st = self.G.starts
        for a in range(4):
            vac = self.vac[a]
            let = self.let[a]
            for rev in (0, 1) if wd[3] else (0,):
                s = wd[1] if rev else wd[0]
                ch = st
                for k, x in enumerate(s):
                    ch &= (vac | let[x]) >> k
                    if not ch:
                        break
                if ch:
                    out.append((a, rev, ch))
        return out

    def count_options(self, i, cap):
        cnt = 0
        for _, _, ch in self.options(i):
            cnt += _pc(ch)
            if cnt >= cap:
                break
        return cnt

    def best_placements(self, i, opts):
        """Return (overlap, [(a, rev, bit), ...]) for maximum overlap."""
        k = self.W[i][2]
        best_ov = -1
        best = []
        for a, rev, ch in opts:
            vac = self.vac[a]
            planes = []
            for j in range(k):
                carry = ch & ~(vac >> j)
                for t in range(len(planes)):
                    if not carry:
                        break
                    p = planes[t]
                    planes[t] = p ^ carry
                    carry &= p
                if carry:
                    planes.append(carry)
            mask = ch
            ov = 0
            for t in range(len(planes) - 1, -1, -1):
                more = mask & planes[t]
                if more:
                    mask = more
                    ov |= 1 << t
            if ov > best_ov:
                best_ov = ov
                best = [(a, rev, mask)]
            elif ov == best_ov:
                best.append((a, rev, mask))
        return best_ov, best

    def touch(self, i, a, b, rev):
        k = self.W[i][2]
        path = self._path(a, b, k)
        adj = 0
        pm = 0
        cells = self.cells
        nb = self.G.nb
        for c in path:
            pm |= 1 << c
            if cells[c] < 0:
                adj |= nb[c]
        return _pc(self.filled & adj & ~pm)

    def insert_best(self, i, prm):
        opts = self.options(i)
        if not opts:
            return False
        ov, groups = self.best_placements(i, opts)
        cands = []
        for a, rev, mask in groups:
            for b in _bits(mask):
                cands.append((a, b, rev))
        rng = self.rng
        tw = prm["TOUCH"]
        if len(cands) > 1:
            if len(cands) > prm["TSAMP"]:
                cands = rng.sample(cands, prm["TSAMP"])
            if tw:
                cands = sorted(cands, key=lambda c: -(self.touch(i, *c) + rng.random() * 0.5))
            else:
                rng.shuffle(cands)
        for a, b, rev in cands[:20]:
            if self.put(i, a, b, rev):
                return True
        if self.ctx.forb_re is not None:
            # fall back to any conflict-free spot that avoids forbidden words
            allc = []
            for a, rev, ch in opts:
                for b in _bits(ch):
                    allc.append((a, b, rev))
            rng.shuffle(allc)
            for a, b, rev in allc[:60]:
                if self.put(i, a, b, rev):
                    return True
        return False

    def mismatch_sets(self, i):
        """Placements with exactly one / exactly two conflicting cells."""
        wd = self.W[i]
        st = self.G.starts
        one = []
        two = []
        for a in range(4):
            vac = self.vac[a]
            let = self.let[a]
            for rev in (0, 1) if wd[3] else (0,):
                s = wd[1] if rev else wd[0]
                f1 = f2 = f3 = 0
                for k, x in enumerate(s):
                    bad = st & ~((vac | let[x]) >> k)
                    f3 |= f2 & bad
                    f2 |= f1 & bad
                    f1 |= bad
                e1 = f1 & ~f2
                e2 = f2 & ~f3
                if e1:
                    one.append((a, rev, e1))
                if e2:
                    two.append((a, rev, e2))
        return one, two

    def rows(self, filler_fn):
        return filler_fn(self.cells)


def _fill_and_verify(n, cells, ctx, rng):
    g = [ALPHA[x] if x >= 0 else None for x in cells]
    if None in g:
        if ctx.filler is not None:
            g = [ch or ctx.filler for ch in g]
        else:
            G = _geom(n)
            order = [c for c in range(n * n) if g[c] is None]
            rng.shuffle(order)
            reps = ctx.ext // n + 2
            for c in order:
                ok = False
                for ch in ctx.fill_order:
                    g[c] = ch
                    bad = False
                    for a, l in G.cl[c]:
                        s = "".join([g[x] or "." for x in G.lines[a][l][:n]])
                        if ctx.forb_re.search((s * reps)[:n + ctx.ext]):
                            bad = True
                            break
                    if not bad:
                        ok = True
                        break
                if not ok:
                    return None
    rows = ["".join(g[r * n:(r + 1) * n]) for r in range(n)]
    return rows if _verify(rows, ctx) else None


def _greedy(bd, order, prm, deadline):
    pool = set()
    W = bd.W
    if prm["ORDER"] == "mcv":
        pending = set(order)
        rnd = bd.rng.random
        while pending:
            if time.monotonic() > deadline:
                return None
            best, bc = -1, 1 << 60
            for i in pending:
                c = bd.count_options(i, bc)
                if c < bc or (c == bc and (W[i][2], rnd()) > (W[best][2], rnd())):
                    best, bc = i, c
                if bc == 0:
                    break
            pending.discard(best)
            if bc == 0 or not bd.insert_best(best, prm):
                pool.add(best)
    else:
        for i in order:
            if time.monotonic() > deadline:
                return None
            if not bd.insert_best(i, prm):
                pool.add(i)
    return pool


def _lns(n, W, init, deadline, rng, ctx, prm):
    """Try to place every word on an n x n torus. Returns (rows, P) or (None, None)."""
    bd = _Board(n, W, ctx, rng)
    m = len(W)
    K = [w[2] for w in W]
    rnd = rng.random
    order = []
    for i in range(m):
        if init is not None and init[i] is not None:
            bd.put(i, *init[i], check=False)
        else:
            order.append(i)
    order.sort(key=lambda i: (-K[i], rnd()))
    pool = _greedy(bd, order, prm, deadline)
    if pool is None:
        return None, None
    if prm.get("GREEDY_ONLY"):
        return sum(K[i] for i in pool), None

    TEMP, TABU, TABU_PEN, OV_W, MU, ESAMP = (prm["TEMP"], prm["TABU"], prm["TABU_PEN"],
                                            prm["OV_W"], prm["MU"], prm["ESAMP"])
    RR = prm.get("RR", 0.0)
    RAD = prm.get("RAD", 0)
    tabu = [-10 ** 9] * m
    f = sum(K[i] for i in pool)
    it = 0
    while True:
        if not pool:
            rows = _fill_and_verify(n, bd.cells, ctx, rng)
            if rows is not None:
                return rows, bd.P[:]
            i = int(rnd() * m)
            bd.take(i)
            pool.add(i)
            f = sum(K[i] for i in pool)
        it += 1
        if not it & 7 and time.monotonic() > deadline:
            return None, None
        if TRACE is not None and not it % 100:
            TRACE.append((it, f, len(pool)))
        if rnd() < RR:
            # ruin & recreate: rip out every word crossing a random window, greedy re-insert
            pool_before = set(pool)
            f_before = f
            e_before = _pc(bd.filled)
            bd.log = []
            cc = int(rnd() * n * n)
            r0, c0 = divmod(cc, n)
            rad = RAD if RAD else 1 + int(rnd() * 3)
            victims = set()
            for dr in range(-rad, rad + 1):
                for dc in range(-rad, rad + 1):
                    victims.update(bd.own[((r0 + dr) % n) * n + (c0 + dc) % n])
            for v in victims:
                bd.take(v)
                pool.add(v)
            for v in sorted(pool, key=lambda i: (-K[i] - 2.5 * rnd())):
                if bd.insert_best(v, prm):
                    pool.discard(v)
            log = bd.log
            bd.log = None
            f = sum(K[i] for i in pool)
            dJ = (f - f_before) + MU * (_pc(bd.filled) - e_before)
            if dJ <= 0 or rnd() < math.exp(-dJ / TEMP):
                continue
            for op in reversed(log):
                if op[0] == 0:
                    bd.take(op[1])
                else:
                    bd.put(op[1], op[2], op[3], op[4], check=False)
            pool = pool_before
            f = f_before
            continue
        pl = list(pool)
        u = pl[int(rnd() * len(pl))]
        if bd.insert_best(u, prm):
            pool.discard(u)
            f -= K[u]
            continue
        one, two = bd.mismatch_sets(u)
        src = one or two
        if not src:
            continue
        cands = []
        for a, rev, mask in src:
            for b in _bits(mask):
                cands.append((a, b, rev))
        if len(cands) > ESAMP:
            cands = rng.sample(cands, ESAMP)
        wd = W[u]
        best = None
        bestc = 1e18
        cells = bd.cells
        own = bd.own
        for a, b, rev in cands:
            s = wd[1] if rev else wd[0]
            bl = set()
            ov = 0
            for c, x in zip(bd._path(a, b, wd[2]), s):
                y = cells[c]
                if y >= 0:
                    if y != x:
                        bl.update(own[c])
                    else:
                        ov += 1
            cost = -OV_W * ov + rnd()
            for bb in bl:
                cost += K[bb]
                if it - tabu[bb] < TABU:
                    cost += TABU_PEN
            if cost < bestc:
                bestc = cost
                best = (a, b, rev, bl)
        a, b, rev, blockers = best
        pool_before = set(pool)
        f_before = f
        e_before = _pc(bd.filled)
        bd.log = []
        for bb in blockers:
            bd.take(bb)
            pool.add(bb)
        ok = bd.put(u, a, b, rev)
        if ok:
            pool.discard(u)
            tabu[u] = it
            for bb in sorted(blockers, key=lambda i: -K[i]):
                tabu[bb] = it
                if bd.insert_best(bb, prm):
                    pool.discard(bb)
            for v in sorted(pool, key=lambda i: -K[i]):
                if v not in blockers and bd.insert_best(v, prm):
                    pool.discard(v)
        log = bd.log
        bd.log = None
        f = sum(K[i] for i in pool)
        dJ = (f - f_before) + MU * (_pc(bd.filled) - e_before)
        if ok and (dJ <= 0 or rnd() < math.exp(-dJ / TEMP)):
            continue
        for op in reversed(log):
            if op[0] == 0:
                bd.take(op[1])
            else:
                bd.put(op[1], op[2], op[3], op[4], check=False)
        pool = pool_before
        f = f_before


def _shrink(n_old, W, P_old, rng):
    """Warm start for n_old-1: delete the row and column crossed by the fewest letters."""
    G = _geom(n_old)
    n = n_old - 1
    Gn = _geom(n)
    rowhit = [0.0] * n_old
    colhit = [0.0] * n_old
    info = []
    for i, (a, b, rev) in enumerate(P_old):
        k = W[i][2]
        l, t = divmod(b, 2 * n_old)
        cells = G.lines[a][l][t:t + k]
        rows = {c // n_old for c in cells}
        cols = {c % n_old for c in cells}
        for r in rows:
            rowhit[r] += k
        for c in cols:
            colhit[c] += k
        info.append((cells[0], a, rev, rows, cols))
    R = min(range(n_old), key=lambda r: (rowhit[r], rng.random()))
    C = min(range(n_old), key=lambda c: (colhit[c], rng.random()))
    init = []
    for (s, a, rev, rows, cols) in info:
        if R in rows or C in cols:
            init.append(None)
            continue
        r, c = divmod(s, n_old)
        r -= r > R
        c -= c > C
        l, t = Gn.where[r * n + c][a]
        init.append((a, 2 * n * l + t, rev))
    return init


def _fallback(words, filler):
    n = max(max(map(len, words)), len(words))
    f = filler or "A"
    return [(words[r] if r < len(words) else "").ljust(n, f) for r in range(n)]


def _prepare(required_words, forbidden_words):
    req = _clean(required_words)
    forb = list(dict.fromkeys(_clean(forbidden_words)))
    forb_letters = set("".join(forb))
    ctx = _Ctx()
    ctx.req = req
    ctx.forb = forb
    ctx.filler = next((ch for ch in "QZXJKVWYBFGHMPUCDLOTNRISAE" if ch not in forb_letters), None)
    if not req:
        return ctx, None
    uniq = list(dict.fromkeys(req))
    ctx.uniq = uniq
    ctx.L = max(map(len, uniq))
    ctx.S = sum(map(len, req))
    core = []
    joined = ""
    for w in sorted(uniq, key=len, reverse=True):
        if w in joined or w[::-1] in joined:
            continue
        core.append(w)
        joined += "|" + w
    pats = set()
    for f in forb:
        pats.add(f)
        pats.add(f[::-1])
    Fmax = max(map(len, forb)) if forb else 0
    ctx.ext = max(ctx.L, Fmax) - 1
    ctx.forb_re = re.compile("|".join(sorted(pats, key=len, reverse=True))) if pats else None
    freq = {ch: 0 for ch in ALPHA}
    for f in forb:
        for ch in f:
            freq[ch] += 1
    ctx.fill_order = sorted(ALPHA, key=lambda ch: freq[ch])
    W = []
    for w in core:
        fw = tuple(ord(ch) - 65 for ch in w)
        W.append((fw, fw[::-1], len(fw), w != w[::-1]))
    return ctx, W


def generate_grid(required_words, forbidden_words):
    try:
        return _generate(required_words, forbidden_words)
    except Exception:
        words = _clean(required_words) or ["A"]
        return _fallback(list(dict.fromkeys(words)), None)


def _generate(required_words, forbidden_words):
    t0 = time.monotonic()
    deadline = t0 + TIME_BUDGET - END_RESERVE
    rng = random.Random(SEED)
    ctx, W = _prepare(required_words, forbidden_words)
    if W is None:
        for ch in ALPHA:
            if not any(set(f) == {ch} for f in ctx.forb):
                return [ch]
        return ["A"]
    if ctx.forb_re is not None and any(ctx.forb_re.search(w) for w in ctx.uniq):
        return _fallback(ctx.uniq, ctx.filler)  # impossible instance

    L, S = ctx.L, ctx.S
    n_stop = max(L, math.isqrt(int(S / 1.7)))  # any N <= floor(sqrt(S/1.7)) already scores 100
    S_core = sum(w[2] for w in W)

    best_rows = None
    best_P = None
    n = max(L, math.isqrt(int(S_core / 1.15)))
    while time.monotonic() < deadline:
        slice_end = min(deadline, time.monotonic() + 0.15 + 0.0005 * S_core)
        rows, P = _lns(n, W, None, slice_end, rng, ctx, PRM)
        if rows is not None:
            best_rows, best_P = rows, P
            break
        n += 1
    while best_rows is not None and len(best_rows) > n_stop and time.monotonic() < deadline:
        n_old = len(best_rows)
        init = _shrink(n_old, W, best_P, rng)
        rows, P = _lns(n_old - 1, W, init, deadline, rng, ctx, PRM)
        if rows is None:
            break
        best_rows, best_P = rows, P

    if best_rows is None:
        return _fallback(ctx.uniq, ctx.filler)
    return best_rows
