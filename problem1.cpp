#include <bits/stdc++.h>
using namespace std;

// Increase this if the judge allows more time. It is a budget per invocation.
#ifndef PACK_TIME_MS
#define PACK_TIME_MS 1800
#endif

namespace square_packing {
using ll = long long;
using Area = __int128_t;
struct Rect { ll x, y, w, h; };
struct Item { ll s; int id; };
struct Point { ll x = 0, y = 0; };

class Solver {
    vector<Item> a;
    vector<Point> best;
    vector<ll> widths;
    Area total = 0, bestArea = (Area(1) << 125), lower;
    ll largest = 0, sumSides = 0, unit = 0, bestWidth = 0;
    bool bestTransposed = false;
    mutable unordered_map<ll,ll> heightBounds;
    int n;
    mt19937 rng{718293};
    chrono::steady_clock::time_point deadline;
    bool expired() const { return chrono::steady_clock::now() >= deadline; }
    static ll ceilDiv(Area x, ll y) { return (ll)((x + y - 1) / y); }
    static bool contains(const Rect &a, const Rect &b) {
        return a.x <= b.x && a.y <= b.y &&
               a.x + a.w >= b.x + b.w && a.y + a.h >= b.y + b.h;
    }
    static bool intersects(const Rect &a, const Rect &b) {
        return a.x < b.x+b.w && b.x < a.x+a.w &&
               a.y < b.y+b.h && b.y < a.y+a.h;
    }
    void accept(const vector<Point> &p) {
        ll w = 0, h = 0, minX = LLONG_MAX, minY = LLONG_MAX;
        for (int i = 0; i < n; ++i) {
            w = max(w, p[i].x + a[i].s);
            h = max(h, p[i].y + a[i].s);
            minX = min(minX,p[i].x); minY = min(minY,p[i].y);
        }
        w -= minX; h -= minY;
        for (int i = 0; i < n; ++i) {
            // The requested return type uses int coordinates.
            if (Area(p[i].x-minX)*unit > INT_MAX || Area(p[i].y-minY)*unit > INT_MAX) return;
        }
        Area area = Area(w)*h;
        if (area < bestArea) {
            bestArea = area; best = p; bestWidth = min(w,h); bestTransposed = w > h;
            for (Point &q : best) q.x -= minX, q.y -= minY;
        }
    }
    // Best-fit decreasing shelves give an inexpensive, always-valid incumbent.
    void shelves(ll width) {
        struct Shelf { ll y, height, used; };
        vector<Shelf> rows;
        set<pair<ll,int>> gaps;
        vector<Point> p(n);
        ll height = 0;
        for (int i = 0; i < n; ++i) {
            ll s = a[i].s;
            int row = -1;
            auto fit = gaps.lower_bound({s,-1});
            if (fit != gaps.end()) { row = fit->second; gaps.erase(fit); }
            if (row < 0) {
                row = (int)rows.size();
                rows.push_back({height, s, 0});
                height += s;
            }
            p[i] = {rows[row].used, rows[row].y};
            rows[row].used += s;
            gaps.insert({width-rows[row].used,row});
        }
        accept(p);
    }
    ll heightLowerBound(ll w) const {
        auto cached = heightBounds.find(w);
        if (cached != heightBounds.end()) return cached->second;
        ll h = max(largest, ceilDiv(total, w));
        Area sideSum = 0;
        for (int i = 0; i < n; ++i) {
            ll s = a[i].s, across = w/s;
            if (!across) return LLONG_MAX;
            sideSum += s;
            // At any horizontal cut at most 'across' of these squares fit.
            h = max(h, ceilDiv(sideSum, across));
            // Shrinking the first i+1 squares to side s gives another bound.
            h = max(h, ((i+across)/across)*s);
        }
        heightBounds[w] = h;
        return h;
    }
    // Maximal empty rectangles may overlap each other, but never placed squares.
    // Only newly generated rectangles need containment pruning.
    static void split(vector<Rect> &free, const Rect &used) {
        vector<Rect> kept, added;
        kept.reserve(free.size()+8);
        added.reserve(16);
        for (const Rect &r : free) {
            if (!intersects(r, used)) { kept.push_back(r); continue; }
            if (used.x > r.x) added.push_back({r.x,r.y,used.x-r.x,r.h});
            if (used.x+used.w < r.x+r.w)
                added.push_back({used.x+used.w,r.y,r.x+r.w-used.x-used.w,r.h});
            if (used.y > r.y) added.push_back({r.x,r.y,r.w,used.y-r.y});
            if (used.y+used.h < r.y+r.h)
                added.push_back({r.x,used.y+used.h,r.w,r.y+r.h-used.y-used.h});
        }
        for (const Rect &r : added) {
            bool redundant = false;
            for (const Rect &q : kept)
                if (contains(q,r)) { redundant = true; break; }
            if (redundant) continue;
            for (size_t j = 0; j < kept.size(); ) {
                if (contains(r,kept[j])) { kept[j] = kept.back(); kept.pop_back(); }
                else ++j;
            }
            kept.push_back(r);
        }
        free.swap(kept);
    }
    bool pack(ll w, ll h, const vector<int> &order, int mode, int corner = 0,
              bool repair = false, int destruction = 35) {
        vector<Rect> free{{0,0,w,h}};
        vector<Point> p(n);
        vector<char> fixed(n,0);
        ll usedW = 0, usedH = 0;
        if (repair && !best.empty()) {
            for (int i = 0; i < n; ++i) {
                if ((i & 15) == 0 && expired()) return false;
                Point q = best[i];
                if (bestTransposed) swap(q.x,q.y);
                ll s = a[i].s;
                if (q.x+s > w || q.y+s > h || rng()%100 < (unsigned)destruction) continue;
                fixed[i] = 1; p[i] = q;
                usedW = max(usedW,q.x+s); usedH = max(usedH,q.y+s);
                split(free,{q.x,q.y,s,s});
            }
        }
        vector<int> todo;
        for (int id : order) if (!fixed[id]) todo.push_back(id);
        multiset<pair<ll,int>> remaining;
        if (mode >= 5) for (int id : todo) remaining.insert({a[id].s,id});
        for (int k = 0; k < (int)todo.size(); ++k) {
            if ((k & 15) == 0 && expired()) return false;
            int id = todo[k], chosen = -1;
            ll s = a[id].s;
            array<Area,4> bestKey{{Area(1)<<125,0,0,0}};
            for (int j = 0; j < (int)free.size(); ++j) {
                const Rect &r = free[j];
                int candidate = id;
                if (mode >= 5) {
                    auto it = remaining.upper_bound({min(r.w,r.h),INT_MAX});
                    if (it == remaining.begin()) continue;
                    --it;
                    s = it->first; candidate = it->second;
                }
                if (s > r.w || s > r.h) continue;
                ll small = min(r.w-s,r.h-s), large = max(r.w-s,r.h-s);
                array<Area,4> key;
                if (mode == 0 || mode == 5) key = {small,large,r.y,r.x};
                else if (mode == 1 || mode == 6) key = {Area(r.w)*r.h-Area(s)*s,small,r.y,r.x};
                else if (mode == 2) key = {r.y+s,r.x,small,large};
                else if (mode == 3) key = {large,small,r.y,r.x};
                else key = {Area(max(usedW,r.x+s))*max(usedH,r.y+s),small,r.y,r.x};
                if (key < bestKey) bestKey = key, chosen = j, id = candidate;
            }
            if (chosen < 0) return false;
            s = a[id].s;
            if (mode >= 5) remaining.erase(remaining.find({s,id}));
            const Rect r = free[chosen];
            ll x = r.x, y = r.y;
            // Alternative corners provide different ways to fill the same bin.
            if (corner & 1) x += r.w-s;
            if (corner & 2) y += r.h-s;
            p[id] = {x,y};
            usedW = max(usedW,x+s); usedH = max(usedH,y+s);
            split(free, {x,y,s,s});
        }
        accept(p);
        return true;
    }
    void makeWidths() {
        ll top = max(largest, (ll)sqrt((long double)bestArea)+1);
        set<ll> ws;
        auto add = [&](ll w) { if (w >= largest && w <= top) ws.insert(w); };
        add(largest); add(top);
        for (int i = 0; i <= 100; ++i) {
            add(largest+(top-largest)*i/100);
            if (top > largest)
                add((ll)llround(largest*powl((long double)top/largest, i/100.0L)));
        }
        // Good widths often lie at sums of square side lengths.
        ll prefix = 0;
        for (int i = 0; i < n; ++i) {
            prefix += a[i].s; add(prefix);
            if (i < 48 || n <= 96) {
                ll s = a[i].s;
                add(top/s*s); add((top/s-1)*s);
                for (int j = i; j < min(n,64); ++j) add(s+a[j].s);
            }
        }
        if (top-largest <= 600) for (ll w = largest; w <= top; ++w) add(w);
        widths.assign(ws.begin(),ws.end());
        // Try theoretically promising widths first. Squarer bins win ties.
        stable_sort(widths.begin(),widths.end(),[&](ll u,ll v) {
            Area au = Area(u)*heightLowerBound(u), av = Area(v)*heightLowerBound(v);
            return au != av ? au < av : u > v;
        });
    }
public:
    explicit Solver(const vector<int> &s) : n((int)s.size()) {
        deadline = chrono::steady_clock::now()+chrono::milliseconds(PACK_TIME_MS);
        for (int x : s) unit = gcd(unit,(ll)x);
        if (!unit) unit = 1;
        for (int i = 0; i < n; ++i) a.push_back({s[i]/unit,i});
        stable_sort(a.begin(),a.end(),[](const Item &x,const Item &y){return x.s>y.s;});
        for (auto x : a) total += Area(x.s)*x.s, sumSides += x.s;
        largest = n ? a[0].s : 0;
        lower = total;
        if (n >= 2) lower = max(lower, Area(a[0].s)*(a[0].s+a[1].s));
    }
    vector<vector<int>> run() {
        if (!n) return {};
        // Establish a fallback before any time-limited work.
        ll root = max(largest,(ll)ceill(sqrt((long double)total)));
        shelves(root);
        shelves(largest);
        vector<int> order(n); iota(order.begin(),order.end(),0);
        if (bestArea > lower) {
            makeWidths();
            int count = 0;
            for (ll w : widths) {
                if (expired() || bestArea == lower) break;
                if (++count <= 160) shelves(w);
                if (Area(w)*heightLowerBound(w) >= bestArea) continue;
                // First obtain a good strip packing without forcing tight gaps.
                ll h = min(sumSides, (ll)((bestArea-1)/w));
                pack(w,h,order,2);
                if (count >= 24) break;
            }
            size_t trial = 0;
            const double fractions[] = {0.0,0.45,0.8,1.0,0.2,0.65,1.0};
            while (!expired() && bestArea > lower && !widths.empty()) {
                size_t round = trial/7;
                ll w;
                if (trial%4 == 0) w = bestWidth;
                else if (trial%4 == 1) {
                    ll radius = max(2LL,bestWidth/40);
                    w = max(largest,bestWidth+(ll)(rng()%(2*radius+1))-radius);
                } else if (trial%4 == 2) w = widths[(trial/4)%widths.size()];
                else w = widths[rng()%widths.size()];
                ++trial;
                if (Area(w)*w > bestArea*2) continue;
                ll lo = heightLowerBound(w), hi = (ll)((bestArea-1)/w);
                if (lo > hi) continue;
                double f = fractions[round%7];
                ll h = lo+(ll)((hi-lo)*f);
                iota(order.begin(),order.end(),0);
                int mode = (int)(trial%7), corner = 0;
                if (trial >= 28 && trial%3 != 0 && mode < 5) {
                    // Preserve the large-first bias, varying similarly sized items.
                    vector<double> priority(n);
                    double noise = (round%4 == 0 ? 0.35 : 0.10);
                    for (int i = 0; i < n; ++i)
                        priority[i] = a[i].s*(1.0+noise*(double(rng())/rng.max()));
                    stable_sort(order.begin(),order.end(),[&](int i,int j){return priority[i]>priority[j];});
                    if (n <= 16 && round%4 == 0) shuffle(order.begin(),order.end(),rng);
                    if (round%6 == 0) corner = 1;
                }
                if (trial%5 == 0) {
                    ll repairWidth = bestWidth;
                    if (trial%10 == 0) {
                        ll delta = max(1LL,largest/12);
                        repairWidth = max(largest,repairWidth+(ll)(rng()%(2*delta+1))-delta);
                    }
                    ll repairHeight = (ll)((bestArea-1)/repairWidth);
                    if (repairHeight >= heightLowerBound(repairWidth))
                        pack(repairWidth,repairHeight,order,mode,0,true,20+rng()%51);
                } else pack(w,h,order,mode,corner);
            }
        }
        vector<vector<int>> answer(n,vector<int>(2));
        if (best.empty()) throw runtime_error("No packing fits the integer coordinate range.");
        for (int i = 0; i < n; ++i) {
            // x in the statement points down: return (row, column).
            answer[a[i].id] = {(int)(best[i].y*unit),(int)(best[i].x*unit)};
        }
        return answer;
    }
};
}

vector<vector<int>> pack_squares(vector<int> squares) {
    return square_packing::Solver(squares).run();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> squares(n);
    for (int &s : squares) cin >> s;
    vector<vector<int>> result = pack_squares(squares);
    ofstream file;
    ostream *out = &cout;
    if (const char *path = getenv("OUTPUT_PATH")) {
        file.open(path);
        if (file) out = &file;
    }
    for (const auto &p : result) *out << p[0] << ' ' << p[1] << '\n';
    return 0;
}
