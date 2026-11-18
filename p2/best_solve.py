import random
import time

CONFIG = {'TIME_BUDGET': 8.0,
 'START_DENSITY': 1.15,
 'TOP_CANDIDATES': 12,
 'RANDOM_TRIES': 400,
 'TOUCH_WEIGHT': 1.0,
 'BEST_FIT_SAMPLE': 6,
 'MAX_BLOCKERS': 3,
 'MAX_REPAIRS': 40,
 'PORTFOLIO': [('longest_first', 'shared')],
 'SEED': 1,
 'TIME_MARGIN': 0.035,
 'FALLBACK_RESERVE': 0.2,
 'LIGHT_SHUFFLE_PROBABILITY': 0.25,
 'CROSSING_BONUS': 0.5,
 'FUTURE_BONUS': 0.05,
 'REPAIR_SAMPLE': 2000}

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIRS = ((0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, -1), (-1, 1))


build_attempts = 0


def check(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("No verified grid before the deadline")


def clean(words, deadline):
    result = {}
    for word in words:
        check(deadline)
        if isinstance(word, str):
            word = word.strip().upper()
            if word.isascii() and word.isalpha():
                result[word] = None
    return list(result)


def big_string(grid, rep, deadline=float("inf")):
    lines = []
    left = []
    right = []
    for k, row in enumerate(grid):
        check(deadline)
        lines.append("".join(row) * rep)
        left.append(row[k:] + row[:k])
        right.append(row[-k:] + row[:-k])
    for rows in (grid, left, right):
        check(deadline)
        for line in zip(*rows):
            check(deadline)
            lines.append("".join(line) * rep)
    return "|".join(lines)


def generate_grid(required_words, forbidden_words) -> list[str]:
    global build_attempts
    build_attempts = 0
    end = time.monotonic() + min(8.0, CONFIG["TIME_BUDGET"]) - CONFIG["TIME_MARGIN"]
    required = clean(required_words, end)
    forbidden = clean(forbidden_words, end)
    if not required:
        if "A" in forbidden or any_a_cycle(forbidden, end):
            raise ValueError('The prescribed ["A"] grid violates a forbidden word')
        return ["A"]

    required.sort(key=len, reverse=True)
    longest = len(required[0])
    total = 0
    forbidden_max = 0
    used = set()
    patterns = set()
    for word in forbidden:
        check(end)
        forbidden_max = max(forbidden_max, len(word))
        used.update(word)
        patterns.update((word, word[::-1]))
    for word in required:
        check(end)
        total += len(word)
        for pattern in patterns:
            check(end)
            if pattern in word:
                raise ValueError("A required word contains a forbidden fragment")
    filler = None
    for letter in "QXZJKVWY" + ALPHABET:
        check(end)
        if letter not in used:
            filler = letter
            break
    rng = random.Random(CONFIG["SEED"])

    def has_forbidden(grid, deadline):
        if patterns:
            lines = big_string(grid, 2 + forbidden_max // len(grid), deadline)
            for pattern in patterns:
                check(deadline)
                if pattern in lines:
                    return True
        return False

    def verify(grid, deadline):
        if has_forbidden(grid, deadline):
            return None
        lines = big_string(grid, 2, deadline)
        for word in required:
            check(deadline)
            if word not in lines and word[::-1] not in lines:
                return None
        result = []
        for row in grid:
            check(deadline)
            result.append("".join(row))
        return result

    def try_build(order, placement_rule, n, deadline):
        global build_attempts
        build_attempts += 1
        grid = []
        pos = {}
        for _ in range(n):
            check(deadline)
            grid.append(["."] * n)

        # A bit represents one grid cell. Union counts shared neighbours once.
        occupied = 0
        neighbours = []
        for r in range(n):
            check(deadline)
            masks = []
            for c in range(n):
                check(deadline)
                mask = 0
                for dr, dc in DIRS:
                    check(deadline)
                    mask |= 1 << (((r + dr) % n) * n + (c + dc) % n)
                masks.append(mask)
            neighbours.append(masks)

        def rank(word, start):
            r, c, dr, dc = start
            overlap = 0
            adjacent = 0
            for letter in word:
                check(deadline)
                cell = grid[r][c]
                if cell == letter:
                    overlap += 1
                elif cell == ".":
                    adjacent |= neighbours[r][c]
                else:
                    return None
                r, c = (r + dr) % n, (c + dc) % n
            if overlap == len(word):
                return None
            touching = (occupied & adjacent).bit_count()
            return placement_rule(overlap), touching, rng.random(), start

        def place(word, r, c, dr, dc):
            nonlocal occupied
            written = []
            for letter in word:
                check(deadline)
                if grid[r][c] == ".":
                    grid[r][c] = letter
                    written.append((r, c))
                r, c = (r + dr) % n, (c + dc) % n
            if has_forbidden(grid, deadline):
                for r, c in written:
                    check(deadline)
                    grid[r][c] = "."
                return False
            for r, c in written:
                check(deadline)
                occupied |= 1 << (r * n + c)
                pos.setdefault(grid[r][c], []).append((r, c))
            return True

        for word in order:
            check(deadline)
            lines = big_string(grid, 2, deadline)
            if word in lines or word[::-1] in lines:
                continue
            ranked = []
            seen = set()
            for k, letter in enumerate(word):
                check(deadline)
                for r, c in pos.get(letter, ()):
                    check(deadline)
                    for dr, dc in DIRS:
                        check(deadline)
                        start = ((r-k*dr) % n, (c-k*dc) % n, dr, dc)
                        if start in seen:
                            continue
                        seen.add(start)
                        entry = rank(word, start)
                        if entry is not None:
                            ranked.append(entry)
            ranked.sort(reverse=True)
            for _, _, _, start in ranked[:CONFIG["TOP_CANDIDATES"]]:
                check(deadline)
                if place(word, *start):
                    break
            else:
                seen.clear()
                sampled = []
                for _ in range(CONFIG["RANDOM_TRIES"]):
                    check(deadline)
                    start = (rng.randrange(n), rng.randrange(n), *rng.choice(DIRS))
                    if start in seen:
                        continue
                    seen.add(start)
                    entry = rank(word, start)
                    if entry is not None:
                        sampled.append(entry)
                        if not occupied:
                            # All starts tie on an empty torus.
                            break
                sampled.sort(reverse=True)
                for _, _, _, start in sampled:
                    check(deadline)
                    if place(word, *start):
                        break
                else:
                    return None

        for row in grid:
            check(deadline)
            for c, cell in enumerate(row):
                check(deadline)
                if cell != ".":
                    continue
                if filler:
                    row[c] = filler
                    continue
                for letter in rng.sample(ALPHABET, 26):
                    check(deadline)
                    row[c] = letter
                    if not has_forbidden(grid, deadline):
                        break
                else:
                    return None
        return verify(grid, deadline)

    target = longest
    while 17 * target * target < 10 * total:
        check(end)
        target += 1
    n = target
    while total / (n * n) > CONFIG["START_DENSITY"]:
        check(end)
        n += 1

    best = None
    try:
        while best is None:
            check(end - CONFIG["FALLBACK_RESERVE"])
            best = try_build(required, int, n, end - CONFIG["FALLBACK_RESERVE"])
            n += 1
    except TimeoutError:
        pass
    if best is None and filler:
        n = max(target, len(required))
        grid = []
        for r in range(n):
            check(end)
            word = required[r] if r < len(required) else ""
            grid.append(list(word.ljust(n, filler)))
        best = verify(grid, end)
    try:
        while best is not None and len(best) > target:
            check(end)
            candidate = try_build(required, int, len(best) - 1, end)
            if candidate is not None:
                best = candidate
    except TimeoutError:
        pass
    if best is None:
        raise TimeoutError("No verified grid found")
    return best


def any_a_cycle(words, deadline):
    for word in words:
        check(deadline)
        if word.strip("A") == "":
            return True
    return False
