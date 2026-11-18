#include <bits/stdc++.h>

using namespace std;

string ltrim(const string &);
string rtrim(const string &);



/*
 * Complete the 'solve' function below.
 *
 * The function is expected to return a STRING_ARRAY.
 * The function accepts STRING_ARRAY grid as parameter.
 */
 
 class SAT {
    struct Clause { std::vector<int> x; };
    std::vector<Clause> clauses;
    std::vector<std::vector<int>> watch;
    std::vector<int> value, level, reason, phase, trail, limits, heap, position;
    std::vector<double> activity;
    std::vector<unsigned char> seen;
    int head=0;
    double increment=1;
    bool consistent=true;
    std::chrono::steady_clock::time_point deadline;
    int truth(int p) const { return value[p>>1]<0?-1:value[p>>1]^(p&1); }
    void up(int i) {
        int v=heap[i];
        while(i && activity[v]>activity[heap[(i-1)/2]]) {
            heap[i]=heap[(i-1)/2]; position[heap[i]]=i; i=(i-1)/2;
        }
        heap[i]=v; position[v]=i;
    }
    void insert(int v) {
        if(position[v]>=0) return;
        position[v]=(int)heap.size(); heap.push_back(v); up(position[v]);
    }
    int pop() {
        int result=heap[0],v=heap.back(); heap.pop_back(); position[result]=-1;
        if(!heap.empty()) {
            int i=0;
            while(2*i+1<(int)heap.size()) {
                int j=2*i+1;
                if(j+1<(int)heap.size() && activity[heap[j+1]]>activity[heap[j]]) ++j;
                if(activity[v]>=activity[heap[j]]) break;
                heap[i]=heap[j]; position[heap[i]]=i; i=j;
            }
            heap[i]=v; position[v]=i;
        }
        return result;
    }
    void bump(int v) {
        activity[v]+=increment;
        if(activity[v]>1e100) {
            for(double &a:activity) a*=1e-100;
            increment*=1e-100;
        }
        if(position[v]>=0) up(position[v]);
    }
    bool enqueue(int p,int why) {
        int t=truth(p);
        if(t>=0) return t==1;
        int v=p>>1;
        value[v]=1-(p&1); level[v]=(int)limits.size(); reason[v]=why;
        trail.push_back(p); return true;
    }
    int propagate() {
        int work=0;
        while(head<(int)trail.size()) {
            int falseLiteral=trail[head++]^1;
            auto &list=watch[falseLiteral];
            for(size_t i=0;i<list.size();) {
                if((++work&8191)==0 && std::chrono::steady_clock::now()>=deadline) {
                    --head; return -2;
                }
                int id=list[i]; auto &c=clauses[id].x;
                if(c[0]==falseLiteral) std::swap(c[0],c[1]);
                int first=c[0];
                if(truth(first)==1) { ++i; continue; }
                size_t k=2;
                while(k<c.size() && truth(c[k])==0) ++k;
                if(k<c.size()) {
                    std::swap(c[1],c[k]);
                    watch[c[1]].push_back(id);
                    list[i]=list.back(); list.pop_back();
                } else {
                    ++i;
                    if(!enqueue(first,id)) return id;
                }
            }
        }
        return -1;
    }
    void cancel(int target) {
        if((int)limits.size()<=target) return;
        int begin=limits[target];
        for(int i=(int)trail.size()-1;i>=begin;--i) {
            int v=trail[i]>>1;
            phase[v]=value[v]; value[v]=-1; insert(v);
        }
        trail.resize(begin); head=begin; limits.resize(target);
    }
    int learn(int conflict,std::vector<int> &out) {
        out.assign(1,-1);
        int unresolved=0,p=-1,index=(int)trail.size();
        do {
            for(int q:clauses[conflict].x) {
                int v=q>>1;
                if((p>=0 && v==(p>>1)) || seen[v] || level[v]==0) continue;
                seen[v]=1; bump(v);
                if(level[v]==(int)limits.size()) ++unresolved;
                else out.push_back(q);
            }
            do { p=trail[--index]; } while(!seen[p>>1]);
            seen[p>>1]=0; --unresolved; conflict=reason[p>>1];
        } while(unresolved);
        out[0]=p^1;
        int back=0;
        for(size_t i=1;i<out.size();++i) {
            seen[out[i]>>1]=0;
            if(level[out[i]>>1]>back) {
                back=level[out[i]>>1]; std::swap(out[1],out[i]);
            }
        }
        return back;
    }
    int store(std::vector<int> c) {
        int id=(int)clauses.size(); clauses.push_back({std::move(c)});
        auto &x=clauses.back().x;
        if(x.size()>1) watch[x[0]].push_back(id),watch[x[1]].push_back(id);
        return id;
    }
public:
    explicit SAT(std::chrono::steady_clock::time_point until):deadline(until) {}
    int variable(bool preferred=false) {
        int v=(int)value.size();
        value.push_back(-1); level.push_back(0); reason.push_back(-1);
        phase.push_back(preferred); activity.push_back(0);
        seen.push_back(0); position.push_back(-1);
        watch.resize(2*(v+1)); insert(v); return v;
    }
    void reset() { cancel(0); }
    void setDeadline(std::chrono::steady_clock::time_point until) { deadline=until; }
    void prefer(int v,bool preferred) { phase[v]=preferred; }
    bool add(std::vector<int> c) {
        if(!consistent) return false;
        std::sort(c.begin(),c.end());
        c.erase(std::unique(c.begin(),c.end()),c.end());
        std::vector<int> x;
        for(size_t i=0;i<c.size();++i) {
            if(i && c[i]==(c[i-1]^1)) return true;
            if(truth(c[i])==1) return true;
            if(truth(c[i])<0) x.push_back(c[i]);
        }
        if(x.empty()) return consistent=false;
        for(int p:x) { activity[p>>1]+=0.01; if(position[p>>1]>=0) up(position[p>>1]); }
        int id=store(std::move(x));
        if(clauses[id].x.size()==1) consistent=enqueue(clauses[id].x[0],id);
        return consistent;
    }
    bool assigned(int v) const { return value[v]==1; }
    // 1 = model, 0 = time limit, -1 = unsatisfiable.
    int solve() {
        if(!consistent) return -1;
        int conflicts=0, nextRestart=100, interval=100, iterations=0;
        std::vector<int> learnt;
        for(;;) {
            if((++iterations&63)==0 && std::chrono::steady_clock::now()>=deadline) return 0;
            int conflict=propagate();
            if(conflict==-2) return 0;
            if(conflict>=0) {
                if(limits.empty()) { consistent=false; return -1; }
                int back=learn(conflict,learnt);
                cancel(back);
                int id=store(learnt);
                enqueue(learnt[0],id);
                increment/=0.95;
                if(++conflicts>=nextRestart) {
                    cancel(0); interval=std::min(2000,interval+interval/2);
                    nextRestart=conflicts+interval;
                }
            } else {
                int v=-1;
                while(!heap.empty()) {
                    int candidate=pop();
                    if(value[candidate]<0) { v=candidate; break; }
                }
                if(v<0) return 1;
                limits.push_back((int)trail.size());
                enqueue(2*v+(phase[v]?0:1),-1);
            }
        }
    }
};

 
class Solver {
    using Clock = chrono::steady_clock;
    // N,E,S,W; states: empty, EW, NS, NE, NW, SE, SW.
    const array<int,7> shape{0,10,5,3,9,6,12};
    const string symbol = ".-|LJF7";
    int R,C,N, firstPearl=-1, bestLength=1000000000;
    vector<int> type, row, col;
    vector<array<int,4>> nb;
    vector<uint8_t> dom, initial, best, hint;
    int hintScore=-1;
    array<int,128> count{}, any{}, all{}, singleton{};
    array<int,4> has{}, lacks{};
    uint8_t support[3][3][4][128]{};
    vector<pair<int,uint8_t>> trail;
    vector<int> queue;
    vector<uint8_t> queued;
    size_t head=0;
    vector<int> parent, size, required, forcedDegree, stubs;
    vector<int> disc, low, mark, edgeStack, kept, distance, bfs;
    vector<array<int,3>> edges;
    vector<array<int,4>> edgeId;
    int totalRequired=0, forcedEdges=0, components=0;
    int dfsTimer=0, blockId=0, keepStamp=0;
    bool goodBlock=false, stopped=false, strong=false;
    uint64_t nodes=0;
    uint32_t randomState=123456789;
    vector<uint32_t> priority;
    Clock::time_point start;
    double deadline=0, totalBudget, improveBudget;

