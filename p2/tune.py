"""Benchmark one candidate with two-seed confirmation. Run from any directory."""

import argparse
import ast
import csv
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import pprint
import statistics
import subprocess
import tempfile
import time
import traceback

import score

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "results.csv"
FIELDS = ("time", "label", "config", "mean_score", "mean_n", "per_case_n", "invalid",
          "slowest", "seed", "status", "solver_sha256", "cases")
EXTRA = {
    "constellations": """Andromeda Antlia Apus Aquarius Aquila Ara Aries Auriga Bootes Caelum
    Camelopardalis Cancer CanesVenatici CanisMajor CanisMinor Capricornus Carina Cassiopeia
    Centaurus Cepheus Cetus Chamaeleon Circinus Columba ComaBerenices Corvus Crater Crux Cygnus
    Delphinus Dorado Draco Equuleus Eridanus Fornax Gemini Grus Hercules Horologium Hydra
    Hydrus Indus Lacerta Leo LeoMinor Lepus Libra Lupus Lynx Lyra Mensa Microscopium Monoceros
    Musca Norma Octans Ophiuchus Orion Pavo Pegasus Perseus Phoenix Pictor Pisces PiscisAustrinus
    Puppis Pyxis Reticulum Sagitta Sagittarius Scorpius Sculptor Scutum Serpens Sextans Taurus
    Telescopium Triangulum Tucana UrsaMajor UrsaMinor Vela Virgo Volans Vulpecula""",
    "minerals": """actinolite albite allanite almandine amazonite amphibole anatase andalusite
    andesine anglesite anhydrite ankerite apatite apophyllite aragonite arsenopyrite augite
    aurichalcite azurite barite bauxite beryl biotite bornite brucite calcite carnelian
    cassiterite celestine cerussite chabazite chalcedony chalcopyrite chlorite chromite cinnabar
    clinozoisite cobaltite colemanite corundum covellite crocoite cuprite datolite diamond
    diopside dioptase dolomite elbaite enstatite epidote fluorite galena garnet goethite graphite
    gypsum halite hematite hornblende ilmenite jadeite jasper kaolinite kyanite labradorite
    lazurite lepidolite magnetite malachite marcasite microcline molybdenite muscovite olivine
    opal orthoclase pyrite quartz rhodonite rutile siderite sodalite spinel stibnite talc
    topaz tourmaline tremolite turquoise zircon zoisite""",
    "instruments": """accordion bagpipes balalaika banjo bassoon berimbau bongos bouzouki bugle
    carillon castanets celesta cello chimes cimbalom cithara cittern clarinet clavichord
    concertina contrabass cornet cornett cowbell crumhorn cymbals didgeridoo djembe dulcimer
    dulcian euphonium fiddle flugelhorn flute gamelan glockenspiel gong guitar guiro gusle
    handbell harmonica harmonium harp harpsichord heckelphone horn hurdygurdy kalimba kantele
    kettleDrum keyboard koto lute lyre mandola mandolin maracas marimba melodica metallophone
    musette oboe ocarina organ oud panpipes piano piccolo psaltery recorder rebec sackbut
    santur sarangi sarod saxophone shamisen shawm sheng sitar spinet tabla tambourine theorbo
    timpani tiple triangle trombone trumpet tuba ukulele vibraphone viola violin violone
    whistle xylophone zither""",
    "trees": """acacia alder almond apple apricot arborvitae aspen avocado baobab basswood
    beech birch blackthorn boxwood breadfruit buckeye butternut cacao camphor carob cashew
    casuarina catalpa cedar cherry chestnut chinquapin cinnamon clementine coconut coffeetree
    cottonwood crabapple cypress dogwood ebony elder elm eucalyptus fir ginkgo grapefruit
    grevillea guava hackberry hawthorn hazel hemlock hickory holly hornbeam horsechestnut
    ironwood jacaranda juniper kapok larch laurel lemon lime linden locust madrone magnolia
    mahogany mango mangrove maple medlar mimosa mulberry myrtle nectarine nutmeg olive orange
    palm papaya peach pear pecan persimmon pine pistachio plane plum pomegranate poplar quince
    redbud redwood rowan sassafras sequoia spruce sycamore tamarack tamarind tuliptree walnut
    willow yellowwood yew""",
    "foods": """baguette baklava barley beetroot biscuit blackberry blueberry bokchoy bread
    brioche broccoli brownie bulgur burrito cabbage calzone cannelloni cantaloupe caper
    caramel carrot cashew cauliflower celery cheddar chickpea chocolate chutney ciabatta
    cinnamon coconut couscous cranberry croissant cucumber cupcake currant custard daikon
    dumpling eggplant endive falafel farfalle fennel focaccia frittata gnocchi granola
    grapefruit guacamole halibut hazelnut hummus jalapeno kohlrabi kumquat lasagna leek
    lentil lettuce linguine lychee macaroni mango marmalade meatball millet mozzarella muffin
    mushroom mustard nectarine noodle oatmeal olive omelette onion oregano pancake papaya
    paprika parsley parsnip pastry peach peanut pecan pepper pesto pickles pineapple plantain
    polenta popcorn potato pretzel pumpkin quinoa radish raisin raspberry ravioli rhubarb
    risotto rosemary saffron shallot sorbet spinach squash strawberry tahini tamarind tempeh
    tomato tortilla truffle turnip vanilla vinegar waffle walnut yoghurt zucchini""",
}


def cases():
    themes = score.THEMES.copy()
    for name, source in EXTRA.items():
        words = []
        for word in source.split():
            if 4 <= len(word) <= 12:
                words.append(word)
        themes[name] = " ".join(words)
    result = score.themed_cases(themes)
    for name, words, forbidden in result:
        if not (60 <= len(words) <= 80 and 460 <= sum(map(len, words)) <= 540):
            raise ValueError(f"Unrepresentative case {name}")
    return result


