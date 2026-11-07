/* Карта проекта: космос из частиц. Данные: data/graph.js (build_graph.py). Без внешних зависимостей, кроме three.min.js (r128). */
(function () {
  "use strict";
  const G = window.GRAPH;
  const $ = (id) => document.getElementById(id);
  if (!G || typeof THREE === "undefined") { const e = $("err"); e.style.display = "block"; e.textContent = "Нет данных графа или three.js: запусти build_graph.py и открой страницу через локальный сервер."; return; }
  if (G.project) {
    document.title = G.project + " · Plexus Universe";
    const brand = $("brand");
    if (brand) brand.innerHTML = "<i></i>" + G.project + " · карта проекта";
  }

  const V3 = THREE.Vector3;
  const NOW = Date.now() / 1000;
  const FRESH_S = G.fresh_hours * 3600;
  const STATUS = { idea: 0, art: 1, proto: 2, wip: 3, live: 4, polished: 5, shelved: 6 };
  const SCOL = { idea: "#8aa0c8", art: "#b690ff", proto: "#ffb347", wip: "#4fd8ff", live: "#3ee58f", polished: "#ffe39a", shelved: "#667089" };
  const LCOL = { calls: "#6fe0ff", reads_state: "#b79cff", reads: "#b79cff", persists_to: "#7dffb2", reads_writes: "#7dffb2", writes: "#7dffb2", owns: "#ffd36a", creates: "#ffffff", hosts: "#ffffff", opens: "#ffffff",
    delegates: "#ff8fd0", uses_art: "#9ad0ff", renders: "#9ad0ff", selects_visuals: "#9ad0ff", defines: "#ffd36a", defines_data: "#ffd36a", uses: "#6fe0ff", hosts_mode: "#ffffff", hosts_operation: "#ffffff", accepts_models: "#9ad0ff" };
  const TYPE_RU = { calls: "вызывает", reads_state: "читает состояние", reads: "читает", persists_to: "сохраняет в", reads_writes: "читает и пишет", writes: "пишет в", owns: "владеет", creates: "создаёт", hosts: "содержит", opens: "открывает",
    delegates: "передаёт управление", uses_art: "показывает арты", renders: "рисует", selects_visuals: "определяет облик", defines: "определяет", defines_data: "задаёт данные", uses: "использует", hosts_mode: "содержит режим", hosts_operation: "содержит операцию", accepts_models: "принимает модели", subsystem: "состоит из", primary_hierarchy: "ядро", roster_member: "боец ростера", uses_items: "использует предметы" };

  // ---------------------------------------------------------------- данные
  const N = {}; G.nodes.forEach((n) => { N[n.id] = n; });
  G.nodes.forEach((n) => {
    const t = n.agg_at || n.at; const own = n.at;
    const age = own ? NOW - own : 1e12, ageA = t ? NOW - t : 1e12;
    const f = (a) => (a < 6 * 3600 ? 1 : a < 24 * 3600 ? 0.65 : a < FRESH_S ? 0.4 : 0);
    n.freshOwn = f(age); n.fresh = n.children.length ? f(ageA) * 0.55 : f(age); n.freshAt = n.children.length ? t : own;
    n.expanded = false; n.vis = 0; n.alpha = 0; n.boost = 0; n.pos = new V3(); n.home = new V3(); n.sp = null;
    n.facets = (n.facets || []).map((f2) => Object.assign({ fresh: f2.at && NOW - f2.at < FRESH_S }, f2));
  });
  const root = G.nodes.find((n) => !n.parent);
  const links = G.links.map((l) => Object.assign({}, l, { s: N[l.source], t: N[l.target], kind: l.proposed ? 2 : (l.type === "subsystem" || l.type === "primary_hierarchy" || l.type === "roster_member") ? 0 : 1 }));
  const adj = {}; links.forEach((l) => { (adj[l.s.id] = adj[l.s.id] || []).push(l); (adj[l.t.id] = adj[l.t.id] || []).push(l); });
  const anc = (n) => { const a = []; let p = n.parent && N[n.parent]; while (p) { a.push(p); p = p.parent && N[p.parent]; } return a; };
  const desc = (n, out = []) => { n.children.forEach((c) => { out.push(N[c]); desc(N[c], out); }); return out; };

  // ---------------------------------------------------------------- раскладка
  const phi = 2.399963;
  function basis(d) { const t = Math.abs(d.y) < 0.9 ? new V3(0, 1, 0) : new V3(1, 0, 0); const u = new V3().crossVectors(d, t).normalize(); const v = new V3().crossVectors(d, u); return [u, v]; }
  function layout(p) {
    const kids = p.children.map((c) => N[c]); const m = kids.length; if (!m) return;
    const pp = p.parent ? N[p.parent].home : new V3(); let d = p.home.clone().sub(pp); if (d.length() < 1e-3) d.set(0, 1, 0); d.normalize();
    const [u, v] = basis(d); const rad = (p.tier === 1 ? 92 : p.tier === 2 ? 64 : 50) + 9 * Math.sqrt(m);
    kids.forEach((c, i) => {
      const k = m === 1 ? 0 : i / (m - 1); const cz = 1 - k * 1.3; const sr = Math.sqrt(Math.max(0, 1 - cz * cz)); const a = i * phi + p.tier * 0.7;
      const dir = d.clone().multiplyScalar(cz).add(u.clone().multiplyScalar(sr * Math.cos(a))).add(v.clone().multiplyScalar(sr * Math.sin(a)));
      c.home = p.home.clone().add(dir.multiplyScalar(rad * (0.85 + (i % 3) * 0.1)));
    });
    kids.forEach(layout);
  }
  const pillars = root.children.map((c) => N[c]);
  pillars.forEach((p, i) => { const th = (i / pillars.length) * Math.PI * 2 + 0.35; const R = 270; p.home = new V3(Math.cos(th) * R, (i % 2 ? 1 : -1) * (46 + (i % 3) * 16), Math.sin(th) * R); });
  root.home = new V3(0, 0, 0); pillars.forEach(layout);
  G.nodes.forEach((n) => n.pos.copy(n.parent ? N[n.parent].home : n.home));

  // ---------------------------------------------------------------- three
  const cv = $("gl");
  const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true }); renderer.setPixelRatio(Math.min(2, devicePixelRatio || 1)); renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(48, 1, 1, 6000);
  const uni = { uTime: { value: 0 }, uScale: { value: 1 } };
  function resize() { const w = innerWidth, h = innerHeight; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); uni.uScale.value = h / (2 * Math.tan((camera.fov * Math.PI) / 360)); }
  addEventListener("resize", resize); resize();

  const hex = (c) => new THREE.Color(c);
  const mat = (vs, fs, extra) => new THREE.ShaderMaterial(Object.assign({ uniforms: uni, vertexShader: vs, fragmentShader: fs, transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending }, extra || {}));

  // --- звёзды
  (function stars() {
    const n = 2600, pos = new Float32Array(n * 3), seed = new Float32Array(n), col = new Float32Array(n * 3), siz = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const r = 1500 + Math.random() * 2600, th = Math.random() * 6.283, ph = Math.acos(2 * Math.random() - 1);
      pos.set([r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th)], i * 3); seed[i] = Math.random();
      const c = hex(["#bcd4ff", "#ffe9c4", "#ffffff", "#a8c4ff", "#ffc4e6"][(Math.random() * 5) | 0]); col.set([c.r, c.g, c.b], i * 3); siz[i] = Math.random() < 0.04 ? 3.4 : 0.8 + Math.random() * 1.5;
    }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1)); g.setAttribute("aCol", new THREE.BufferAttribute(col, 3)); g.setAttribute("aSz", new THREE.BufferAttribute(siz, 1));
    const m = mat(`attribute float aSeed; attribute vec3 aCol; attribute float aSz; uniform float uTime; varying vec3 vC; varying float vA;
      void main(){ vC=aCol; vA=0.35+0.5*(0.5+0.5*sin(uTime*(0.4+aSeed*1.6)+aSeed*40.0)); gl_PointSize=aSz*(1.0+0.3*sin(uTime+aSeed*20.0)); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
      `varying vec3 vC; varying float vA; void main(){ vec2 p=gl_PointCoord-0.5; float d=length(p)*2.0; float g=exp(-d*d*3.0); gl_FragColor=vec4(vC,g*vA);}`);
    const pts = new THREE.Points(g, m); pts.renderOrder = 0; scene.add(pts); window.__stars = pts;
  })();

  // --- облака частиц узлов
  const cloudCount = (n) => (n.tier === 0 ? 560 : n.tier === 1 ? 300 : n.tier === 2 ? 150 : 90);
  let P = 0; G.nodes.forEach((n) => { n.pOff = P; n.pN = cloudCount(n); P += n.pN; });
  const cg = new THREE.BufferGeometry();
  const aCenter = new Float32Array(P * 3), aSeed4 = new Float32Array(P * 4), aRad = new Float32Array(P), aColor = new Float32Array(P * 3), aVis = new Float32Array(P), aFresh = new Float32Array(P), aSize = new Float32Array(P);
  G.nodes.forEach((n) => { const c = hex(n.color); for (let i = 0; i < n.pN; i++) { const k = n.pOff + i; aSeed4.set([Math.random(), Math.random(), Math.random(), Math.random()], k * 4); aRad[k] = n.size * 1.9; aColor.set([c.r, c.g, c.b], k * 3); aSize[k] = (0.7 + Math.random() * 1.5) * (0.65 + n.size * 0.045); } });
  cg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(P * 3), 3));
  const A = (name, arr, sz) => { const a = new THREE.BufferAttribute(arr, sz); a.setUsage(THREE.DynamicDrawUsage); cg.setAttribute(name, a); return a; };
  const bCenter = A("aCenter", aCenter, 3), bVis = A("aVis", aVis, 1), bFresh = A("aFresh", aFresh, 1); A("aSeed", aSeed4, 4); A("aRad", aRad, 1); A("aColor", aColor, 3); A("aSize", aSize, 1);
  const cloud = new THREE.Points(cg, mat(`attribute vec3 aCenter; attribute vec4 aSeed; attribute float aRad; attribute vec3 aColor; attribute float aVis; attribute float aFresh; attribute float aSize; uniform float uTime; uniform float uScale; varying vec3 vC; varying float vA;
    void main(){ float t=uTime; float r=aRad*(0.18+0.82*pow(aSeed.x,1.5)); float sp=0.10+aSeed.z*0.30; float a=aSeed.y*6.2831+t*sp/(0.35+aSeed.x*0.9); float b=acos(2.0*aSeed.w-1.0)+0.2*sin(t*0.23+aSeed.y*9.0);
      vec3 off=r*vec3(sin(b)*cos(a),cos(b)*0.78,sin(b)*sin(a)); vec4 mv=modelViewMatrix*vec4(aCenter+off,1.0);
      float tw=1.0+aFresh*0.9*sin(t*(5.0+aSeed.z*7.0)+aSeed.y*30.0); gl_PointSize=max(1.0,aSize*tw*uScale/-mv.z);
      vC=mix(vec3(1.0),aColor,smoothstep(0.0,0.75,aSeed.x*1.15)); vA=aVis*(0.18+0.82*(1.0-aSeed.x))*(0.75+aFresh*0.7*(0.5+0.5*sin(t*4.0+aSeed.y*40.0))); gl_Position=projectionMatrix*mv;}`,
    `varying vec3 vC; varying float vA; void main(){ vec2 p=gl_PointCoord-0.5; float d=length(p)*2.0; float g=exp(-d*d*3.6); gl_FragColor=vec4(vC,g*vA);}`));
  cloud.renderOrder = 2; cloud.frustumCulled = false; scene.add(cloud);

  // --- по одной точке на узел: ореол, ядро, кольцо статуса
  const NN = G.nodes.length; const ng = new THREE.BufferGeometry();
  const nCenter = new Float32Array(NN * 3), nColor = new Float32Array(NN * 3), nSize = new Float32Array(NN), nVis = new Float32Array(NN), nFresh = new Float32Array(NN), nSeed = new Float32Array(NN), nStat = new Float32Array(NN), nProp = new Float32Array(NN), nBoost = new Float32Array(NN), nSel = new Float32Array(NN);
  G.nodes.forEach((n, i) => { n.idx = i; const c = hex(n.color); nColor.set([c.r, c.g, c.b], i * 3); nSize[i] = n.size; nSeed[i] = Math.random(); nStat[i] = STATUS[n.status] ?? 4; nProp[i] = n.proposed ? 1 : 0; });
  ng.setAttribute("position", new THREE.BufferAttribute(new Float32Array(NN * 3), 3));
  const NA = (name, arr, sz) => { const a = new THREE.BufferAttribute(arr, sz); a.setUsage(THREE.DynamicDrawUsage); ng.setAttribute(name, a); return a; };
  const nbC = NA("aCenter", nCenter, 3), nbV = NA("aVis", nVis, 1), nbF = NA("aFresh", nFresh, 1), nbB = NA("aBoost", nBoost, 1), nbS = NA("aSel", nSel, 1); NA("aColor", nColor, 3); NA("aSize", nSize, 1); NA("aSeed", nSeed, 1); NA("aStat", nStat, 1); NA("aProp", nProp, 1);
  const NV = `attribute vec3 aCenter; attribute vec3 aColor; attribute float aSize; attribute float aVis; attribute float aFresh; attribute float aSeed; attribute float aStat; attribute float aProp; attribute float aBoost; attribute float aSel;
    uniform float uTime; uniform float uScale; varying vec3 vC; varying float vV; varying float vF; varying float vS; varying float vSt; varying float vP; varying float vB; varying float vSel;`;
  const nodeMat = (diam, frag) => mat(NV + `void main(){ vC=aColor; vV=aVis; vF=aFresh; vS=aSeed; vSt=aStat; vP=aProp; vB=aBoost; vSel=aSel; vec4 mv=modelViewMatrix*vec4(aCenter,1.0); gl_PointSize=max(2.0,(${diam})*uScale/-mv.z); gl_Position=projectionMatrix*mv; }`,
    `varying vec3 vC; varying float vV; varying float vF; varying float vS; varying float vSt; varying float vP; varying float vB; varying float vSel; uniform float uTime;` + frag);
  const halo = new THREE.Points(ng, nodeMat("aSize*(5.2+1.2*aBoost+0.6*aSel)", `void main(){ vec2 p=gl_PointCoord-0.5; float d=length(p)*2.0;
      float g=exp(-d*d*5.5)*0.55+exp(-d*d*22.0)*0.5; float w=fract(uTime*0.32+vS); float ring=exp(-pow((d-w*0.95)*16.0,2.0))*(1.0-w)*vF;
      float pulse=0.88+0.12*sin(uTime*1.3+vS*20.0); gl_FragColor=vec4(vC*(g*pulse*(1.0+vB*0.8)+ring*1.6),(g*0.8*(1.0+vB*0.7)+ring)*vV);}`)); halo.renderOrder = 1;
  const core = new THREE.Points(ng, nodeMat("aSize*(0.95+0.4*aBoost)", `void main(){ vec2 p=gl_PointCoord-0.5; float d=length(p)*2.0; float g=exp(-d*d*9.0); float tw=1.0+vF*0.7*sin(uTime*(7.0+vS*8.0)+vS*50.0);
      gl_FragColor=vec4(mix(vC,vec3(1.0),0.78)*g*tw,g*vV*(0.95+0.4*vB));}`)); core.renderOrder = 4;
  const ringM = new THREE.Points(ng, nodeMat("aSize*4.3", `float seg(float a,float n,float duty){ return step(fract(a*n),duty); }
    vec3 stCol(float s){ if(s<0.5) return vec3(0.54,0.63,0.78); if(s<1.5) return vec3(0.71,0.56,1.0); if(s<2.5) return vec3(1.0,0.70,0.28); if(s<3.5) return vec3(0.31,0.85,1.0); if(s<4.5) return vec3(0.24,0.9,0.56); if(s<5.5) return vec3(1.0,0.89,0.6); return vec3(0.4,0.44,0.54); }
    void main(){ vec2 p=gl_PointCoord-0.5; float d=length(p)*2.0; float a=atan(p.y,p.x)/6.2831+0.5; float r0=0.42;
      float line=exp(-pow((d-r0)*60.0,2.0)); float m=1.0; float st=vSt; float rot=a+uTime*0.04;
      if(st<0.5) m=seg(rot*1.0,16.0,0.35); else if(st>1.5&&st<2.5) m=seg(rot+uTime*0.05,9.0,0.58); else if(st>2.5&&st<3.5){ m=step(fract(a-uTime*0.35),0.72);} else if(st>5.5) m=seg(a,28.0,0.3);
      float alpha=line*m*(st>3.5&&st<4.5?0.34:0.8); float l2=0.0; if(st>4.5&&st<5.5) l2=exp(-pow((d-0.5)*60.0,2.0))*0.7;
      float pr=0.0; if(vP>0.5){ pr=exp(-pow((d-0.62)*55.0,2.0))*seg(a-uTime*0.02,26.0,0.45)*0.7; }
      float sel=exp(-pow((d-0.5)*45.0,2.0))*vSel*0.9; vec3 col=stCol(st); float fa=vV*(alpha+l2)+vV*pr*0.8+vSel*sel;
      gl_FragColor=vec4(mix(col,vec3(1.0),vP*pr*0.6)*1.0,fa);}`)); ringM.renderOrder = 3;
  [halo, core, ringM].forEach((o) => { o.frustumCulled = false; scene.add(o); });

  // --- грани: орбитальные точки (арт / модель / бой ...)
  const FMAX = 3 * NN; const fg = new THREE.BufferGeometry();
  const fC = new Float32Array(FMAX * 3), fOn = new Float32Array(FMAX), fFr = new Float32Array(FMAX), fCol = new Float32Array(FMAX * 3), fVis = new Float32Array(FMAX);
  fg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(FMAX * 3), 3));
  const FA = (name, arr, sz) => { const a = new THREE.BufferAttribute(arr, sz); a.setUsage(THREE.DynamicDrawUsage); fg.setAttribute(name, a); return a; };
  const fbC = FA("aCenter", fC, 3), fbV = FA("aVis", fVis, 1), fbO = FA("aOn", fOn, 1), fbF = FA("aFr", fFr, 1); FA("aColor", fCol, 3);
  const fpts = new THREE.Points(fg, mat(`attribute vec3 aCenter; attribute vec3 aColor; attribute float aVis; attribute float aOn; attribute float aFr; uniform float uScale; uniform float uTime; varying vec3 vC; varying float vV; varying float vO; varying float vF;
    void main(){ vC=aColor; vV=aVis; vO=aOn; vF=aFr; vec4 mv=modelViewMatrix*vec4(aCenter,1.0); gl_PointSize=max(3.0,(2.6+aFr*0.9*sin(uTime*6.0))*uScale/-mv.z); gl_Position=projectionMatrix*mv;}`,
    `varying vec3 vC; varying float vV; varying float vO; varying float vF; uniform float uTime; void main(){ vec2 p=gl_PointCoord-0.5; float d=length(p)*2.0; float fill=exp(-d*d*7.0); float ring=exp(-pow((d-0.62)*10.0,2.0));
      vec3 c=mix(vec3(0.5,0.58,0.78),vC,vO); float a=vO>0.5?(fill+0.35*ring):(ring*0.55); if(vF>0.5){ c=vec3(1.0,0.89,0.55); a+=0.4*exp(-d*d*3.0); } gl_FragColor=vec4(c,a*vV);}`));
  fpts.renderOrder = 5; fpts.frustumCulled = false; scene.add(fpts);

  // --- связи: изящные дуги с бегущим светом
  const SEG = 24; const L = links.length; const lg = new THREE.BufferGeometry(); const LV = L * SEG * 2;
  const lPos = new Float32Array(LV * 3), lT = new Float32Array(LV), lSeed = new Float32Array(LV), lA = new Float32Array(LV * 3), lB = new Float32Array(LV * 3), lAl = new Float32Array(LV), lKind = new Float32Array(LV), lHi = new Float32Array(LV);
  links.forEach((l, li) => {
    l.seed = Math.random(); l.sign = Math.random() < 0.5 ? -1 : 1;
    const ca = hex(l.kind === 1 || l.kind === 2 ? LCOL[l.type] || "#7fa0d8" : l.s.color), cb = hex(l.kind === 1 || l.kind === 2 ? LCOL[l.type] || "#7fa0d8" : l.t.color);
    for (let s = 0; s < SEG; s++) for (let e = 0; e < 2; e++) {
      const v = (li * SEG + s) * 2 + e; lT[v] = (s + e) / SEG; lSeed[v] = l.seed; lA.set([ca.r, ca.g, ca.b], v * 3); lB.set([cb.r, cb.g, cb.b], v * 3); lKind[v] = l.kind;
    }
  });
  lg.setAttribute("position", new THREE.BufferAttribute(lPos, 3).setUsage(THREE.DynamicDrawUsage));
  const lbAl = new THREE.BufferAttribute(lAl, 1).setUsage(THREE.DynamicDrawUsage), lbHi = new THREE.BufferAttribute(lHi, 1).setUsage(THREE.DynamicDrawUsage);
  lg.setAttribute("aAl", lbAl); lg.setAttribute("aHi", lbHi); lg.setAttribute("aT", new THREE.BufferAttribute(lT, 1)); lg.setAttribute("aSeed", new THREE.BufferAttribute(lSeed, 1)); lg.setAttribute("aA", new THREE.BufferAttribute(lA, 3)); lg.setAttribute("aB", new THREE.BufferAttribute(lB, 3)); lg.setAttribute("aKind", new THREE.BufferAttribute(lKind, 1));
  const lineMesh = new THREE.LineSegments(lg, mat(`attribute float aT; attribute float aSeed; attribute vec3 aA; attribute vec3 aB; attribute float aAl; attribute float aKind; attribute float aHi; varying vec3 vC; varying float vA; varying float vT; varying float vK; varying float vH; varying float vS;
    void main(){ vC=mix(aA,aB,aT); vA=aAl; vT=aT; vK=aKind; vH=aHi; vS=aSeed; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    `varying vec3 vC; varying float vA; varying float vT; varying float vK; varying float vH; varying float vS; uniform float uTime;
    void main(){ float edge=smoothstep(0.0,0.08,vT)*smoothstep(1.0,0.92,vT); float flow=pow(0.5+0.5*sin(6.2831*(vT*1.4-uTime*(0.10+0.07*vS)+vS)),9.0);
      float a=vA*edge*(0.42+1.6*flow*(0.5+vH)); if(vK>1.5) a*=step(0.45,fract(vT*34.0)); gl_FragColor=vec4(vC*(0.8+0.9*flow+0.5*vH),a);}`));
  lineMesh.renderOrder = 0.5; lineMesh.frustumCulled = false; scene.add(lineMesh);

  // ---------------------------------------------------------------- камера
  const cam = { yaw: 0.62, pitch: 0.62, dist: 860, tx: 0, ty: 0, tz: 0, gyaw: null, gdist: 860, gt: new V3(), idle: 0, drawer: 0 };
  function visibleDesc(n) { return desc(n).filter((d) => d.target); }
  let focus = root, selected = null, hover = null, filterFresh = false; const statusOff = {};
  function setFocus(n, quick) {
    focus = n; $("news").classList.toggle("min", n.tier > 0); const vd = [n].concat(visibleDesc(n)); const c = new V3(); vd.forEach((d) => c.add(d.home)); c.divideScalar(vd.length); let r = 0; vd.forEach((d) => { r = Math.max(r, d.home.distanceTo(c)); });
    if (n.tier === 0) { cam.gdist = 900; c.set(0, 0, 0); } else cam.gdist = Math.max(250, r * 2.05 + 150);
    cam.gt.copy(c); if (quick) { cam.tx = c.x; cam.ty = c.y; cam.tz = c.z; cam.dist = cam.gdist; } crumbs();
  }
  function updateTargets() {
    G.nodes.forEach((n) => { n.target = !n.parent || (anc(n).every((a) => a.expanded)); });
  }
  function expand(n) { n.expanded = true; n.children.forEach((c) => { if (N[c].autoexpand) expand(N[c]); }); updateTargets(); }
  function collapse(n) { n.expanded = false; desc(n).forEach((d) => { d.expanded = false; }); updateTargets(); }
  root.expanded = true; updateTargets();
  function reveal(n) { anc(n).reverse().forEach((a) => { if (!a.expanded) expand(a); }); updateTargets(); }

  // ---------------------------------------------------------------- DOM: подписи
  const labels = $("labels"); G.nodes.forEach((n) => {
    const d = document.createElement("div"); d.className = "lbl t" + Math.min(3, n.tier); d.style.color = n.color; d.textContent = n.label;
    const sm = document.createElement("small"); d.appendChild(sm); labels.appendChild(d); n.el = d; n.sm = sm;
    d.style.pointerEvents = "auto"; d.style.cursor = "pointer";
    d.addEventListener("click", (e) => { e.stopPropagation(); onClick(n); });
    d.addEventListener("pointerenter", () => { hover = n; hoverSince = clock.elapsedTime; showCard(n); });
    d.addEventListener("pointerleave", () => { hideCard(); });
  });
  const ago = (s) => { const d = NOW - s; return d < 90 ? "только что" : d < 5400 ? Math.round(d / 60) + " мин назад" : d < 129600 ? Math.round(d / 3600) + " ч назад" : Math.round(d / 86400) + " дн назад"; };
  const fmtDate = (s) => new Date(s * 1000).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  function crumbs() { const c = $("crumbs"); c.innerHTML = ""; const chain = anc(focus).reverse().concat([focus]); chain.forEach((n, i) => { if (i) { const s = document.createElement("span"); s.className = "sep"; s.textContent = "›"; c.appendChild(s); } const b = document.createElement("b"); b.textContent = n.tier === 0 ? "Вселенная проекта" : n.label; b.style.color = n.color; b.onclick = () => { if (n !== focus) { setFocus(n); } }; c.appendChild(b); }); }

  // ---------------------------------------------------------------- левая панель и легенда
  const newsItems = G.nodes.filter((n) => n.tier >= 2 && !n.children.length && n.at && NOW - n.at < FRESH_S).concat(G.nodes.filter((n) => n.tier >= 2 && n.children.length && n.at && NOW - n.at < FRESH_S)).sort((a, b) => b.at - a.at);
  const seenP = {}; const news = []; newsItems.forEach((n) => { const k = n.changes[0] && n.changes[0].path; if (news.length < 7 && !seenP[n.id]) { seenP[n.id] = 1; news.push(n); } });
  $("newsList").innerHTML = news.map((n) => `<div class="it" data-id="${n.id}"><span class="dot" style="background:${n.color};color:${n.color}"></span><div><b style="color:${n.color}">${n.label}</b><small>${ago(n.at)} · ${(n.changes[0] ? n.changes[0].path.split("/").pop() : "")}</small></div></div>`).join("") || '<div class="it"><small>За 48 часов изменений нет</small></div>';
  $("newsList").onclick = (e) => { const it = e.target.closest(".it"); if (it && it.dataset.id) goTo(N[it.dataset.id]); };
  const freshCount = G.nodes.filter((n) => n.freshOwn > 0 || n.fresh > 0).length; $("freshN").textContent = "· " + freshCount;
  const stNames = G.status_names;
  $("legBody").innerHTML = Object.keys(STATUS).map((k) => `<div class="row" data-s="${k}"><span class="ring ${k === "idea" || k === "proto" ? "dash" : k === "shelved" ? "dot2" : ""}" style="border-color:${SCOL[k]};${k === "wip" ? "border-right-color:transparent" : ""}"></span>${stNames[k]}</div>`).join("")
    + `<hr><div class="row" style="cursor:default"><span class="dot" style="background:#ffe39a;box-shadow:0 0 8px #ffe39a"></span>мерцает: менялось за 48 ч</div>`
    + `<div class="row" style="cursor:default"><span class="ring dot2" style="border-color:#fff;width:15px"></span>пунктир снаружи: предложено ревью, ждёт Codex</div>`
    + `<div class="row" style="cursor:default"><span class="dot" style="background:#9fb7ff"></span>точки вокруг узла: арт · модель · бой / код · тесты</div>`;
  $("legBody").onclick = (e) => { const r = e.target.closest(".row"); if (r && r.dataset.s) { statusOff[r.dataset.s] = !statusOff[r.dataset.s]; r.classList.toggle("off", !!statusOff[r.dataset.s]); } };
  $("legT").onclick = () => $("legend").classList.toggle("min"); if (innerHeight < 720) $("legend").classList.add("min");
  $("news").querySelector("h4").onclick = () => $("news").classList.toggle("min");
  $("fFresh").onclick = () => { filterFresh = !filterFresh; $("fFresh").classList.toggle("on", filterFresh); };

  // ---------------------------------------------------------------- навигация
  function goTo(n) { reveal(n); selected = n; openDrawer(n); setFocus(n.parent ? N[n.parent] : n); if (n.children.length) { expand(n); setFocus(n); } }
  const sInput = $("search"), sRes = $("results");
  sInput.oninput = () => { const q = sInput.value.trim().toLowerCase(); if (!q) { sRes.style.display = "none"; return; } const hits = G.nodes.filter((n) => (n.label + " " + n.id + " " + n.human).toLowerCase().includes(q)).slice(0, 12);
    sRes.innerHTML = hits.map((n) => `<div data-id="${n.id}"><span class="dot" style="background:${n.color}"></span>${n.label}<em>${n.status_text || stNames[n.status]}</em></div>`).join(""); sRes.style.display = hits.length ? "block" : "none"; };
  sRes.onclick = (e) => { const d = e.target.closest("div[data-id]"); if (d) { goTo(N[d.dataset.id]); sRes.style.display = "none"; sInput.blur(); } };
  addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== sInput) { e.preventDefault(); sInput.focus(); return; }
    if (e.key === "Escape") { if (document.activeElement === sInput) { sInput.blur(); sRes.style.display = "none"; return; } if ($("lb").classList.contains("on")) { $("lb").classList.remove("on"); return; } if (selected) { closeDrawer(); return; } if (focus.parent) { const p = N[focus.parent]; collapse(focus); setFocus(p); } }
    if ((e.key === "r" || e.key === "R") && document.activeElement !== sInput) { desc(root).forEach((d) => (d.expanded = false)); updateTargets(); closeDrawer(); setFocus(root); cam.gyaw = 0.62; }
  });

  // ---------------------------------------------------------------- правая панель
  const drawer = $("drawer"), dbody = $("dbody");
  function closeDrawer() { selected = null; drawer.classList.remove("on"); }
  $("dx").onclick = closeDrawer;
  $("lb").onclick = () => $("lb").classList.remove("on");
  function summary(n) {
    const ds = desc(n); const by = {}; ds.forEach((d) => { by[d.status] = (by[d.status] || 0) + 1; }); const fr = ds.filter((d) => d.freshOwn > 0).length;
    return `<li>Внутри ${ds.length} узлов: ${Object.keys(by).map((s) => `<span style="color:${SCOL[s]}">${by[s]} ${stNames[s].toLowerCase()}</span>`).join(", ")}</li>${fr ? `<li class="tag">● свежих за 48 ч: ${fr}</li>` : ""}`;
  }
  function openDrawer(n) {
    const sc = SCOL[n.status]; const out = (adj[n.id] || []).filter((l) => l.kind !== 0 || l.s === n); const ins = [], outs = [];
    (adj[n.id] || []).forEach((l) => { if (l.kind === 0) return; (l.s === n ? outs : ins).push(l); });
    const li = (l, other) => `<li><a data-go="${other.id}" style="color:${other.color}">${other.label}</a> <span style="color:var(--dim)">· ${TYPE_RU[l.type] || l.type}</span>${l.proposed ? ' <span class="tag">· по ревью</span>' : ""}${l.label ? `<br><span style="color:var(--faint);font-size:11px">${l.label}</span>` : ""}</li>`;
    dbody.innerHTML = `<h2 style="color:${n.color};text-shadow:0 0 16px ${n.color}">${n.label}</h2><div class="st" style="color:${sc}">${n.status_text || stNames[n.status]}</div>${n.proposed ? ' <span class="st" style="color:#fff">предложено ревью</span>' : ""}
      <p style="color:#c9d5f2;margin:0 0 8px">${n.human}</p>${n.note ? `<p class="tag">${n.note}</p>` : ""}
      ${n.children && n.children.length ? `<div style="margin:8px 0 10px"><button id="dr-toggle-expand" style="width:100%;padding:7px 12px;background:rgba(255,255,255,0.06);border:1px solid ${n.color};color:#fff;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:background .15s"><span>${n.expanded ? "⊟ Свернуть подузлы" : "⊞ Раскрыть подузлы (" + n.children.length + ")"}</span><span style="color:${n.color}">↵</span></button></div>` : ""}
      <h5>Состояние</h5><ul>${n.children.length ? summary(n) : ""}${n.facets.map((f) => `<li>${f.on ? "●" : "○"} ${f.label}${f.at ? ` <span style="color:var(--dim)">· ${ago(f.at)}</span>` : ""}${f.fresh ? ' <span class="tag">новое</span>' : ""}</li>`).join("") || "<li style='color:var(--dim)'>—</li>"}</ul>
      <h5>Последние изменения</h5><ul>${n.changes.map((c) => `<li><code>${c.path.length > 44 ? "…" + c.path.slice(-43) : c.path}</code><br><span style="color:var(--dim);font-size:11px">${fmtDate(c.at)} · ${ago(c.at)}</span></li>`).join("") || "<li style='color:var(--dim)'>нет данных</li>"}</ul>
      ${outs.length ? `<h5>Обращается к</h5><ul>${outs.map((l) => li(l, l.t)).join("")}</ul>` : ""}${ins.length ? `<h5>Используется из</h5><ul>${ins.map((l) => li(l, l.s)).join("")}</ul>` : ""}
      ${n.children.length ? `<h5>Внутри (${n.children.length})</h5><ul>${n.children.map((c) => `<li><a data-go="${c}" style="color:${N[c].color}">${N[c].label}</a></li>`).join("")}</ul>` : ""}
      ${n.arts.length ? `<h5>Арты (${n.arts.length})</h5><div class="gal">${n.arts.map((k) => `<div data-art="${k}" style="background-image:url('${G.arts[k].file}')" title="${G.arts[k].caption}"></div>`).join("")}</div>` : ""}
      <h5>Источники</h5><ul>${n.paths.slice(0, 8).map((p) => `<li><code>${p}</code></li>`).join("")}</ul><p style="color:var(--faint);font-size:11px;margin-top:14px">${n.codex_state || ""}</p>`;
    drawer.classList.add("on"); drawer.scrollTop = 0;
  }
  dbody.onclick = (e) => {
    const tog = e.target.closest("#dr-toggle-expand");
    if (tog && selected && selected.children.length) {
      if (selected.expanded) { collapse(selected); setFocus(selected.parent ? N[selected.parent] : selected); }
      else { expand(selected); setFocus(selected); }
      openDrawer(selected);
      return;
    }
    const a = e.target.closest("[data-go]"); if (a) { goTo(N[a.dataset.go]); return; } const g = e.target.closest("[data-art]"); if (g) { const k = g.dataset.art; $("lbi").src = G.arts[k].file; $("lbc").textContent = G.arts[k].caption; $("lb").classList.add("on"); } };

  // ---------------------------------------------------------------- карточка при наведении
  const hc = $("hc"), hcm = $("hcm"), hcs = $("hcsvg"); let hcNode = null, hcT = 0, hcShown = null;
  hcm.style.pointerEvents = "auto";
  hcm.style.cursor = "pointer";
  hcm.addEventListener("click", (e) => {
    e.stopPropagation();
    if (hover) onClick(hover);
  });
  function buildCard(n) {
    const c = n.color, sc = SCOL[n.status]; hc.style.setProperty("--c", c);
    const hero = n.hero ? G.arts[n.hero].file : "";
    const fac = n.facets.map((f) => `<span class="${f.on ? "on" : ""} ${f.fresh ? "fresh" : ""}">${f.on ? "●" : "○"} ${f.label}${f.fresh ? " · новое" : ""}</span>`).join("");
    const fr = n.freshAt && NOW - n.freshAt < FRESH_S ? `<div class="fr">обновлено ${ago(n.freshAt)}</div>` : "";
    hcm.innerHTML = `<div class="hero" style="background-image:url('${hero}')"><div class="st" style="color:${sc}">${n.status_text || stNames[n.status]}${n.proposed ? " · по ревью" : ""}</div>${fr}</div>
      <div class="body"><h3>${n.label}</h3><p>${n.human}</p>${fac ? `<div class="fac">${fac}</div>` : ""}<div class="hint"><span>${n.children.length ? "внутри: " + n.children.length : n.tests && n.tests.length ? "тесты: " + n.tests.join(", ") : ""}</span><span>${n.children.length ? (n.expanded ? "клик — свернуть" : "клик — раскрыть") : "клик — подробности"}</span></div></div>`;
    hc.querySelectorAll(".sat").forEach((s) => s.remove());
    n.sats.forEach((s, i) => { const d = document.createElement("div"); d.className = "sat"; d.style.setProperty("--i", i); d.style.setProperty("--d", 5 + (i % 3) * 1.4 + "s"); d.style.setProperty("--fx", (i % 2 ? 4 : -4) + "px"); d.style.setProperty("--fy", (i % 2 ? -6 : 5) + "px");
      d.innerHTML = `<div class="im" style="background-image:url('${G.arts[s.art].file}')"></div><span>${s.caption}</span>`; hc.appendChild(d); s.el = d; });
  }
  function placeCard(n) {
    const sp = n.sp; if (!sp) return; const W = innerWidth, H = innerHeight, cw = 300, ch = hcm.offsetHeight || 330; const right = sp.x < W * 0.55;
    let mx = right ? sp.x + 78 : sp.x - 78 - cw, my = Math.min(H - ch - 16, Math.max(70, sp.y - ch * 0.42)); if (drawer.classList.contains("on")) mx = Math.min(mx, W - 360 - cw - 20);
    hcm.style.left = mx + "px"; hcm.style.top = my + "px";
    const cxm = mx + cw / 2, cym = my + ch / 2; let path = ""; const cols = n.color;
    const k = n.sats.length; const side = right ? 1 : -1; const baseX = right ? mx + cw : mx; const stepY = Math.min(104, (H - 120) / Math.max(1, k)); const span = stepY * (k - 1);
    n.sats.forEach((s, i) => { const t = k === 1 ? 0.5 : i / (k - 1); const u = k === 1 ? 0 : (t - 0.5) * 2; const py = Math.min(H - 110, Math.max(60, cym - span / 2 + i * stepY - 46)); const arcX = 26 + (1 - u * u) * 58;
      const px = right ? baseX + arcX : baseX - arcX - 112; s.el.style.left = px + "px"; s.el.style.top = py + "px";
      const sx = baseX, sy = my + ch * (0.25 + 0.5 * t), ex = right ? px : px + 112, ey = py + 46; path += `<path d="M${sx} ${sy} Q${(sx + ex) / 2} ${(sy + ey) / 2 - 18 * side} ${ex} ${ey}" stroke="${cols}"/>`; });
    path += `<path d="M${sp.x} ${sp.y} Q${(sp.x + (right ? mx : mx + cw)) / 2} ${sp.y - 18} ${right ? mx : mx + cw} ${my + ch * 0.4}" stroke="${cols}" style="stroke-dasharray:none;opacity:.8"/>`; hcs.innerHTML = path;
  }
  function showCard(n) { if (hcShown === n) { placeCard(n); return; } hcShown = n; buildCard(n); hc.classList.add("on"); requestAnimationFrame(() => placeCard(n)); }
  function hideCard() { hcShown = null; hc.classList.remove("on"); }

  // ---------------------------------------------------------------- мышь
  let drag = null, moved = 0; const mouse = { x: -1, y: -1 };
  cv.addEventListener("pointerdown", (e) => {
    drag = { x: e.clientX, y: e.clientY, btn: e.button, yaw: cam.yaw, pitch: cam.pitch, t: new V3(cam.tx, cam.ty, cam.tz), downNode: hover };
    moved = 0; cam.idle = 0; cv.setPointerCapture(e.pointerId); hideCard();
  });
  cv.addEventListener("pointermove", (e) => {
    mouse.x = e.clientX; mouse.y = e.clientY;
    if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved = Math.max(moved, Math.abs(dx) + Math.abs(dy)); cam.idle = 0;
    if (drag.btn === 0 && !e.shiftKey) { cam.yaw = drag.yaw - dx * 0.0055; cam.pitch = Math.max(-1.35, Math.min(1.35, drag.pitch + dy * 0.0055)); cam.gyaw = null; }
    else { const k = cam.dist * 0.0016; const r = new V3(Math.cos(cam.yaw), 0, -Math.sin(cam.yaw)), u = new V3(0, 1, 0); cam.tx = drag.t.x - r.x * dx * k; cam.ty = drag.t.y + dy * k; cam.tz = drag.t.z - r.z * dx * k; cam.gt.set(cam.tx, cam.ty, cam.tz); }
  });
  cv.addEventListener("pointerup", (e) => {
    const was = moved < 6 && drag && drag.btn === 0;
    const clicked = drag ? (drag.downNode || hover) : hover;
    drag = null;
    if (was) onClick(clicked);
  });
  cv.addEventListener("contextmenu", (e) => e.preventDefault());
  cv.addEventListener("wheel", (e) => { e.preventDefault(); cam.gdist = Math.max(120, Math.min(2200, cam.gdist * Math.exp(e.deltaY * 0.0012))); cam.idle = 0; hideCard(); }, { passive: false });
  cv.addEventListener("pointerleave", () => { mouse.x = -1; });
  function onClick(clickedNode) {
    const n = clickedNode || hover; if (!n) { if (selected) closeDrawer(); return; }
    selected = n; openDrawer(n);
    if (n.children && n.children.length) {
      if (n.expanded) { collapse(n); setFocus(n.parent ? N[n.parent] : n); }
      else { expand(n); setFocus(n); }
    } else if (n.parent) setFocus(N[n.parent]);
  }

  // ---------------------------------------------------------------- цикл
  const clock = new THREE.Clock(); const tmp = new V3(); let lastHover = null, hoverSince = 0;
  const lerp = (a, b, k) => a + (b - a) * k;
  function inFocusSet(n) { if (focus.tier === 0) return 1; if (n === focus || anc(focus).includes(n) || anc(n).includes(focus)) return 1; if (n.parent && n.parent === focus.parent) return 0.55; if (focus.parent && n.id === focus.parent) return 1; return 0.2; }
  function linkAlphaPair(l) { return Math.min(l.s.vis, l.t.vis); }
  function frame() {
    const dt = Math.min(0.05, clock.getDelta()), t = clock.elapsedTime; uni.uTime.value = t; cam.idle += dt;
    // камера
    const k = 1 - Math.exp(-dt * 3.2); cam.dist = lerp(cam.dist, cam.gdist, k); cam.tx = lerp(cam.tx, cam.gt.x, drag ? 0 : k); cam.ty = lerp(cam.ty, cam.gt.y, drag ? 0 : k); cam.tz = lerp(cam.tz, cam.gt.z, drag ? 0 : k);
    if (cam.gyaw !== null) { cam.yaw = lerp(cam.yaw, cam.gyaw, k); if (Math.abs(cam.yaw - cam.gyaw) < 0.003) cam.gyaw = null; } else if (cam.idle > 6 && !drag) cam.yaw += dt * 0.025;
    const cp = Math.cos(cam.pitch); const right = new V3(Math.cos(cam.yaw), 0, -Math.sin(cam.yaw)); cam.drawer = lerp(cam.drawer, drawer.classList.contains("on") ? 1 : 0, k);
    const tgt = new V3(cam.tx, cam.ty, cam.tz).add(right.clone().multiplyScalar(cam.dist * 0.16 * cam.drawer));
    camera.position.set(tgt.x + cam.dist * cp * Math.sin(cam.yaw), tgt.y + cam.dist * Math.sin(cam.pitch), tgt.z + cam.dist * cp * Math.cos(cam.yaw)); camera.lookAt(tgt); camera.updateMatrixWorld();
    if (window.__stars) window.__stars.rotation.y = t * 0.002;
    // узлы
    const W = innerWidth, H = innerHeight; let best = null, bd = 1e9; const hl = new Set();
    const hn = hover || selected; if (hn) { hl.add(hn.id); (adj[hn.id] || []).forEach((l) => { hl.add(l.s.id); hl.add(l.t.id); }); }
    G.nodes.forEach((n, i) => {
      const goal = n.target ? 1 : 0; n.vis = lerp(n.vis, goal, 1 - Math.exp(-dt * (goal ? 3.4 : 5)));
      const des = n.target ? n.home : (n.parent ? N[n.parent].pos : n.home); n.pos.lerp(des, 1 - Math.exp(-dt * 4.2));
      const df = inFocusSet(n); let dim = df; if (filterFresh) dim *= n.freshOwn > 0 || n.fresh > 0 ? 1 : 0.14; if (statusOff[n.status]) dim *= 0.1; n.dim = lerp(n.dim === undefined ? 1 : n.dim, dim, k);
      n.alpha = n.vis * n.dim; n.boost = lerp(n.boost, n === hover || n === selected ? 1 : 0, 1 - Math.exp(-dt * 8));
      const j3 = i * 3; nCenter[j3] = n.pos.x; nCenter[j3 + 1] = n.pos.y; nCenter[j3 + 2] = n.pos.z; nVis[i] = n.alpha; nFresh[i] = n.fresh * (filterFresh ? 1.3 : 1); nBoost[i] = n.boost; nSel[i] = n === selected ? 1 : 0;
      for (let p = 0; p < n.pN; p++) { const q = n.pOff + p, q3 = q * 3; aCenter[q3] = n.pos.x; aCenter[q3 + 1] = n.pos.y; aCenter[q3 + 2] = n.pos.z; aVis[q] = n.alpha * (0.85 + 0.9 * n.boost); aFresh[q] = n.fresh; }
      // экран
      tmp.copy(n.pos).project(camera); const vis = n.alpha > 0.25 && tmp.z < 1; n.sp = vis ? { x: (tmp.x * 0.5 + 0.5) * W, y: (-tmp.y * 0.5 + 0.5) * H, z: tmp.z } : null;
      if (n.sp) { const dist = camera.position.distanceTo(n.pos); const pr = Math.max(15, (n.size * 2.2 * uni.uScale.value) / dist); const d = Math.hypot(n.sp.x - mouse.x, n.sp.y - mouse.y); const hitPr = Math.max(22, pr); if (mouse.x >= 0 && d < hitPr && d < bd) { bd = d; best = n; } n.sp.dist = dist; n.sp.pr = hitPr; }
    });
    bCenter.needsUpdate = bVis.needsUpdate = bFresh.needsUpdate = true; nbC.needsUpdate = nbV.needsUpdate = nbF.needsUpdate = nbB.needsUpdate = nbS.needsUpdate = true;
    if (best !== hover) { hover = best; hoverSince = t; cv.style.cursor = hover ? "pointer" : "default"; }
    // грани
    let fi = 0; G.nodes.forEach((n) => { n.facets.forEach((f, j) => { if (fi >= FMAX) return; const R = n.size * 2.6, a = t * 0.22 + (j / Math.max(1, n.facets.length)) * 6.2831 + n.idx; const q3 = fi * 3;
      fC[q3] = n.pos.x + Math.cos(a) * R; fC[q3 + 1] = n.pos.y + Math.sin(a * 0.7) * R * 0.45; fC[q3 + 2] = n.pos.z + Math.sin(a) * R; const c = hex(n.color); fCol[q3] = c.r; fCol[q3 + 1] = c.g; fCol[q3 + 2] = c.b;
      fOn[fi] = f.on ? 1 : 0; fFr[fi] = f.fresh ? 1 : 0; fVis[fi] = n.tier >= 2 ? n.alpha * (0.5 + 0.5 * Math.min(1, 420 / camera.position.distanceTo(n.pos))) * (n.sp ? 1 : 0.2) : 0; fi++; }); });
    for (; fi < FMAX; fi++) fVis[fi] = 0; fbC.needsUpdate = fbV.needsUpdate = fbO.needsUpdate = fbF.needsUpdate = true;
    // связи
    const P0 = new V3(), P1 = new V3(), C = new V3(), up = new V3(0, 1, 0);
    links.forEach((l, li) => {
      P0.copy(l.s.pos); P1.copy(l.t.pos); const len = P0.distanceTo(P1); const mid = P0.clone().add(P1).multiplyScalar(0.5); const dir = P1.clone().sub(P0).normalize(); const perp = new V3().crossVectors(dir, up); if (perp.lengthSq() < 1e-4) perp.set(1, 0, 0); perp.normalize();
      const bend = l.kind === 0 ? 0.05 : 0.2; C.copy(mid).add(perp.multiplyScalar(len * bend * l.sign * 2)).add(mid.clone().normalize().multiplyScalar(len * 0.1));
      const hi = hn && (l.s === hn || l.t === hn) ? 1 : 0; let a = (l.kind === 0 ? 0.26 : l.kind === 1 ? 0.2 : 0.3) * linkAlphaPair(l) * Math.min(l.s.dim, l.t.dim) ; if (hn) a *= hi ? 3.4 : 0.35; if (hi && l.kind === 0) a *= 1.2;
      for (let s = 0; s < SEG; s++) for (let e = 0; e < 2; e++) { const u = (s + e) / SEG, v = (li * SEG + s) * 2 + e, v3 = v * 3, w0 = (1 - u) * (1 - u), w1 = 2 * (1 - u) * u, w2 = u * u;
        lPos[v3] = w0 * P0.x + w1 * C.x + w2 * P1.x; lPos[v3 + 1] = w0 * P0.y + w1 * C.y + w2 * P1.y; lPos[v3 + 2] = w0 * P0.z + w1 * C.z + w2 * P1.z; lAl[v] = a; lHi[v] = hi; }
    });
    lg.attributes.position.needsUpdate = true; lbAl.needsUpdate = true; lbHi.needsUpdate = true;
    // подписи: показываем нужные и разводим наложения (приоритет: наведённый, выбранный, ниже по уровню)
    const items = [];
    G.nodes.forEach((n) => { const e = n.el; if (!n.sp || n.alpha < 0.2) { e.style.opacity = 0; return; } const near = n.sp.dist < 520;
      const inSub = focus.tier > 0 && (n === focus || anc(n).includes(focus)); const show = n.tier <= 1 || (n.tier === 2 && n.dim > 0.5) || inSub || n === hover || n === selected || (near && n.vis > 0.6 && n.dim > 0.5);
      if (!show) { e.style.opacity = 0; return; } const off = 14 + n.size * 1.6 * (uni.uScale.value / n.sp.dist) * 0.5;
      const fr = n.freshAt && NOW - n.freshAt < FRESH_S; n.sm.textContent = fr ? "● " + ago(n.freshAt) : ""; e.classList.toggle("fresh", !!fr);
      if (!n.lw) { n.lw = e.offsetWidth || 90; n.lh = e.offsetHeight || 16; } items.push({ n, x: n.sp.x, y: n.sp.y + off, w: n.lw, h: n.lh, pri: (n === hover ? -2 : n === selected ? -1 : 0) * 10 + n.tier }); });
    items.sort((a, b) => a.pri - b.pri); const placed = [];
    items.forEach((it) => { let y = it.y, tries = 0; const hit = (yy) => placed.some((p) => Math.abs(p.x - it.x) < (p.w + it.w) / 2 + 4 && Math.abs(p.y - yy) < (p.h + it.h) / 2 + 1);
      while (hit(y) && tries < 4) { y += it.h + 2; tries++; } const ok = !hit(y) || it.pri < 0; const e = it.n.el; e.style.opacity = ok ? Math.min(1, it.n.alpha * 1.1) * (it.n === hover ? 1 : 0.92) : 0;
      if (ok) { placed.push({ x: it.x, y, w: it.w, h: it.h }); e.style.transform = `translate(-50%,0) translate(${it.x}px,${y}px)`; e.style.left = 0; e.style.top = 0; } });
    // карточка
    if (hover && t - hoverSince > 0.16 && !drag) { showCard(hover); } else if (!hover || drag) { if (hcShown) hideCard(); }
    if (hcShown && hover && hover.sp) { hcShown.sp = hover.sp; }
    renderer.render(scene, camera); requestAnimationFrame(frame);
  }
  // старт: показать столпы и общий вид
  setFocus(root, true); cam.dist = 980; crumbs(); requestAnimationFrame(frame);
  window.__graph = { G, N, cam, expand, collapse, goTo, setFocus, get hover() { return hover; }, get selected() { return selected; }, links };
})();
