"use strict";
const $ = id => document.getElementById(id);
let doc, revision, selected, dirty = false, busy = false, mapSelected = null;
const message = (text, error = false) => { $("message").textContent = text; $("message").classList.toggle("error", error); };
const changed = () => { dirty = true; $("save").disabled = busy; message("Есть несохранённые изменения"); };
function setBusy(value) {
  busy = value; $("form").inert = value;
  for (const id of ["nodes", "filter", "add", "reload"]) $(id).disabled = value;
  $("save").disabled = value || !dirty;
}
const option = (value, label) => { const el = document.createElement("option"); el.value = value; el.textContent = label; return el; };
const title = id => `${doc.NODES[id].label || id} · ${id}`;

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Не удалось выполнить запрос");
  return body;
}
function list() {
  const query = $("filter").value.toLowerCase();
  $("nodes").replaceChildren(...Object.keys(doc.NODES).filter(id => title(id).toLowerCase().includes(query)).map(id => option(id, title(id))));
  $("nodes").value = selected || "";
}
function selectNode(id, focus = false) {
  if (!doc.NODES[id]) return;
  selected = id; $("form").hidden = false; list();
  const n = doc.NODES[id];
  for (const field of ["label", "human", "status", "tier"]) $(field).value = n[field] ?? ({status:"live",tier:2}[field] ?? "");
  for (const field of ["paths", "tests"]) $(field).value = (n[field] || []).join("\n");
  $("parent").replaceChildren(option("", "Нет — корень проекта"), ...Object.keys(doc.NODES).filter(key => key !== id).map(key => option(key, title(key))));
  $("parent").value = n.parent || "";
  $("delete").disabled = !n.parent;
  renderLinks(); renderGallery();
  if (focus) { const graph = $("map").contentWindow.__graph; if (graph?.N[id]) graph.goTo(graph.N[id]); }
}
function renderLinks() {
  $("links").replaceChildren();
  doc.LINKS.filter(link => link.source === selected).forEach(link => {
    const row = document.createElement("div"); row.className = "link";
    const target = document.createElement("select"); target.setAttribute("aria-label", "Цель связи"); target.append(...Object.keys(doc.NODES).map(id => option(id, title(id)))); target.value = link.target;
    const type = document.createElement("input"); type.value = link.type || "uses"; type.placeholder = "Тип: calls, reads_state, writes…"; type.setAttribute("aria-label", "Тип связи");
    const label = document.createElement("input"); label.value = link.label || ""; label.placeholder = "Описание связи"; label.setAttribute("aria-label", "Описание связи");
    target.onchange = () => { link.target = target.value; changed(); };
    type.oninput = () => { link.type = type.value; changed(); };
    label.oninput = () => { link.label = label.value; changed(); };
    const remove = document.createElement("button"); remove.textContent = "Удалить связь"; remove.onclick = () => { doc.LINKS.splice(doc.LINKS.indexOf(link), 1); renderLinks(); changed(); };
    row.append(target, type, label, remove); $("links").append(row);
  });
  $("incoming").textContent = doc.LINKS.filter(l => l.target === selected).map(l => `${title(l.source)} → ${l.type || "uses"}: ${l.label || ""}`).join("\n") || "Нет явных входящих связей";
  $("incoming").style.whiteSpace = "pre-line";
}
function renderGallery() {
  const node = doc.NODES[selected]; $("gallery").replaceChildren();
  const keys = [...new Set([node.hero, ...(node.arts || []), ...(node.sats || [])].filter(Boolean))];
  keys.forEach(key => {
    const art = (doc.CUSTOM_ARTS || []).find(a => a.key === key); if (!art) return;
    const box = document.createElement("div"); box.className = "image";
    const image = document.createElement("img"); image.src = `art/${encodeURIComponent(key)}.jpg`; image.alt = art.caption || key;
    const caption = document.createElement("input"); caption.value = art.caption || ""; caption.setAttribute("aria-label", "Подпись изображения"); caption.oninput = () => { art.caption = caption.value; changed(); };
    const cover = document.createElement("button"); cover.textContent = node.hero === key ? "★ Обложка" : "Сделать обложкой"; cover.classList.toggle("cover", node.hero === key); cover.onclick = () => { node.hero = key; changed(); renderGallery(); };
    const remove = document.createElement("button"); remove.textContent = "Убрать из узла"; remove.onclick = () => { node.arts = (node.arts || []).filter(k => k !== key); node.sats = (node.sats || []).filter(k => k !== key); if (node.hero === key) node.hero = null; changed(); renderGallery(); };
    box.append(image, caption, cover, remove); $("gallery").append(box);
  });
}
async function load() {
  const data = await api("/api/document"); doc = data.document; revision = data.revision;
  doc.LINKS ||= []; doc.CUSTOM_ARTS ||= [];
  dirty = false; $("save").disabled = true;
  selectNode(doc.NODES[selected] ? selected : Object.keys(doc.NODES)[0]);
  message("Выберите узел. Правки сохраняются в graph_edit.json.");
}
$("filter").oninput = list;
$("nodes").onchange = () => selectNode($("nodes").value, true);
for (const field of ["label", "human", "status", "tier", "parent", "paths", "tests"]) {
  $(field).oninput = () => {
    const value = $(field).value;
    doc.NODES[selected][field] = field === "tier" ? Number(value) : field === "parent" ? value || null : ["paths", "tests"].includes(field) ? value.split("\n").map(s => s.trim()).filter(Boolean) : value;
    changed(); if (field === "label") list();
  };
}
$("add").onclick = () => {
  const id = $("new-id").value.trim();
  if (!/^[a-zA-Z0-9_-]+$/.test(id) || doc.NODES[id]) return message("Нужен уникальный ID: латиница, цифры, _ или -", true);
  const tier = (doc.NODES[selected]?.tier ?? 0) + 1;
  if (tier > 3) return message("Выберите родителя с уровнем 0, 1 или 2", true);
  doc.NODES[id] = {label:id, human:"", tier, parent:selected, status:"idea", paths:[], tests:[]};
  $("new-id").value = ""; $("filter").value = ""; selectNode(id); changed();
};
$("delete").onclick = () => {
  const n = doc.NODES[selected];
  if (!n.parent) return;
  if (Object.values(doc.NODES).some(node => node.parent === selected)) return message("Сначала перенесите или удалите дочерние узлы", true);
  if (!confirm(`Удалить узел «${n.label || selected}» и его связи?`)) return;
  doc.LINKS = doc.LINKS.filter(l => l.source !== selected && l.target !== selected);
  delete doc.NODES[selected]; selectNode(n.parent); changed();
};
$("add-link").onclick = () => {
  const target = Object.keys(doc.NODES).find(id => id !== selected && !doc.LINKS.some(l => l.source === selected && l.target === id));
  if (!target) return message("Нет доступного узла для новой связи", true);
  doc.LINKS.push({source:selected, target, type:"uses", label:""}); renderLinks(); changed();
};
$("reload").onclick = async () => { if (busy || (dirty && !confirm("Отменить несохранённые изменения и загрузить граф с диска?"))) return; try { await load(); $("map").contentWindow.location.reload(); } catch (e) { message(e.message, true); } };
$("save").onclick = async () => {
  if (busy) return; setBusy(true); message("Сохранение и сборка…");
  try {
    const data = await api("/api/document", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({document:doc, revision})});
    revision = data.revision; dirty = false; mapSelected = null; $("map").contentWindow.location.reload(); message("Сохранено. Карта и индекс агента обновлены.");
  } catch (e) { message(e.message, true); }
  finally { setBusy(false); }
};
$("map").addEventListener("load", () => {
  // The editor sidebar replaces the viewer's read-only drawer in this mode.
  const drawer = $("map").contentDocument?.getElementById("drawer");
  if (drawer) drawer.style.display = "none";
  const style = $("map").contentDocument.createElement("style");
  style.textContent = "@media(max-width:900px){#crumbs{display:none}#brand{max-width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}#search{width:120px}#fFresh{white-space:nowrap}#top{gap:8px;padding:10px}}";
  $("map").contentDocument.head.append(style);
  const graph = $("map").contentWindow.__graph;
  if (selected && graph?.N[selected]) { graph.goTo(graph.N[selected]); mapSelected = selected; }
});
setInterval(() => {
  const id = $("map").contentWindow.__graph?.selected?.id;
  if (!busy && doc && id && id !== mapSelected) { mapSelected = id; selectNode(id); }
}, 200);
window.addEventListener("beforeunload", e => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

async function thumbnail(file) {
  if (!file.type.startsWith("image/")) throw new Error("Выберите изображение");
  const bitmap = await createImageBitmap(file);
  try {
    const scale = Math.min(1, 720 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas"); canvas.width = Math.max(1, Math.round(bitmap.width * scale)); canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext("2d"); ctx.fillStyle = "#080d1c"; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return await new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("Не удалось подготовить изображение")), "image/jpeg", .86));
  } finally { bitmap.close(); }
}
async function upload(files) {
  if (!doc || !selected || busy) return;
  const nodeId = selected; setBusy(true);
  try {
    for (const file of files) {
      message(`Загружаю ${file.name}…`);
      const blob = await thumbnail(file);
      const art = await api("/api/image", {method:"POST", headers:{"Content-Type":"image/jpeg"}, body:blob});
      if (!doc.CUSTOM_ARTS.some(a => a.key === art.key)) doc.CUSTOM_ARTS.push({key:art.key, path:art.path, caption:file.name.replace(/\.[^.]+$/, "")});
      const node = doc.NODES[nodeId]; node.arts = [...new Set([...(node.arts || []), art.key])]; node.hero ||= art.key;
      dirty = true;
    }
    if (selected === nodeId) renderGallery(); message("Изображения добавлены. Сохраните граф.");
  } catch (e) { message(e.message, true); }
  finally { setBusy(false); $("files").value = ""; }
}
$("drop").onclick = () => $("files").click();
$("drop").onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("files").click(); } };
$("files").onchange = () => upload([...$("files").files]);
for (const event of ["dragenter", "dragover"]) $("drop").addEventListener(event, e => { e.preventDefault(); $("drop").classList.add("over"); });
$("drop").ondragleave = () => $("drop").classList.remove("over");
$("drop").ondrop = e => { e.preventDefault(); $("drop").classList.remove("over"); upload([...e.dataTransfer.files]); };
window.addEventListener("dragover", e => e.preventDefault());
window.addEventListener("drop", e => e.preventDefault());
load().catch(e => message(e.message + ". Запустите python -X utf8 edit_graph.py", true));
