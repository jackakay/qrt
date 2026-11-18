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
 'PORTFOLIO': [['longest_first', 'shared']],
 'SEED': 1,
 'TIME_MARGIN': 0.035,
 'FALLBACK_RESERVE': 0.2,
 'LIGHT_SHUFFLE_PROBABILITY': 0.25,
 'CROSSING_BONUS': 0.5,
 'FUTURE_BONUS': 0.05,
 'REPAIR_SAMPLE': 2000,
 'BRANCH_WIDTH': 6,
 'BACKTRACK_PATIENCE': 40,
 'BEAM_WIDTH': 12,
 'BEAM_CHILDREN': 4,
 'EXPECTED_NEW': 0.7,
 'BEAM_NOISE': 1.5,
 'TINY_LETTERS': 40,
 'TINY_NODES': 48,
 'TINY_RESTARTS': 32,
 'TINY_RESTART_SECONDS': 0.06}

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


def tiny_grid(words, filler, has_forbidden, verify, best, deadline):
    """Visit sizes in order, exhaust word placements, then exhaust safe fillings."""
    needed = {}
    for word in words:
        counts = {}
        for ch in word:
            counts[ch] = counts.get(ch, 0) + 1
        for ch, count in counts.items():
            needed[ch] = max(needed.get(ch, 0), count)
    n = len(words[0])
    minimum_cells = sum(needed.values())
    while n*n < minimum_cells:
        n += 1

    rng = random.Random(CONFIG["SEED"])

    def placements(grid, word, first, randomize=False):
        check(deadline)
        text = big_string(grid, 2, deadline)
        if word in text or word[::-1] in text:
            yield ()
            return
        # Translation fixes the first start. Rotations and reflections leave
        # just two distinct direction classes, axial and diagonal.
        extent = 1 if first else n
        directions = ((0,1),(1,1)) if first else DIRS
        if len(word) == 1:
            directions = ((0,1),)
        origin = rng.randrange(extent*extent) if randomize else 0
        if randomize:
            directions = rng.sample(directions,len(directions))
        for index in range(extent*extent):
            r,c = divmod((index+origin) % (extent*extent),extent)
            check(deadline)
            for dr,dc in directions:
                rr,cc = r,c
                written = []
                for ch in word:
                    old = grid[rr][cc]
                    if old == ".":
                        written.append((rr,cc,ch))
                    elif old != ch:
                        break
                    rr,cc = (rr+dr)%n,(cc+dc)%n
                else:
                    yield written

    def filled_grid(grid):
        empty = []
        for r,row in enumerate(grid):
            check(deadline)
            for c,ch in enumerate(row):
                if ch == ".":
                    empty.append((r,c))
        if filler:
            for r,c in empty:
                grid[r][c] = filler
            answer = verify(grid,deadline)
            for r,c in empty:
                grid[r][c] = "."
            return answer
        next_letter = [0]*len(empty)
        depth = 0
        while depth >= 0:
            check(deadline)
            if depth == len(empty):
                return verify(grid,deadline)
            r,c = empty[depth]
            if next_letter[depth] == len(ALPHABET):
                grid[r][c] = "."
                next_letter[depth] = 0
                depth -= 1
                continue
            grid[r][c] = ALPHABET[next_letter[depth]]
            next_letter[depth] += 1
            if not has_forbidden(grid,deadline):
                depth += 1
        return None

    def search_size(order, randomized, stop):
        grid = []
        for _ in range(n):
            grid.append(["."]*n)
        stack = [[placements(grid,order[0],True,randomized),()]]
        nodes = 0
        while stack:
            check(deadline)
            if randomized and (nodes >= CONFIG["TINY_NODES"] or time.monotonic() >= stop):
                return None
            nodes += 1
            choices,previous = stack[-1]
            for r,c,ch in previous:
                grid[r][c] = "."
            written = next(choices,None)
            if written is None:
                stack.pop()
                continue
            for r,c,ch in written:
                grid[r][c] = ch
            stack[-1][1] = written
            if has_forbidden(grid,deadline):
                continue
            if len(stack) == len(order):
                answer = filled_grid(grid)
                if answer is not None:
                    return answer
            else:
                stack.append([placements(grid,order[len(stack)],False,randomized),()])
        return None

    while best is None or n < len(best):
        check(deadline)
        stop = min(deadline,time.monotonic()+CONFIG["TINY_RESTART_SECONDS"])
        order = list(words)
        for _ in range(CONFIG["TINY_RESTARTS"]):
            if time.monotonic() >= stop:
                break
            rng.shuffle(order)
            answer = search_size(order,True,stop)
            if answer is not None:
                return answer
        answer = search_size(words,False,deadline)
        if answer is not None:
            return answer
        n += 1
    return best


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

    geometry_cache = {}

    def geometry(n, deadline):
        if n in geometry_cache:
            return geometry_cache[n]
        masks, neighbours = [], []
        lines = [[], [], [], []]
        starts = 0
        for r in range(n):
            check(deadline)
            starts |= ((1 << n)-1) << (2*n*r)
            for c in range(n):
                bits = []
                for line, offset in ((r,c),(c,r),((c-r)%n,r),((c+r)%n,r)):
                    bits.append(((1<<n)+1) << (2*n*line+offset))
                masks.append(bits)
                adjacent = 0
                for dr, dc in DIRS:
                    adjacent |= 1 << (((r+dr)%n)*n+(c+dc)%n)
                neighbours.append(adjacent)
        for axis, (dr,dc) in enumerate(DIRS[:4]):
            for line in range(n):
                check(deadline)
                r, c = (line,0) if axis == 0 else (0,line)
                cells = []
                for _ in range(n):
                    cells.append(r*n+c)
                    r,c = (r+dr)%n, (c+dc)%n
                lines[axis].append(cells*2)
        geometry_cache[n] = starts, masks, neighbours, lines
        return geometry_cache[n]

    spellings = {}
    for word in required:
        spellings[word] = (word, word[::-1])

    domain_cache = {}

    def line_domains(n, deadline):
        if n in domain_cache:
            return domain_cache[n]
        # A lane holds all forward and backward starts for one word on one line.
        width = 1 << (max(2*n,(8*n*n).bit_length())-1).bit_length()
        lanes = 0
        for i in range(len(required)):
            lanes |= 1 << (i*width)
        full = lanes*((1 << (2*n))-1)
        allowed = []
        for offset in range(n):
            check(deadline)
            hits = {}
            touched = 0
            for i,word in enumerate(required):
                for direction,spelling in enumerate(spellings[word]):
                    for k,ch in enumerate(spelling):
                        bit = 1 << (i*width+direction*n+(offset-k)%n)
                        touched |= bit
                        hits[ch] = hits.get(ch,0) | bit
            row = {}
            for ch in ALPHABET:
                row[ch] = (full ^ touched) | hits.get(ch,0)
            allowed.append(row)
        stages = []
        group = 1
        while group < width:
            pattern = ((1 << width)-1)//((1 << group)+1)
            stages.append((group,pattern*lanes))
            group *= 2
        domain_cache[n] = width, lanes, full, allowed, stages
        return domain_cache[n]

    def backtrack(n, deadline):
        global build_attempts
        build_attempts += 1
        starts, cell_masks, neighbours, lines = geometry(n,deadline)
        vacant = [(1 << (2*n*n))-1]*4
        letters = [{},{},{},{}]
        cells = ["."]*(n*n)
        filled = 0
        pending = set(required)

        width, lanes, full, allowed, stages = line_domains(n,deadline)
        live = [full]*(4*n)
        totals = lanes*(8*n*n)
        one_direction = (1 << n)-1

        def filter_domains(written):
            nonlocal totals
            saved = {}
            for cell,ch in written:
                r,c = divmod(cell,n)
                for line,offset in ((r,c),(n+c,r),(2*n+(c-r)%n,r),(3*n+(c+r)%n,r)):
                    old = live[line]
                    new = old & allowed[offset][ch]
                    if old != new:
                        saved.setdefault(line,old)
                        live[line] = new
            before = totals
            for line,old in saved.items():
                lost = old ^ live[line]
                # Parallel population count within every word's lane.
                for group,mask in stages:
                    lost = (lost & mask) + ((lost >> group) & mask)
                totals -= lost
            return before,saved

        def domains():
            fewest = 8*n*n+1
            winner = None
            counts = totals.to_bytes((width*len(required)+7)//8,"little")
            for i,word in enumerate(required):
                if word not in pending:
                    continue
                if width >= 8:
                    start = i*(width//8)
                    count = int.from_bytes(counts[start:start+width//8],"little")
                else:
                    count = (totals >> (i*width)) & ((1 << width)-1)
                if not count:
                    return None,None
                if count < fewest:
                    fewest, winner, shift = count, word, i*width
            options = []
            for axis in range(4):
                forward = reverse = 0
                for line in range(n):
                    lane = live[axis*n+line] >> shift
                    forward |= (lane & one_direction) << (2*n*line)
                    reverse |= ((lane >> n) & one_direction) << (2*n*line)
                if forward:
                    options.append((axis,winner,forward))
                if reverse:
                    options.append((axis,spellings[winner][1],reverse))
            return winner,options

        def placements(word, options):
            ranked = []
            for axis, spelling, choices in options:
                check(deadline)
                # Choose starts with maximum overlap across this line family.
                counts = []
                for k in range(len(word)):
                    carry = choices & ~(vacant[axis] >> k)
                    for j, plane in enumerate(counts):
                        if not carry:
                            break
                        counts[j] = plane ^ carry
                        carry &= plane
                    if carry:
                        counts.append(carry)
                sampled = 0
                while choices and sampled < CONFIG["BRANCH_WIDTH"]:
                    mask = choices
                    overlap = 0
                    for j in range(len(counts)-1,-1,-1):
                        more = mask & counts[j]
                        if more:
                            mask = more
                            overlap |= 1 << j
                    while mask and sampled < CONFIG["BRANCH_WIDTH"]:
                        pick = mask
                        while pick & (pick-1):
                            half = pick & rng.getrandbits(pick.bit_length())
                            if half:
                                pick = half
                        mask ^= pick
                        choices ^= pick
                        sampled += 1
                        line, offset = divmod(pick.bit_length()-1,2*n)
                        path = lines[axis][line][offset:offset+len(word)]
                        adjacent = 0
                        for cell in path:
                            if cells[cell] == ".":
                                adjacent |= neighbours[cell]
                        touching = (filled & adjacent).bit_count()
                        ranked.append((overlap,touching,rng.random(),path,spelling))
            ranked.sort(reverse=True)
            return ranked[:CONFIG["BRANCH_WIDTH"]]

        def toggle(written):
            nonlocal filled
            for cell, letter in written:
                filled ^= 1 << cell
                cells[cell] = letter if cells[cell] == "." else "."
                for axis, mask in enumerate(cell_masks[cell]):
                    vacant[axis] ^= mask
                    board = letters[axis]
                    board[letter] = board.get(letter,0) ^ mask

        def finish():
            grid = []
            for r in range(n):
                check(deadline)
                row = cells[r*n:(r+1)*n]
                grid.append(row)
            for row in grid:
                for j,ch in enumerate(row):
                    if ch == ".":
                        if filler:
                            row[j] = filler
                        else:
                            for letter in rng.sample(ALPHABET,26):
                                row[j] = letter
                                if not has_forbidden(grid,deadline):
                                    break
                            else:
                                return None
            return verify(grid,deadline)

        def snapshot():
            saved_letters = []
            for board in letters:
                saved_letters.append(board.copy())
            return (pending.copy(),cells.copy(),vacant.copy(),saved_letters,
                    filled,live.copy(),totals)

        beam = [(0.0,0.0,0,snapshot())]
        high = lanes << (width-1)
        for depth in range(len(required)):
            check(deadline)
            children = []
            for _,_,length_sum,state in beam:
                pending,cells,vacant,letters,filled,live,totals = state
                word,options = domains()
                if word is None:
                    continue
                pending.remove(word)
                branches = placements(word,options)
                if depth == 0:
                    branches = branches[:1]
                for _,_,_,path,spelling in branches[:CONFIG["BEAM_CHILDREN"]]:
                    check(deadline)
                    written = []
                    for cell,ch in zip(path,spelling):
                        if cells[cell] == ".":
                            written.append((cell,ch))
                    delta = filter_domains(written)
                    if (~totals & (totals-lanes) & high) == 0:
                        toggle(written)
                        if not pending:
                            result = finish()
                            if result is not None:
                                return result
                        else:
                            length = length_sum+len(word)
                            value = (CONFIG["EXPECTED_NEW"]*length - filled.bit_count()
                                     + rng.random()*CONFIG["BEAM_NOISE"])
                            children.append((value,rng.random(),length,snapshot()))
                        toggle(written)
                    totals,saved = delta
                    for line,old in saved.items():
                        live[line] = old
            if not children:
                return None
            children.sort(reverse=True)
            beam = children[:CONFIG["BEAM_WIDTH"]]
        return None

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
    if total < CONFIG["TINY_LETTERS"]:
        try:
            return tiny_grid(required, filler, has_forbidden, verify, best, end)
        except TimeoutError:
            if best is not None:
                return best
            raise
    try:
        while best is not None and len(best) > target:
            check(end)
            candidate = backtrack(len(best)-1,end)
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
