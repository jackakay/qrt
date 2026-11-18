import sys
import time
import random
import importlib

DIRS = [(0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, -1), (-1, 1)]


def occurs(grid, N, word):
    L = len(word)
    for r in range(N):
        for c in range(N):
            if grid[r][c] != word[0]:
                continue
            for dr, dc in DIRS:
                ok = True
                for i in range(L):
                    if grid[(r + i * dr) % N][(c + i * dc) % N] != word[i]:
                        ok = False
                        break
                if ok:
                    return True
    return False


def score(required, forbidden, grid):
    N = len(grid)
    longest = 0
    total = 0
    for w in required:
        total += len(w)
        if len(w) > longest:
            longest = len(w)
    if N < longest:
        return 0.0, "N smaller than longest word"
    for row in grid:
        if len(row) != N:
            return 0.0, "not square"
        for ch in row:
            if not ("A" <= ch <= "Z"):
                return 0.0, "non-letter cell"
    for w in required:
        if not occurs(grid, N, w):
            return 0.0, "missing " + w
    for w in forbidden:
        if occurs(grid, N, w):
            return 0.0, "forbidden " + w
    density = total / float(N * N)
    return 100.0 * min(1.0, density / 1.7), "N=%d density=%.3f" % (N, density)


def make_case(n_words, lo, hi, n_forbidden, seed, real_words):
    rng = random.Random(seed)
    req = []
    if real_words:
        pool = []
        for w in real_words:
            if lo <= len(w) <= hi:
                pool.append(w)
        req = rng.sample(pool, n_words)
        rest = []
        for w in real_words:
            if 3 <= len(w) <= 5:
                rest.append(w)
        forb = rng.sample(rest, n_forbidden)
    else:
        letters = "EEEEEEEEEEEETTTTTTTTTAAAAAAAAOOOOOOOIIIIIIINNNNNNNSSSSSSHHHHHHRRRRRRDDDDLLLLCCCUUUMMMWWFFGGYYPPBBVKJXQZ"
        for i in range(n_words):
            L = rng.randint(lo, hi)
            w = ""
            for j in range(L):
                w += rng.choice(letters)
            req.append(w)
        forb = []
        for i in range(n_forbidden):
            w = ""
            for j in range(rng.randint(3, 4)):
                w += rng.choice(letters)
            forb.append(w)
    clean = []
    for f in forb:
        bad = False
        for w in req:
            if f in w or f[::-1] in w:
                bad = True
        if not bad:
            clean.append(f)
    return req, clean


THEMES = {
    "rivers": """Amazon Orinoco Parana Uruguay Paraguay Tocantins Araguaia Madeira Tapajos Xingu
    Negro Solimoes Ucayali Maranon Magdalena Mississippi Missouri Arkansas Colorado Columbia
    Tennessee Potomac Delaware Hudson Susquehanna Allegheny Monongahela Willamette Sacramento
    Mackenzie Athabasca Saskatchewan Yukon Fraser Ottawa Danube Rhine Rhone Seine Thames
    Shannon Severn Tagus Douro Volga Dnieper Dniester Donets Vistula Elbe Loire
    Garonne Dordogne Drava Tigris Euphrates Jordan Indus Ganges Yamuna Brahmaputra Mekong
    Salween Irrawaddy Yangtze Huanghe Amur Lena Yenisei Angara Kolyma Limpopo Zambezi
    Okavango Orange Congo Niger Senegal Gambia Murray Darling Murrumbidgee Penobscot Shenandoah Cumberland Rappahannock Tennessee Tombigbee Patapsco Potomac Saginaw Wabash Pecos Brazos Salinas Tuolumne Truckee Merced""",
    "countries": """Albania Algeria Angola Argentina Armenia Australia Austria Azerbaijan Bahamas
    Bahrain Bangladesh Barbados Belarus Belgium Belize Benin Bhutan Bolivia Botswana Brazil
    Brunei Bulgaria Burundi Cambodia Cameroon Canada Chad Chile China Colombia Comoros Croatia
    Cuba Cyprus Denmark Djibouti Dominica Ecuador Egypt Eritrea Estonia Eswatini Ethiopia
    Finland France Gabon Gambia Georgia Germany Ghana Greece Grenada Guatemala Guinea Guyana
    Haiti Honduras Hungary Iceland India Indonesia Iran Iraq Ireland Israel Italy Jamaica Japan
    Jordan Kazakhstan Kenya Kiribati Kuwait Kyrgyzstan Laos Latvia Lebanon Lesotho Liberia Libya
    Lithuania Luxembourg Madagascar Malaysia Maldives Mauritius Mongolia Mozambique Nicaragua
    Pakistan Paraguay Portugal Singapore Slovakia Slovenia Suriname Tanzania Thailand Zimbabwe""",
    "animals": """aardvark albatross alligator alpaca anaconda anchovy anteater antelope armadillo
    baboon badger bandicoot barracuda beaver bison blackbird bobcat bonobo buffalo butterfly
    capybara caracal caribou cassowary catfish chameleon cheetah chipmunk chinchilla cobra
    condor cormorant coyote crocodile cuttlefish dolphin dormouse dragonfly dugong echidna
    elephant falcon flamingo gazelle gecko gerbil gibbon giraffe gorilla grouper guanaco
    guillemot haddock hamster hedgehog heron hornbill hyena ibex iguana impala jaguar jellyfish
    kangaroo kestrel kingfisher koala lemur leopard lobster macaque manatee mandrill marmot
    meerkat mongoose narwhal octopus ocelot pangolin pelican penguin porcupine puffin raccoon
    raven salamander squirrel tapir tortoise walrus wombat zebra""",
    "elements": """hydrogen helium lithium beryllium boron carbon nitrogen oxygen fluorine neon
    sodium magnesium aluminium silicon phosphorus sulfur chlorine argon potassium calcium scandium
    titanium vanadium chromium manganese iron cobalt nickel copper zinc gallium germanium arsenic
    selenium bromine krypton rubidium strontium yttrium zirconium niobium molybdenum technetium
    ruthenium rhodium palladium silver cadmium indium tellurium iodine xenon caesium barium
    lanthanum cerium praseodymium neodymium promethium samarium europium gadolinium terbium
    dysprosium holmium erbium thulium ytterbium lutetium hafnium tantalum tungsten rhenium
    osmium iridium platinum gold mercury lead bismuth polonium astatine radon francium radium
    actinium thorium uranium neptunium plutonium""",
    "cities": """Aberdeen Adelaide Alexandria Algiers Amsterdam Ankara Athens Atlanta Auckland
    Baghdad Bangkok Barcelona Beijing Beirut Belfast Belgrade Berlin Birmingham Bogota Bologna
    Boston Brasilia Bremen Brisbane Bristol Brussels Bucharest Budapest Santiago Cairo Calgary
    Canberra Caracas Cardiff Casablanca Chennai Chicago Cologne Colombo Copenhagen Cordoba Dakar
    Dallas Damascus Delhi Denver Detroit Dublin Durban Edinburgh Florence Frankfurt Geneva Genoa
    Glasgow Guadalajara Hamburg Hanoi Harare Havana Helsinki Houston Istanbul Jakarta Jerusalem
    Johannesburg Kabul Kampala Karachi Kathmandu Khartoum Kingston Kinshasa Kolkata Kyoto Lagos
    Lahore Leipzig Lima Lisbon Liverpool London Madrid Manila Melbourne Milan Montreal Mumbai
    Munich Nairobi Naples Osaka Ottawa Palermo Paris Prague Quito Reykjavik Seattle Shanghai
    Stockholm Sydney Toronto Valencia Venice Vienna Warsaw Zagreb Zurich""",
}


