# Prompt: Linux socket & process graph explorer

Build a tool that, in **one command on a Linux host**, snapshots every open socket and
the processes using them, plus the process tree, and writes a **single self-contained,
offline, interactive HTML** force-directed graph for exploring it.

Deliver two things: (A) a **stdlib-only Python 3 collector** that gathers the data, and
(B) it emits the **standalone HTML** described in Part B. No external Python packages; the
visualization library is vendored inline so the HTML opens offline in any browser.

This spec is **opinionated on purpose** — the rendering and physics choices below are
mandatory. They're the distillate of a long tuning process; deviating reproduces known
failure modes (see Anti-patterns). Follow Part B and the reference skeleton closely.

Run shape:
```bash
sudo python3 socket_graph.py            # sudo → full process↔socket visibility
python3 socket_graph.py -o sockets.html # works unprivileged too (own processes only)
```

---

## Part A — Data collection (stdlib only, no deps)

Read everything from `/proc` directly (no dependency on `ss`/`lsof`; you may *optionally*
cross-check with `ss` if present, but `/proc` is the source of truth). If a read raises
`PermissionError`/`FileNotFoundError`, skip that item and keep going; tally how many
sockets you couldn't attribute to a process and, if >0 and not root, print a one-line
hint to re-run with `sudo`.

### A1. Processes — from `/proc/<pid>/`
For each numeric `pid` dir:
- `status` → `Name` (comm), `PPid`, real `Uid` (first field), state.
- `cmdline` → NUL-separated full argv (fall back to `[comm]` if empty → kernel thread).
- Resolve username from uid via `pwd.getpwuid` (best-effort).
Record: `pid, comm, cmdline, uid, user, ppid, is_kernel_thread`.

### A2. Sockets — from `/proc/net/{tcp,tcp6,udp,udp6,unix}`
Parse each file (skip header line). Key fields and gotchas:
- **tcp / udp (IPv4):** `local_address` and `rem_address` are `HEXIP:HEXPORT`. The IP is
  **little-endian** — bytes reversed: `0100007F` → `127.0.0.1`; port is big-endian hex.
  `st` is the hex TCP state; **inode** is the 10th whitespace column (after `uid`,
  `timeout`). TCP states: `01`=ESTABLISHED, `0A`=LISTEN, `06`=TIME_WAIT, `08`=CLOSE_WAIT,
  etc. (UDP rows are mostly `07`; treat as “bound/in-use”.)
- **tcp6 / udp6:** address is 32 hex chars = 16 bytes; parse as 4 little-endian 32-bit
  words → IPv6. Collapse `::1`, `::`, and v4-mapped `::ffff:a.b.c.d`.
- **unix:** columns `Num RefCount Protocol Flags Type St Inode Path`. `Type`:
  `0001`=STREAM, `0002`=DGRAM, `0005`=SEQPACKET. `St`: `01`=UNCONNECTED, `03`=CONNECTED.
  `Flags & 0x10000` (SO_ACCEPTCON) ⇒ **listening**. `Path` may be empty (unnamed) or start
  with `@` (abstract namespace). Key unix sockets by **inode**.
Record per socket: `inode, family (tcp/tcp6/udp/udp6/unix), kind (stream/dgram), state,
local (ip:port or path), peer (ip:port or ""), listening (bool)`.

### A3. Socket → process ownership — from `/proc/<pid>/fd/`
For every `pid`, `os.readlink` each entry in `/proc/<pid>/fd/`. Links of the form
`socket:[INODE]` map that **inode → pid** (a socket may be held by several pids; a process
holds many sockets). Build `inode → set(pid)`.

### A4. Build the graph
**Node types** (drive color/filter; call this field `type`):
- `proc-root` (uid 0) and `proc-user` — processes. (Kernel threads: `proc-kernel`.)
- `tcp`, `udp`, `unix` — sockets, by family. Flag listening sockets (`data.listen=true`)
  for emphasis.
- `remote` — a foreign endpoint (a non-local peer IP:port of an ESTABLISHED socket that no
  local process owns). Create one per distinct foreign `ip:port` so outbound/inbound
  connections are visible.

