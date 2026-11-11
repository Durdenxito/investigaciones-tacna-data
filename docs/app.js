'use strict';
const PUBLIC_MODEL = 'https://raw.githubusercontent.com/Durdenxito/investigaciones-tacna-data/main/data/modelo_web.json';
const LOCAL_MODEL = '/data/modelo_web.json';
const localPreview = ['localhost', '127.0.0.1'].includes(location.hostname);
const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat('es-PE');
const labels = {sin_evidencia: 'Sin evidencia textual detectada', piloto: 'Indicios de prototipo / piloto', produccion: 'Indicios de producción', sin_resumen: 'Resumen no disponible'};
const colors = {sin_evidencia: 'var(--gray)', piloto: 'var(--blue)', produccion: 'var(--green)', sin_resumen: 'var(--gray)'};
let records = [], selected = [], page = 0, view = 'panorama', loaded = false;
const PAGE_SIZE = 25;
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function showView(name) {
  view = name;
  for (const section of ['panorama', 'explorar']) {
    $(section).hidden = !loaded || section !== name;
    $('nav-' + section).setAttribute('aria-pressed', String(section === name));
  }
}
function renderCharts() {
  const counts = new Map();
  selected.forEach(r => counts.set(r.anio, (counts.get(r.anio) || 0) + 1));
  const max = Math.max(1, ...counts.values());
  $('years-chart').replaceChildren();
  if (!counts.size) $('years-chart').append(element('p', 'No hay investigaciones para estos filtros.'));
  [...counts].sort((a, b) => a[0] - b[0]).forEach(([year, count]) => {
    const item = element('div', undefined, 'year-item'); item.setAttribute('role', 'listitem');
    item.setAttribute('aria-label', `${year}: ${number.format(count)} investigaciones`);
    const bar = element('div', undefined, 'year-bar'); bar.style.height = `${count / max * 82}%`;
    bar.append(element('span', number.format(count)));
    item.append(bar, element('span', String(year), 'year-label')); $('years-chart').append(item);
  });
  const levels = Object.keys(labels).map(level => [level, selected.filter(r => r.madurez_id === level).length]);
  const largest = Math.max(1, ...levels.map(item => item[1]));
  $('levels-chart').replaceChildren();
  levels.forEach(([level, count]) => {
    const item = element('div'); item.setAttribute('role', 'listitem');
    const label = element('div', undefined, 'level-label'); label.append(element('span', labels[level]), element('strong', number.format(count)));
    const track = element('div', undefined, 'level-track'); track.setAttribute('aria-hidden', 'true');
    const fill = element('div', undefined, 'level-fill'); fill.style.width = `${count / largest * 100}%`; fill.style.background = colors[level];
    if (!count) fill.style.display = 'none';
    track.append(fill); item.append(label, track); $('levels-chart').append(item);
  });
}
function renderTable() {
  $('results').textContent = number.format(selected.length); $('rows').replaceChildren();
  selected.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).forEach(r => {
    const row = element('tr'), titleCell = element('td');
    titleCell.append(element('p', r.titulo || 'Sin título', 'study-title'), element('p', r.universidad + ' ? ' + (r.autores || 'Autor no informado'), 'authors'));
    if (r.abstract) {
      const details = element('details'); details.append(element('summary', 'Leer resumen'), element('p', r.abstract)); titleCell.append(details);
    }
    if (r.evidencia) { const proof = element('details'); proof.append(element('summary', 'Ver se?al textual'), element('p', r.evidencia)); titleCell.append(proof); }
    const levelCell = element('td'); levelCell.append(element('span', labels[r.madurez_id], 'badge' + (r.madurez_id === 'produccion' ? ' production' : r.madurez_id === 'piloto' ? ' pilot' : '')));
    const linkCell = element('td'), url = TacnaData.safeLink(r.enlace);
    if (url) { const link = element('a', 'Abrir estudio ↗'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.setAttribute('aria-label', 'Abrir estudio: ' + r.titulo); linkCell.append(link); }
    else linkCell.textContent = 'No disponible';
    row.append(titleCell, element('td', r.anio || 'Sin a?o'), element('td', r.materias || 'Sin materias'), levelCell, linkCell); $('rows').append(row);
  });
  if (!selected.length) { const cell = element('td', 'No hay resultados. Prueba otro año, nivel o término de búsqueda.'); cell.colSpan = 5; const row = element('tr'); row.append(cell); $('rows').append(row); }
  $('page-info').textContent = selected.length ? `${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, selected.length)} de ${number.format(selected.length)} investigaciones` : '0 investigaciones';
  $('previous').disabled = page === 0; $('next').disabled = (page + 1) * PAGE_SIZE >= selected.length;
}
function render() {
  selected = TacnaData.filterRecords(records, $('year').value, $('level').value, $('search').value, $('university').value).sort((a, b) => b.anio - a.anio || a.titulo.localeCompare(b.titulo, 'es'));
  const stats = TacnaData.stats(selected);
  ['total', 'applied', 'production'].forEach(key => $(key).textContent = number.format(stats[key]));
  $('rate').textContent = stats.rate.toLocaleString('es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' %';
  $('status').textContent = `${number.format(selected.length)} de ${number.format(records.length)} investigaciones · Filtros compartidos entre las dos páginas`;
  renderCharts(); renderTable(); showView(view);
}
async function load() {
  $('retry').hidden = true; $('status').textContent = 'Consultando las investigaciones…';
  try {
    const compressed = typeof DecompressionStream === 'function';
    const modelURL = localPreview ? LOCAL_MODEL : PUBLIC_MODEL;
    const response = await fetch(modelURL + (compressed ? '.gz' : ''), {cache: 'no-store', credentials: 'omit', signal: AbortSignal.timeout(60000)});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const bytes = new Uint8Array(await response.arrayBuffer());
    const json = compressed && bytes[0] === 31 && bytes[1] === 139
      ? await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text()
      : new TextDecoder().decode(bytes);
    const model = JSON.parse(json);
    const data = TacnaData.fromStar(model);
    if (!data.length) throw new Error('El dataset está vacío.');
    records = data; loaded = true;
    $('year').replaceChildren(new Option('Todos los años', ''));
    [...new Set(records.map(r => r.anio).filter(Boolean))].sort((a, b) => b - a).forEach(year => $('year').add(new Option(year, year)));
    if (records.some(r => r.anio === null)) $('year').add(new Option('Sin a?o conocido', 'desconocido'));
    $('university').replaceChildren(new Option('Todas las universidades', ''));
    [...new Set(records.map(r => r.universidad))].sort((a,b) => a.localeCompare(b, 'es')).forEach(u => $('university').add(new Option(u, u)));
    $('coverage').textContent = model.cobertura.map(c => c.universidad + ': ' + (c.alcance.includes('historica') ? 'selección histórica disponible' : 'catálogo recolectado')).join(' · ');
    render();
  } catch (error) {
    $('status').textContent = 'No pudimos descargar los datos. Comprueba tu conexión e intenta de nuevo. No se muestran cifras sin verificar.';
    $('retry').hidden = false; console.error(error);
  }
}
$('nav-panorama').addEventListener('click', () => showView('panorama'));
$('nav-explorar').addEventListener('click', () => showView('explorar'));
$('filters').addEventListener('submit', event => event.preventDefault());
$('filters').addEventListener('input', () => { if (loaded) { page = 0; render(); } });
$('filters').addEventListener('reset', () => { setTimeout(() => { if (loaded) { page = 0; render(); } }, 0); });
$('previous').addEventListener('click', () => { page--; renderTable(); });
$('next').addEventListener('click', () => { page++; renderTable(); });
$('retry').addEventListener('click', load);
load();