def themed_cases(themes=THEMES, target_letters=575):
    cases = []
    for index, (name, source) in enumerate(themes.items()):
        rng = random.Random(101 + index)
        pool = list(dict.fromkeys(source.upper().split()))
        rng.shuffle(pool)
        required = []
        total = 0
        for word in pool:
            assert 4 <= len(word) <= 12
            if len(required) >= 60 and abs(total - target_letters) <= abs(total + len(word) - target_letters):
                break
            required.append(word)
            total += len(word)
            if len(required) == 92:
                break
        forbidden = []
        for word in rng.sample("ASH GEM ICE JET ORE SAP SKY TEA WAX HAY RYE INK DEW MUD OIL".split(), 15):
            if len(forbidden) == (0, 3, 5, 8, 10)[index % 5]:
                break
            for item in required:
                if word in item or word[::-1] in item:
                    break
            else:
                forbidden.append(word)
        cases.append((name, required, forbidden))
    return cases


def benchmark(mod, cases, label):
    points = sizes = attempts = invalid = 0
    elapsed = 0.0
    for name, req, forb in cases:
        t0 = time.monotonic()
        try:
            grid = mod.generate_grid(list(req), list(forb))
        except (ValueError, TimeoutError) as error:
            grid = []
            failure = str(error)
        else:
            failure = ""
        dt = time.monotonic() - t0
        s, info = score(req, forb, grid)
        builds = mod.build_attempts
        elapsed += dt
        attempts += builds
        points += s
        if s:
            sizes += len(grid)
        else:
            invalid += 1
        print("%-48s score %6.2f  %s  %.3fs  %.2f attempts/s %s" %
              (name, s, info, dt, builds / dt, failure))
    valid = len(cases) - invalid
    print("%s: average %.2f  average N %.2f  %.2f attempts/s  invalid %d/%d" %
          (label, points / len(cases), sizes / valid if valid else float("nan"),
           attempts / elapsed, invalid, len(cases)))


if __name__ == "__main__":
    mod = importlib.import_module(sys.argv[1])
    mod.CONFIG["TIME_BUDGET"] = 4.0
    real = []
    cases = [
        ("tiny example", ["ACE", "FIG", "OAK"], []),
    ]
    specs = [(20, 4, 8, 0), (40, 4, 9, 5), (70, 5, 10, 10), (120, 4, 10, 20), (60, 3, 6, 30)]
    seed = 1
    for n, lo, hi, nf in specs:
        req, forb = make_case(n, lo, hi, nf, seed, real)
        cases.append(("%s %d words len %d-%d, %d forbidden" % ("dict" if real else "random", n, lo, hi, len(forb)), req, forb))
        seed += 1
        req, forb = make_case(n, lo, hi, nf, seed, None)
        cases.append(("random %d words len %d-%d, %d forbidden" % (n, lo, hi, len(forb)), req, forb))
        seed += 1
    batch = sys.argv[2] if len(sys.argv) > 2 else "all"
    if batch == "all":
        benchmark(mod, cases, "Original")
    elif batch == "original-1":
        benchmark(mod, cases[:6], "Original 1")
    elif batch == "original-2":
        benchmark(mod, cases[6:], "Original 2")
    if batch in ("all", "themed"):
        benchmark(mod, themed_cases(), "Themed")