**Edges** — two classes (`cls`), because they drive the two force-focus modes:
- `tree` — **process → child process** (from PPid), label `"parent of"`, directed.
- `io` — everything socket-related, directed, with a relationship label:
  - process → socket: label by socket state — `listen` (LISTEN / SO_ACCEPTCON),
    `established`, `connected`, `bound`/`udp`, else the state name; fallback `fd`.
  - socket → remote: for ESTABLISHED sockets with a foreign peer → label `connects`.
  - socket ↔ socket **peer** (best-effort, optional but nice): for **loopback TCP**, match
    one socket's `peer (ip:port)` to another local socket's `local (ip:port)` and link them
    `peer`. (UNIX peer inodes aren't in `/proc/net/unix`; only attempt via `ss -xp` if
    you opted to use `ss`, otherwise skip.)

**Labels** (keep node labels *short*; full detail in the tooltip — see Part B):
- process node: short `comm (pid)`; tooltip: full `cmdline`, `user (uid)`, `ppid`, state,
  socket count.
- socket node: short — TCP/UDP `tcp :443 LISTEN` or `tcp 10.0.0.5:54321`; UNIX basename of
  path or `unix:stream` if unnamed; tooltip: family/kind, full local & peer, state, inode,
  owning pids.
- remote node: short `ip:port`; tooltip: full foreign address.

Emit the model the visualization expects:
```jsonc
{
  "meta":  { "host": "...", "captured": "ISO-8601", "root": true|false, "counts": {...} },
  "types": [ { "id":"proc-user", "label":"Process (user)", "color":"#3F8EE0" }, ... ],
  "nodes": [ { "id":"p:1234", "label":"nginx (1234)", "full":"…tooltip…",
               "type":"proc-user", "listen":false }, ... ],
  "edges": [ { "source":"p:1234", "target":"s:98765", "label":"listen",
               "cls":"io", "dir":true }, ... ]
}
```
Node `id`s must be unique & stable (`p:<pid>`, `s:<inode>`, `r:<ip:port>`). Drop edges
whose endpoints aren't both present.

---

## Part B — The interactive HTML (mandatory design)

### Engine & file
- **Cytoscape.js**, vendored **inline** (download `cytoscape.min.js` once and embed it in a
  `<script>` block). **No CDN, no `http(s)` references** — the file must open offline. No
  D3/`<canvas>`/vis-network/sigma. One `.html` file, data embedded as a JS object.
- **Light theme**: background `#fbfbfd`, sidebar `#fff`, text `#222`. No dark mode.

### Nodes & edges (canonical visual language — don't overload styles)
- **Nodes are rectangles with the label INSIDE**, sized to the label (`width/height:label`),
  fill = the node `type` color, 1px `#6b6b6b` border. Never circles/dots, never external
  labels, never mixed shapes — **shape is constant; color encodes type.** Give **listening
  sockets** a thicker/darker border so hubs stand out.
- **Node label = concise identity only** (the short label). The full detail (cmdline,
  addresses, inode, etc.) goes in the **hover tooltip** — never dump multi-line blocks onto
  the node face.
- **Edges are arcs** (`curve-style:unbundled-bezier`, control-point-distance via a tunable
  `ARC` constant ≈ 90), colored by source-node type, **with a target arrowhead** (these are
  directed relationships).
- **Edge labels ON by default**, `autorotate`d to follow the edge, with a small background
  chip for legibility; keep a toggle to hide them. `tree` edges (“parent of”) get a lighter
  italic label so they read as structure vs the `io` relationship labels.
- **Hover tooltip** shows the node’s `full` text (+ type), or the edge’s relationship label.
- **Click-to-isolate**: clicking a node fades everything except it and its direct
  neighbourhood; click empty space to reset.
- **Layer/type legend = filter**: one swatch + checkbox per `type`; click toggles that
  type’s nodes (and their incident edges).