    double elapsed() const {
        return chrono::duration<double>(Clock::now()-start).count();
    }
    uint32_t random() {
        randomState ^= randomState<<13;
        randomState ^= randomState>>17;
        return randomState ^= randomState<<5;
    }
    bool expired() {
        double t=elapsed();
        if(t>=deadline || t>=totalBudget ||
           (!best.empty() && t>=improveBudget)) stopped=true;
        return stopped;
    }
    int root(int v) {
        while(parent[v]!=v) v=parent[v]=parent[parent[v]];
        return v;
    }
    void unite(int a,int b) {
        a=root(a); b=root(b);
        if(a==b) return;
        if(size[a]<size[b]) swap(a,b);
        parent[b]=a; size[a]+=size[b];
    }
    bool restrictTo(int v,int mask) {
        int d=dom[v]&mask;
        if(d==dom[v]) return true;
        trail.emplace_back(v,dom[v]);
        dom[v]=uint8_t(d);
        if(!d) return false;
        if(!queued[v]) queued[v]=1,queue.push_back(v);
        return true;
    }
    void clearQueue() {
        for(size_t i=head;i<queue.size();++i) queued[queue[i]]=0;
        queue.clear(); head=0;
    }
    void undo(size_t checkpoint) {
        clearQueue();
        while(trail.size()>checkpoint) {
            auto [v,d]=trail.back(); trail.pop_back(); dom[v]=d;
        }
    }
    bool checkWhite(int v) {
        if(!strong) {
            int allowed=0;
            for(int s=1;s<=2;++s) if(dom[v]&(1<<s)) {
                int d=s==1?1:0,a=nb[v][d],b=nb[v][d+2];
                if(a>=0 && b>=0 && ((dom[a]|dom[b])&120)) allowed|=1<<s;
            }
            if(!restrictTo(v,allowed)) return false;
            if(count[dom[v]]==1) {
                int d=dom[v]==2?1:0,a=nb[v][d],b=nb[v][d+2];
                if(!(dom[a]&120) && !restrictTo(b,120)) return false;
                if(!(dom[b]&120) && !restrictTo(a,120)) return false;
            }
            return true;
        }
        int allowed=0;
        for(int s=1;s<=2;++s) if(dom[v]&(1<<s)) {
            int d=(s==1?1:0), a=nb[v][d], b=nb[v][d+2];
            if(a>=0 && b>=0 && ((dom[a]&has[d^2]&120) ||
                                (dom[b]&has[d]&120))) allowed|=1<<s;
        }
        if(!restrictTo(v,allowed)) return false;
        for(int d=0;d<4;++d) {
            int a=nb[v][d],b=nb[v][d^2];
            if(a>=0 && b>=0 && !(dom[b]&has[d]&120))
                if(!restrictTo(a,lacks[d^2]|120)) return false;
        }
        return true;
    }
    bool propagate() {
        while(head<queue.size()) {
            int v=queue[head++]; queued[v]=0;
            for(int d=0;d<4;++d) {
                int u=nb[v][d];
                if(u>=0 && !restrictTo(u,support[type[u]][type[v]][d^2][dom[v]]))
                    return false;
            }
            if(type[v]==1 && !checkWhite(v)) return false;
            for(int u:nb[v]) if(u>=0 && type[u]==1 && !checkWhite(u)) return false;
            if((head&1023)==0 && expired()) return false;
        }
        clearQueue();
        return true;
    }
    bool active(int v,int d) const { return (any[dom[v]]&(1<<d))!=0; }
    void blocks(int v,int parentEdge) {
        disc[v]=low[v]=++dfsTimer;
        for(int d=0;d<4;++d) if(active(v,d)) {
            int u=nb[v][d], e=edgeId[v][d];
            if(e==parentEdge) continue;
            if(!disc[u]) {
                edgeStack.push_back(e);
                blocks(u,e);
                low[v]=min(low[v],low[u]);
                if(low[u]>=disc[v]) {
                    ++blockId;
                    int number=0;
                    size_t begin=edgeStack.size();
                    do {
                        --begin;
                        auto edge=edges[edgeStack[begin]];
                        for(int x:{edge[0],edge[1]}) if(mark[x]!=blockId) {
                            mark[x]=blockId;
                            number+=!(dom[x]&1);
                        }
                    } while(edgeStack[begin]!=e);
                    if(number==totalRequired) {
                        goodBlock=true;
                        for(size_t i=begin;i<edgeStack.size();++i) kept[edgeStack[i]]=keepStamp;
                    }
                    edgeStack.resize(begin);
                }
            } else if(disc[u]<disc[v]) {
                edgeStack.push_back(e);
                low[v]=min(low[v],disc[u]);
            }
        }
    }
    void saveCycle(int component) {
        vector<uint8_t> answer(N,0);
        int length=0;
        for(int v=0;v<N;++v) if(root(v)==component) {
            answer[v]=uint8_t(singleton[dom[v]]); ++length;
        }
        if(length<bestLength) bestLength=length,best=move(answer);
    }
    // -1: contradiction; 0: stable; 1: changed; 2: solution.
    int global() {
        iota(parent.begin(),parent.end(),0);
        fill(size.begin(),size.end(),1);
        fill(required.begin(),required.end(),0);
        totalRequired=forcedEdges=0;
        int r0=R,r1=-1,c0=C,c1=-1,cycle=-1;
        for(int v=0;v<N;++v) {
            forcedDegree[v]=0;
            int f=all[dom[v]];
            for(int d=0;d<4;++d) forcedDegree[v]+=(f>>d)&1;
            if(!(dom[v]&1)) {
                ++totalRequired;
                r0=min(r0,row[v]); r1=max(r1,row[v]);
                c0=min(c0,col[v]); c1=max(c1,col[v]);
            }
            for(int d=1;d<=2;++d) if(f&(1<<d)) {
                int u=nb[v][d]; ++forcedEdges;
                if(root(v)==root(u)) cycle=v;
                else unite(v,u);
            }
        }
        int bound=max(totalRequired,2*(r1-r0+c1-c0));
        if(bound>=bestLength) return -1;
        for(int v=0;v<N;++v) if(!(dom[v]&1)) ++required[root(v)];
        if(cycle>=0) {
            int k=root(cycle);
            if(required[k]!=totalRequired) return -1;
            saveCycle(k); return 2;
        }
        stubs.clear(); components=0;
        for(int v=0;v<N;++v) {
            if(parent[v]==v && required[v]) ++components;
            if(!(dom[v]&1)) for(int i=forcedDegree[v];i<2;++i) stubs.push_back(v);
        }
        // Every unfinished forced path has two ends. Future connecting
        // paths cost at least their endpoints' Manhattan distances.
        if(bestLength<1000000000 && stubs.size()<=80) {
            int sum=0;
            for(int i=0;i<(int)stubs.size();++i) {
                int a=stubs[i], closest=1000000;
                for(int j=0;j<(int)stubs.size();++j) if(i!=j) {
                    int b=stubs[j];
                    if(components>1 && root(a)==root(b)) continue;
                    closest=min(closest,abs(row[a]-row[b])+abs(col[a]-col[b]));
                }
                sum+=closest;
            }
            if(forcedEdges+(sum+1)/2>=bestLength) return -1;
        }
        bool changed=false;
        for(auto e:edges) {
            int v=e[0],u=e[1],d=e[2];
            if(!active(v,d) || (all[dom[v]]&(1<<d))) continue;
            if(root(v)==root(u) && required[root(v)]<totalRequired) {
                if(!restrictTo(v,lacks[d]) || !restrictTo(u,lacks[d^2])) return -1;
                changed=true;
            }
        }
        if(changed) return 1;
        if(strong) for(int v=0;v<N;++v) if(forcedDegree[v]==0 && count[dom[v]]>1) {
            int allowed=dom[v];
            for(int s=1;s<7;++s) if(allowed&(1<<s)) {
                int a=-1,b=-1;
                for(int d=0;d<4;++d) if(shape[s]&(1<<d)) {
                    if(a<0) a=nb[v][d]; else b=nb[v][d];
                }
                if(root(a)==root(b) && required[root(a)]+(!(dom[v]&1))<totalRequired)
                    allowed^=1<<s;
            }
            if(allowed!=dom[v]) {
                if(!restrictTo(v,allowed)) return -1;
                changed=true;
            }
        }
        if(changed) return 1;
        // A simple cycle must lie entirely inside one vertex-biconnected block.
        fill(disc.begin(),disc.end(),0);
        dfsTimer=0; goodBlock=false; ++keepStamp; edgeStack.clear();
        blocks(firstPearl,-1);
        if(!goodBlock) return -1;
        for(int e=0;e<(int)edges.size();++e) {
            auto [v,u,d]=edges[e];
            if(active(v,d) && kept[e]!=keepStamp) {
                if(!restrictTo(v,lacks[d]) || !restrictTo(u,lacks[d^2])) return -1;
                changed=true;
            }
        }
        return changed?1:0;
    }
    int choose(int last) {
        int chosen=-1, bestKey=1000000000;
        uint32_t tie=0;
        for(int v=0;v<N;++v) if(!(dom[v]&1) && count[dom[v]]>1) {
            int key=16*count[dom[v]]-3*(type[v]!=0)-forcedDegree[v];
            if(last>=0) key+=min(6,abs(row[v]-row[last])+abs(col[v]-col[last]));
            if(key<bestKey || (key==bestKey && priority[v]>tie))
                chosen=v,bestKey=key,tie=priority[v];
        }
        return chosen;
    }
    array<int,7> orderedStates(int v,int &length) {
        // Distances to ends of other forced paths, using currently possible
        // unforced edges. This is only an ordering heuristic, never a prune.
        fill(distance.begin(),distance.end(),1000000);
        bfs.clear(); int component=root(v);
        for(int u:stubs) if(u!=v && (components==1 || root(u)!=component)) {
            if(distance[u]) distance[u]=0,bfs.push_back(u);
        }
        for(size_t i=0;i<bfs.size();++i) {
            int x=bfs[i];
            for(int d=0;d<4;++d) if(active(x,d) && !(all[dom[x]]&(1<<d))) {
                int u=nb[x][d];
                if(u==v || (!(dom[u]&1) && distance[u]!=0)) continue;
                if(distance[u]>distance[x]+1) {
                    distance[u]=distance[x]+1; bfs.push_back(u);
                }
            }
        }
        array<pair<int,int>,7> candidates{}; length=0;
        for(int s=1;s<7;++s) if(dom[v]&(1<<s)) {
            int score=0;
            for(int d=0;d<4;++d) if((shape[s]&~all[dom[v]])&(1<<d)) {
                int u=nb[v][d];
                score+=8*distance[u]+((dom[u]&1)?3:0);
            }
            candidates[length++]={score*8+int(random()&7),s};
        }
        sort(candidates.begin(),candidates.begin()+length);
        array<int,7> result{};
        for(int i=0;i<length;++i) result[i]=candidates[i].second;
        return result;
    }
    void search(int last=-1) {
        if(stopped || ((++nodes&15)==0 && expired())) return;
        for(;;) {
            if(!propagate()) return;
            int status=global();
            if(status<0 || status==2) return;
            if(!status) break;
        }
        if(!best.empty() && expired()) return;
        if(best.empty() && totalRequired>hintScore) hintScore=totalRequired,hint=dom;
        int v=choose(last);
        if(v<0) return;
        int length;
        auto choices=orderedStates(v,length);
        for(int i=0;i<length && !stopped;++i) {
            size_t checkpoint=trail.size();
            if(restrictTo(v,1<<choices[i])) search(v);
            undo(checkpoint);
        }
    }
    void satFallback() {
        strong=true;
        dom=initial; trail.clear(); clearQueue(); stopped=false;
        deadline=totalBudget;
        for(int v=0;v<N;++v) queued[v]=1,queue.push_back(v);
        for(;;) {
            if(!propagate()) return;
            int status=global();
            if(status<0 || status==2) return;
            if(status==0) break;
        }
        auto until=start+chrono::duration_cast<Clock::duration>(chrono::duration<double>(totalBudget));
        auto phaseUntil=start+chrono::duration_cast<Clock::duration>(chrono::duration<double>(5.0));
        SAT sat(min(until,phaseUntil));
        vector<int> ev(edges.size(),-1);
        vector<array<int,7>> sv(N);
        for(auto &a:sv) a.fill(-1);
        for(int e=0;e<(int)edges.size();++e)
            if(active(edges[e][0],edges[e][2])) {
                ev[e]=sat.variable();
            }
        for(int v=0;v<N;++v) {
            vector<int> choices;
            for(int s=0;s<7;++s) if(dom[v]&(1<<s)) {
                int variable=sat.variable(s==0); sv[v][s]=variable;
                choices.push_back(2*variable);
                for(int d=0;d<4;++d) {
                    int e=edgeId[v][d];
                    if(e>=0 && ev[e]>=0)
                        sat.add({2*variable+1,2*ev[e]+((shape[s]&(1<<d))?0:1)});
                }
            }
            sat.add(choices);
        }
        for(int v=0;v<N;++v) {
            if(type[v]==1) for(int s=1;s<=2;++s) if(sv[v][s]>=0) {
                vector<int> c{2*sv[v][s]+1};
                for(int d=0;d<4;++d) if(shape[s]&(1<<d)) {
                    int u=nb[v][d];
                    for(int t=3;t<7;++t) if(sv[u][t]>=0 && (shape[t]&(1<<(d^2))))
                        c.push_back(2*sv[u][t]);
                }
                sat.add(c);
            }
            if(type[v]==2) for(int d=0;d<4;++d) {
                int e=edgeId[v][d];
                if(e<0 || ev[e]<0) continue;
                int u=nb[v][d];
                vector<int> c{2*ev[e]+1};
                for(int t=1;t<=2;++t) if(sv[u][t]>=0) c.push_back(2*sv[u][t]);
                sat.add(c);
            }
        }
        vector<int> selected(N),component(N);
        int pearlCount=0;
        for(int t:type) pearlCount+=t!=0;
        bool secondPhase=false;
        while(elapsed()<totalBudget) {
            int status=sat.solve();
            if(status<0) return;
            if(status==0) {
                if(secondPhase || elapsed()>=totalBudget) return;
                secondPhase=true; sat.reset(); sat.setDeadline(until);
                if(!hint.empty()) {
                    for(int e=0;e<(int)edges.size();++e) if(ev[e]>=0)
                        sat.prefer(ev[e],(all[hint[edges[e][0]]]&(1<<edges[e][2]))!=0);
                    for(int v=0;v<N;++v) for(int s=0;s<7;++s) if(sv[v][s]>=0)
                        sat.prefer(sv[v][s],hint[v]==(1<<s) || ((hint[v]&1) && s==0));
                }
                continue;
            }
            for(int v=0;v<N;++v) {
                selected[v]=0;
                for(int s=0;s<7;++s) if(sv[v][s]>=0 && sat.assigned(sv[v][s])) selected[v]=s;
            }
            fill(component.begin(),component.end(),-1);
            vector<vector<int>> groups;
            vector<int> pearls;
            for(int v=0;v<N;++v) if(selected[v] && component[v]<0) {
                int id=(int)groups.size();
                groups.push_back({v}); pearls.push_back(0); component[v]=id;
                for(size_t i=0;i<groups[id].size();++i) {
                    int x=groups[id][i]; pearls[id]+=type[x]!=0;
                    for(int d=0;d<4;++d) if(shape[selected[x]]&(1<<d)) {
                        int u=nb[x][d];
                        if(component[u]<0) component[u]=id,groups[id].push_back(u);
                    }
                }
                if(pearls[id]==pearlCount) {
                    if((int)groups[id].size()<bestLength) {
                        bestLength=(int)groups[id].size(); best.assign(N,0);
                        for(int x:groups[id]) best[x]=uint8_t(selected[x]);
                    }
                    return;
                }
            }
            sat.reset();
            for(int id=0;id<(int)groups.size();++id) if(pearls[id]) {
                vector<int> cut;
                for(int v:groups[id]) for(int d=0;d<4;++d) {
                    int u=nb[v][d],e=edgeId[v][d];
                    if(u>=0 && ev[e]>=0 && component[u]!=id) cut.push_back(2*ev[e]);
                }
                if(!sat.add(cut)) return;
            }
        }
    }
public:
    Solver(vector<string> grid,double seconds=9.0,double optimize=0.90)
        :R((int)grid.size()),C((int)grid[0].size()),N(R*C),
         totalBudget(seconds),improveBudget(optimize) {
        type.resize(N); row.resize(N); col.resize(N); nb.resize(N);
        dom.resize(N); queued.assign(N,0); priority.resize(N);
        parent.resize(N); size.resize(N); required.resize(N); forcedDegree.resize(N);
        disc.resize(N); low.resize(N); mark.assign(N,0); distance.resize(N);
        edgeId.resize(N);
        for(int d=0;d<4;++d) {
            for(int s=0;s<7;++s) if(shape[s]&(1<<d)) has[d]|=1<<s;
            lacks[d]=127^has[d];
        }
        for(int mask=1;mask<128;++mask) {
            all[mask]=15;
            for(int s=0;s<7;++s) if(mask&(1<<s)) {
                ++count[mask]; any[mask]|=shape[s]; all[mask]&=shape[s]; singleton[mask]=s;
            }
        }
        for(int a=0;a<3;++a) for(int b=0;b<3;++b)
            for(int d=0;d<4;++d) for(int mask=1;mask<128;++mask)
                for(int s=0;s<7;++s) for(int t=0;t<7;++t) if(mask&(1<<t)) {
                    bool edge=(shape[s]&(1<<d))!=0;
                    if(edge!=((shape[t]&(1<<(d^2)))!=0)) continue;
                    if(edge && ((a==2 && !(t==1||t==2)) ||
                                (b==2 && !(s==1||s==2)))) continue;
                    support[a][b][d][mask]|=1<<s;
                }
        for(int v=0;v<N;++v) {
            int r=v/C,c=v%C; row[v]=r; col[v]=c;
            type[v]=(grid[r][c]=='W'?1:grid[r][c]=='B'?2:0);
            if(type[v] && firstPearl<0) firstPearl=v;
            nb[v]={r?v-C:-1,c+1<C?v+1:-1,r+1<R?v+C:-1,c?v-1:-1};
            edgeId[v].fill(-1);
            dom[v]=uint8_t(type[v]==1?6:type[v]==2?120:127);
            for(int d=0;d<4;++d) if(nb[v][d]<0) dom[v]&=lacks[d];
        }
        for(int v=0;v<N;++v) for(int d=1;d<=2;++d) if(nb[v][d]>=0) {
            int u=nb[v][d],e=(int)edges.size();
            edges.push_back({v,u,d}); edgeId[v][d]=edgeId[u][d^2]=e;
        }
        kept.assign(edges.size(),0); initial=dom;
    }
    vector<string> solve() {
        start=Clock::now();
        double slice=0.12;
        while(elapsed()<totalBudget) {
            if(best.empty() && elapsed()>min(1.20,totalBudget*0.40)) {
                satFallback(); break;
            }
            dom=initial; trail.clear(); clearQueue();
            for(int v=0;v<N;++v) {
                if(!dom[v]) return {};
                priority[v]=random(); queued[v]=1; queue.push_back(v);
            }
            stopped=false;
            deadline=min(totalBudget,elapsed()+slice);
            search();
            if(!stopped) break; // Exhausted the search: incumbent is optimal.
            if(!best.empty() && elapsed()>=improveBudget) break;
            slice*=2;
        }
        if(best.empty()) return {};
        vector<string> answer(R,string(C,'.'));
        for(int v=0;v<N;++v) answer[v/C][v%C]=symbol[best[v]];
        return answer;
    }
};





vector<string> solve(vector<string> grid) {
    Solver solver(std::move(grid));
    return solver.solve();
}

int main()
{
    ofstream fout(getenv("OUTPUT_PATH"));

    string grid_count_temp;
    getline(cin, grid_count_temp);

    int grid_count = stoi(ltrim(rtrim(grid_count_temp)));

    vector<string> grid(grid_count);

    for (int i = 0; i < grid_count; i++) {
        string grid_item;
        getline(cin, grid_item);

        grid[i] = grid_item;
    }

    vector<string> result = solve(grid);

    for (size_t i = 0; i < result.size(); i++) {
        fout << result[i];

        if (i != result.size() - 1) {
            fout << "\n";
        }
    }

    fout << "\n";

    fout.close();

    return 0;
}

string ltrim(const string &str) {
    string s(str);

    s.erase(
        s.begin(),
        find_if(s.begin(), s.end(), not1(ptr_fun<int, int>(isspace)))
    );

    return s;
}

string rtrim(const string &str) {
    string s(str);

    s.erase(
        find_if(s.rbegin(), s.rend(), not1(ptr_fun<int, int>(isspace))).base(),
        s.end()
    );

    return s;
}