def namespace(source):
    ns = {"__name__": "trial_solver"}
    exec(compile(source, "<trial_solver>", "exec"), ns)
    return ns


def worker(job):
    source, config, case = job
    ns = namespace(source)
    ns["CONFIG"].update(config)
    name, words, forbidden = case
    start = time.monotonic()
    try:
        grid = ns["generate_grid"](words, forbidden)
        elapsed = time.monotonic() - start
        points, detail = score.score(words, forbidden, grid)
        n = len(grid)
    except Exception:
        elapsed = time.monotonic() - start
        n, points, detail = 0, 0.0, traceback.format_exc()
    return dict(name=name, score=points, n=n, dt=elapsed, detail=detail,
                attempts=ns["build_attempts"], winner=ns.get("winning_pair"))


def measure(source, config):
    jobs = []
    for case in cases():
        jobs.append((source, config, case))
    # One fresh worker per case, even if a trial fails immediately.
    with multiprocessing.get_context("spawn").Pool(len(jobs), maxtasksperchild=1) as pool:
        rows = pool.map_async(worker, jobs, chunksize=1).get(timeout=35)
    sizes = {}
    scores = []
    slowest = 0.0
    invalid = 0
    for row in rows:
        scores.append(row["score"])
        if row["score"] == 0:
            invalid += 1
        sizes[row["name"]] = row["n"]
        slowest = max(slowest, row["dt"])
    return dict(mean_score=statistics.mean(scores), mean_n=statistics.mean(sizes.values()),
                per_case_n=sizes, invalid=invalid, slowest=slowest, cases=rows)


def log(label, source, config, measured, status):
    row = dict(measured)
    row.update(time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), label=label,
               config=config, seed=config["SEED"], status=status,
               solver_sha256=hashlib.sha256(source.encode()).hexdigest())
    for key in ("config", "cases", "per_case_n"):
        row[key] = json.dumps(row[key], sort_keys=True)
    new = not HISTORY.exists()
    with HISTORY.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)
    counts = {}
    for n in measured["per_case_n"].values():
        counts[n] = counts.get(n, 0) + 1
    print(f"{label} seed {row['seed']}: {row['mean_score']:.2f} {status}; "
          f"mean N {row['mean_n']:.2f}, sizes {dict(sorted(counts.items()))}, "
          f"invalid {row['invalid']}, slowest {row['slowest']:.3f}s", flush=True)


def embedded(source, config):
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "CONFIG":
            lines = source.splitlines(keepends=True)
            replacement = "CONFIG = " + pprint.pformat(config, sort_dicts=False) + "\n"
            return "".join(lines[:node.lineno-1]) + replacement + "".join(lines[node.end_lineno:])
    raise ValueError("Missing CONFIG")


def atomic_write(path, data):
    tmp = ROOT / ("." + path.name + ".new")
    tmp.write_text(data)
    tmp.replace(path)


def publish():
    # A private index based on the remote branch preserves the user's main checkout.
    files = ["solve.py", "best_solve.py", "best_config.json", "score.py", "tune.py", "results.csv"]
    def git(*args, env=None):
        proc = subprocess.run(["git", *args], cwd=ROOT, env=env, check=True, text=True,
                              stdout=subprocess.PIPE, timeout=15)
        return proc.stdout.strip()
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(Path(tmp) / "index")
        git("fetch", "origin", "ananth")
        parent = git("rev-parse", "FETCH_HEAD")
        git("read-tree", parent, env=env)
        git("add", "--", *files, env=env)
        tree = git("write-tree", env=env)
        if tree != git("rev-parse", parent + "^{tree}"):
            state = best_scores()
            commit = git("commit-tree", tree, "-p", parent, "-m",
                         f"p2: verified solver score {min(state.values()):.2f}")
            git("push", "origin", commit + ":refs/heads/ananth")


def best_scores():
    scores = {}
    if HISTORY.exists():
        with HISTORY.open(newline="") as handle:
            pending = None
            for row in csv.DictReader(handle):
                if row["status"] == "confirming":
                    pending = row
                if row["status"] == "accepted" and pending:
                    scores = {1: float(pending["mean_score"]), 2: float(row["mean_score"])}
    return scores


def trial(label, source, settings, local):
    previous = best_scores()
    config = namespace(source)["CONFIG"].copy()
    config.update(settings)
    config["SEED"] = 1
    source = embedded(source, config)
    for seed in (1, 2):
        run_config = config.copy()
        run_config["SEED"] = seed
        result = measure(source, run_config)
        if (result["invalid"] or result["slowest"] > 8.3 or
                previous and result["mean_score"] < previous[seed] + 0.5):
            log(label, source, run_config, result, "rejected")
            return False
        log(label, source, run_config, result, "confirming" if seed == 1 else "accepted")
        if seed == 1:
            first = result
    for filename in ("best_solve.py", "solve.py"):
        atomic_write(ROOT / filename, source)
    atomic_write(ROOT / "best_config.json", json.dumps(config, indent=2) + "\n")
    if not local:
        publish()
    print(f"NEW BEST {min(first['mean_score'],result['mean_score']):.2f}  "
          f"mean N {max(first['mean_n'],result['mean_n']):.2f}  -> p2/best_solve.py", flush=True)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--source", default="solve.py")
    parser.add_argument("--set", default="{}", type=json.loads)
    parser.add_argument("--local", action="store_true", help="Publish separately with tune.py publish")
    args = parser.parse_args()
    if args.label == "publish":
        publish()
    else:
        trial(args.label, (ROOT / args.source).read_text(), args.set, args.local)