### Layout — a LIVE force simulation that anneals to rest
Drive node positions with your own `requestAnimationFrame` loop (Cytoscape `layout:'preset'`
+ you set positions). It must:
- **Start loose and self-organize** from a random cloud; the view **auto-frames only while
  it first settles** and then **stops auto-fitting** — never re-fit on settle or on
  interaction (losing the user’s pan/zoom is the #1 annoyance). A manual **Fit** button and
  a **🌀 Jiggle / reset** button (random kick + reset damping) stay available.
- **Cool by a RISING damping factor**, not by velocity damping alone: each tick
  `damping = min(DAMP_MAX, damping + DAMP_RAMP)` and `velocity *= (1 - damping)`; **stop the
  loop when the fastest node’s speed < SETTLE** (a threshold). This is the correct annealing
  loop — it *halts*. (A loop that re-applies full-strength forces forever with only constant
  damping never converges — it orbits/jitters. Don’t do that.)
- **Box-aware separation**: measure each node’s label-box `w/h` and add an **AABB collision
  force** that pushes overlapping boxes apart along the axis of least penetration — otherwise
  wide labels stack on top of each other.
- **One `SEP` multiplier** scales all spacing constants (spring length, collision pad,
  initial spread, etc.) so the user can spread the whole graph with a single knob.
- Forces: inverse-square **repulsion**, **spring** attraction along edges, gentle
  **centering gravity**, the collision force, plus a velocity clamp. A node being **dragged
  is pinned** (and dragging re-energizes the field).

### Controls — focus + strength (the key to taming a dense graph)
This graph is highly connected, so add a **force-focus selector** and a **strength slider**:
- **Focus** (select): **process tree** (weight `tree` edges), **socket I/O** (weight `io`
  edges), **distance from selected** (radial). Default to **process tree** so structure
  dominates the hairball.
- **Strength** (slider, weak→strong): scales the **focused** force from ~0.2× up to ~**12×**
  (quadratic mapping for fine low-end control). The non-focused edge springs stay at a weak
  baseline (~0.15) so the focus genuinely dominates. **Changing focus or strength
  re-energizes** the sim (reheat) so it can climb out of metastable arrangements — strength
  alone without re-injecting energy won’t escape a local minimum.
- **Distance-from-selected** mode: BFS hop-distance from the clicked node → concentric rings
  (ring gap per hop); pin the selected node as the centre. Re-click to re-centre.

### Sidebar
Header with host + node/edge counts and a live settle status (`● settling… v=… damp=…` →
`✓ settled`); the focus select; strength slider; edge-label & (optional) per-class label
toggles; the type legend/filter; a short edge-style key.

### Reference skeleton (fill `NODES/EDGES/TYPES`; inline `cytoscape.min.js`)
```html
<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Linux sockets — explorer</title>
<style>
 html,body{margin:0;height:100%;font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#fbfbfd;color:#222}
 #wrap{display:flex;height:100vh}#net{flex:1;background:#fbfbfd}
 #side{width:280px;padding:12px 14px;box-sizing:border-box;border-left:1px solid #e2e2ea;overflow:auto;background:#fff;font-size:13px}
 h2{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#888;margin:14px 0 6px}
 .row{display:flex;align-items:center;gap:7px;margin:3px 0}.sw{width:13px;height:13px;border-radius:3px;border:1px solid #999}
 button{font:inherit;padding:5px 9px;margin:2px 4px 2px 0;border:1px solid #ccc;border-radius:6px;background:#f4f4f8;cursor:pointer}
 #tip{position:absolute;display:none;max-width:340px;background:#222;color:#fff;font-size:12px;line-height:1.4;
      padding:7px 9px;border-radius:6px;white-space:pre-wrap;pointer-events:none;z-index:9}
 #status{font-size:11.5px;color:#555;margin:4px 0}
</style></head><body>
<div id="tip"></div>
<div id="wrap"><div id="net"></div><div id="side">
  <div id="count"></div>
  <h2>Force layout (live)</h2>
  <button id="jiggle">🌀 Jiggle / reset</button><button id="fit">⤢ Fit</button>
  <div class="row"><label for="focus">Focus&nbsp;</label><select id="focus">
    <option value="tree">process tree</option><option value="io">socket I/O</option>
    <option value="radial">distance from selected</option></select></div>
  <div style="margin:6px 0 2px"><div style="display:flex;justify-content:space-between;font-size:11px;color:#777"><span>weak</span><span>strong</span></div>
    <input type="range" id="strength" min="0" max="100" value="45" style="width:100%"></div>
  <div id="status">● settling…</div>
  <div class="row"><input type="checkbox" id="elabels" checked><label for="elabels">show edge labels</label></div>
  <h2>Types — click to filter</h2><div id="legend"></div>
</div></div>
<script>/* …inline cytoscape.min.js here… */</script>
<script>
const NODES=__NODES__, EDGES=__EDGES__, TYPES=__TYPES__;
const COL=Object.fromEntries(TYPES.map(t=>[t.id,t.color]));
const SEP=4, ARC=90;
const STEP=.045, MAX_V=20*SEP, K_REP=6000*SEP, SPR_L=150*SEP, CONT_L=82*SEP, GRAV=.012/SEP;
const COL_K=3, COL_PAD=16*SEP, DAMP0=.08, DAMP_MAX=.9, DAMP_RAMP=.0032, SETTLE=.2*SEP, JIGGLE=40*SEP;
const RING=.55*SPR_L, RAD_K=.05;
const els=NODES.map(n=>({data:{id:n.id,label:n.label,full:n.full||n.label,type:n.type,col:COL[n.type]||"#bbb",
    listen:n.listen?"yes":"no",tip:(n.full||n.label)+"\n\n["+n.type+"]"}}))
 .concat(EDGES.map((e,i)=>({data:{id:"e"+i,source:e.source,target:e.target,label:e.label,cls:e.cls,
    col:COL[(NODES.find(n=>n.id===e.source)||{}).type]||"#9aa0a6",tip:e.label||""},classes:e.cls})));
const cy=cytoscape({container:document.getElementById("net"),elements:els,wheelSensitivity:.25,layout:{name:"preset"},style:[
  {selector:"node",style:{"shape":"round-rectangle","background-color":"data(col)","border-color":"#6b6b6b","border-width":1,
    "label":"data(label)","text-wrap":"wrap","text-max-width":150,"font-size":11,"color":"#1a1a1a",
    "text-valign":"center","text-halign":"center","width":"label","height":"label","padding":"7px"}},
  {selector:'node[listen = "yes"]',style:{"border-width":3,"border-color":"#333"}},
  {selector:"edge",style:{"curve-style":"unbundled-bezier","control-point-distances":ARC,"control-point-weights":.5,
    "width":1.4,"line-color":"data(col)","target-arrow-color":"data(col)","target-arrow-shape":"triangle","arrow-scale":.9,"opacity":.82}},
  {selector:'edge.tree',style:{"line-color":"#aeb3bd","target-arrow-color":"#aeb3bd","width":1}},
  {selector:"edge.showlabel",style:{"label":"data(label)","font-size":9,"color":"#555","text-rotation":"autorotate",
    "text-background-color":"#fbfbfd","text-background-opacity":.9,"text-background-padding":"2px"}},
  {selector:"edge.tree.showlabel",style:{"color":"#9aa0a6","font-style":"italic","font-size":8}},
  {selector:".faded",style:{"opacity":.1,"text-opacity":.1}}]});

const tip=document.getElementById("tip");
cy.on("mouseover","node,edge",e=>{const t=e.target.data("tip");if(t){tip.textContent=t;tip.style.display="block";}});
cy.on("mousemove","node,edge",e=>{tip.style.left=(e.originalEvent.pageX+12)+"px";tip.style.top=(e.originalEvent.pageY+12)+"px";});
cy.on("mouseout","node,edge",()=>tip.style.display="none");
let selectedId=null,hop=null,focus="tree",wTREE=2.6,wIO=.15,radial=false,radK=RAD_K;
const ADJ={};cy.nodes().forEach(n=>ADJ[n.id()]=[]);
EDGES.forEach(e=>{if(ADJ[e.source]&&ADJ[e.target]){ADJ[e.source].push(e.target);ADJ[e.target].push(e.source);}});
function applyForces(t){const s=.2+t*t*12;
  if(focus==="io"){wIO=s;wTREE=.15;radial=false;}
  else if(focus==="radial"){wIO=.3;wTREE=.3;radial=true;radK=RAD_K*(.4+s*.25);}
  else{wIO=.15;wTREE=s;radial=false;}}
function computeHop(){hop={};if(!selectedId)return;const q=[selectedId];hop[selectedId]=0;
  for(let i=0;i<q.length;i++){const u=q[i];(ADJ[u]||[]).forEach(v=>{if(hop[v]===undefined){hop[v]=hop[u]+1;q.push(v);}});}}
const E_TREE=EDGES.filter(e=>e.cls==="tree").map(e=>({s:e.source,t:e.target}));
const E_IO=EDGES.filter(e=>e.cls!=="tree").map(e=>({s:e.source,t:e.target}));
const N=cy.nodes(),sz={},vel={};
N.forEach(n=>{const bb=n.boundingBox();sz[n.id()]={w:bb.w||40,h:bb.h||22};});
let damping=DAMP0,running=true,framed=false;const status=document.getElementById("status");
const R=30*SEP*Math.sqrt(N.length);
cy.batch(()=>N.forEach(n=>{n.position({x:(Math.random()-.5)*2*R,y:(Math.random()-.5)*2*R});vel[n.id()]={vx:0,vy:0};}));
function spring(pos,fx,fy,s,t,k,L){const a=pos[s],b=pos[t];if(!a||!b)return;
  let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||.01,f=(d-L)*k,ux=dx/d,uy=dy/d;fx[s]+=ux*f;fy[s]+=uy*f;fx[t]-=ux*f;fy[t]-=uy*f;}
function tick(){const pos={},fx={},fy={},arr=N;
  arr.forEach(n=>{const id=n.id(),p=n.position();pos[id]={x:p.x,y:p.y};fx[id]=0;fy[id]=0;});
  for(let i=0;i<arr.length;i++){const ai=arr[i].id(),pa=pos[ai];for(let j=i+1;j<arr.length;j++){const bi=arr[j].id(),pb=pos[bi];
    let dx=pa.x-pb.x,dy=pa.y-pb.y,d2=dx*dx+dy*dy||.01,d=Math.sqrt(d2);if(d<15){d=15;d2=225;}
    const f=K_REP/d2,ux=dx/d,uy=dy/d;fx[ai]+=ux*f;fy[ai]+=uy*f;fx[bi]-=ux*f;fy[bi]-=uy*f;
    const A=sz[ai],B=sz[bi],ox=(A.w+B.w)/2+COL_PAD-Math.abs(dx),oy=(A.h+B.h)/2+COL_PAD-Math.abs(dy);
    if(ox>0&&oy>0){if(ox<=oy){const s=(dx===0?Math.random()-.5:(dx<0?-1:1))*ox*COL_K;fx[ai]+=s;fx[bi]-=s;}
      else{const s=(dy===0?Math.random()-.5:(dy<0?-1:1))*oy*COL_K;fy[ai]+=s;fy[bi]-=s;}}}}
  E_IO.forEach(e=>spring(pos,fx,fy,e.s,e.t,.02*wIO,SPR_L));
  E_TREE.forEach(e=>spring(pos,fx,fy,e.s,e.t,.05*wTREE,CONT_L));
  if(radial&&selectedId&&hop){const c=pos[selectedId]||{x:0,y:0};
    arr.forEach(n=>{const id=n.id();if(id===selectedId)return;const tr=((hop[id]!==undefined)?hop[id]:6)*RING;
      let dx=pos[id].x-c.x,dy=pos[id].y-c.y,d=Math.hypot(dx,dy)||.01,f=(tr-d)*radK;fx[id]+=dx/d*f;fy[id]+=dy/d*f;});}
  let maxv=0;cy.batch(()=>arr.forEach(n=>{const id=n.id();
    if(n.grabbed()||(radial&&id===selectedId)){vel[id]={vx:0,vy:0};return;}
    fx[id]-=pos[id].x*GRAV;fy[id]-=pos[id].y*GRAV;const v=vel[id];
    v.vx=(v.vx+fx[id]*STEP)*(1-damping);v.vy=(v.vy+fy[id]*STEP)*(1-damping);
    const sp=Math.hypot(v.vx,v.vy);if(sp>MAX_V){v.vx*=MAX_V/sp;v.vy*=MAX_V/sp;}
    n.position({x:pos[id].x+v.vx,y:pos[id].y+v.vy});if(sp>maxv)maxv=sp;}));
  damping=Math.min(DAMP_MAX,damping+DAMP_RAMP);
  if(status)status.textContent="● settling… v="+maxv.toFixed(1)+" damp="+damping.toFixed(2);
  if(!framed)cy.fit(undefined,40);
  if(maxv<SETTLE&&damping>.5){running=false;framed=true;if(status)status.textContent="✓ settled";}
  if(running)requestAnimationFrame(tick);}
function reheat(k){damping=DAMP0;N.forEach(n=>{const v=vel[n.id()];v.vx+=(Math.random()-.5)*k;v.vy+=(Math.random()-.5)*k;});
  if(!running){running=true;requestAnimationFrame(tick);}}
applyForces(.45);requestAnimationFrame(tick);
cy.on("grab","node",()=>{framed=true;reheat(0);});
cy.on("tap","node",e=>{selectedId=e.target.id();const keep=e.target.closedNeighborhood();
  cy.elements().addClass("faded");keep.removeClass("faded");if(radial){computeHop();reheat(0);}});
cy.on("tap",e=>{if(e.target===cy)cy.elements().removeClass("faded");});
document.getElementById("jiggle").onclick=()=>reheat(JIGGLE);
document.getElementById("fit").onclick=()=>cy.fit(undefined,30);
const fsel=document.getElementById("focus"),str=document.getElementById("strength");
fsel.onchange=()=>{focus=fsel.value;if(focus==="radial"&&selectedId)computeHop();applyForces(+str.value/100);reheat(10*SEP);};
str.oninput=()=>{applyForces(+str.value/100);reheat(0);};
const elbl=document.getElementById("elabels");const al=()=>cy.batch(()=>cy.edges().forEach(x=>x.toggleClass("showlabel",elbl.checked)));
elbl.onchange=al;al();
document.getElementById("count").textContent=NODES.length+" nodes · "+EDGES.length+" edges";
const hide=new Set(),leg=document.getElementById("legend");
TYPES.forEach(t=>{const r=document.createElement("div");r.className="row";
  const c=document.createElement("input");c.type="checkbox";c.checked=true;
  const s=document.createElement("span");s.className="sw";s.style.background=t.color;
  const b=document.createElement("label");b.textContent=t.label;
  c.onchange=()=>{c.checked?hide.delete(t.id):hide.add(t.id);
    cy.batch(()=>cy.nodes().forEach(n=>n.style("display",hide.has(n.data("type"))?"none":"element")));};
  b.onclick=()=>{c.checked=!c.checked;c.onchange();};r.append(c,s,b);leg.append(r);});
</script></body></html>
```

---

## Anti-patterns (these are known failures — avoid)
- Dark theme; `<canvas>`/D3 force; circles/dots; labels outside nodes; mixed shapes.
- A force loop that **never settles**: re-applying full-strength forces forever with only
  constant velocity damping and no rising-damping/alpha cooling and **no stop threshold** →
  perpetual jitter. The loop must anneal and halt.
- Point-only repulsion that ignores box size → labels stack. Use the AABB collision force.
- **Auto-fitting on settle or on every interaction** → yanks the user’s viewport. Frame only
  until first settle, then never again (manual Fit button aside).
- Multi-line detail dumped on nodes → put it in the tooltip; node shows a short identity.
- A strength control that doesn’t **re-energize** on change → can’t escape metastable layouts.
- CDN `<script>` tags → breaks offline use.

## Verify before declaring done
- HTML has **zero** `http(s)` references; opens offline with **no console errors**.
- Node/edge counts match the collector; every node maps to a declared `type`; no edge
  references a missing node.
- Re-run as root vs non-root: non-root degrades gracefully (fewer attributed sockets) and
  prints the sudo hint; counts in `meta` reflect what was captured.
- Sanity-check a couple of known sockets (e.g., your SSH session shows as an ESTABLISHED tcp
  socket owned by `sshd`; a listening service shows a `listen` edge).
- Layout settles (status → ✓), boxes don’t overlap, and Focus=process-tree visibly clusters
  by ancestry while Focus=socket-I/O clusters around listening sockets.

## Output
- `socket_graph.py` (collector + HTML emitter) and the generated `.html` path.
- Print capture summary: host, root/non-root, counts per node type and per edge class, and
  how many sockets couldn’t be attributed to a process.
- Note that it’s a **point-in-time snapshot**; suggest re-running to refresh.
