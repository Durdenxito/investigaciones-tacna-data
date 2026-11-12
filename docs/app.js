'use strict';
const PUBLIC_MODEL = 'https://raw.githubusercontent.com/Durdenxito/investigaciones-tacna-data/main/data/modelo_web.json';
const LOCAL_MODEL = '/data/modelo_web.json';
const localPreview = ['localhost', '127.0.0.1'].includes(location.hostname);
const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat('es-PE');
const labels = {sin_evidencia: 'Sin evidencia textual detectada', piloto: 'Indicios de prototipo / piloto', produccion: 'Indicios de producción', sin_resumen: 'Resumen no disponible'};
const colors = {sin_evidencia: 'var(--gray)', piloto: 'var(--blue)', produccion: 'var(--green)', sin_resumen: 'var(--gray)'};
const reports = ['panorama', 'tiempo', 'universidades', 'madurez', 'temas', 'explorar'];
const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
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
  for (const section of reports) {
    $(section).hidden = !loaded || section !== name;
    $('nav-' + section).setAttribute('aria-pressed', String(section === name));
  }
  if (!loaded) return;
  switch (name) {
    case 'panorama': renderCharts(); break;
    case 'tiempo': renderTime(); break;
    case 'universidades': renderUniversities(); break;
    case 'madurez': renderMaturity(); break;
    case 'temas': renderSubjects(); break;
    case 'explorar': renderTable(); break;
  }
}

function drawTimeline(id, rows) {
  const target = $(id), visible = rows.slice(-60);
  target.replaceChildren();
  if (!visible.length) target.append(element('p', 'No hay fechas con este detalle para los filtros seleccionados.'));
  const max = Math.max(1, ...visible.map(r => r.count));
  for (const row of visible) {
    const item = element('div', undefined, 'year-item');
    item.setAttribute('role', 'listitem');
    item.setAttribute('aria-label', `${row.label}: ${number.format(row.count)} investigaciones`);
    const bar = element('div', undefined, 'year-bar');
    bar.style.height = `${row.count / max * 82}%`;
    bar.append(element('span', number.format(row.count)));
    item.append(bar, element('span', row.label, 'year-label'));
    target.append(item);
  }
}

function drawBars(id, rows) {
  const target = $(id);
  target.replaceChildren();
  if (!rows.length) target.append(element('p', 'No hay resultados para estos filtros.'));
  const largest = Math.max(1, ...rows.map(r => r.count));
  for (const row of rows) {
    const item = element('div'); item.setAttribute('role', 'listitem');
    const label = element('div', undefined, 'level-label');
    label.append(element('span', row.label), element('strong', number.format(row.count)));
    const track = element('div', undefined, 'level-track'); track.setAttribute('aria-hidden', 'true');
    const fill = element('div', undefined, 'level-fill');
    fill.style.width = `${row.count / largest * 100}%`;
    fill.style.background = row.color || 'var(--accent)';
    if (!row.count) fill.style.display = 'none';
    track.append(fill); item.append(label, track); target.append(item);
  }
}

function drawTable(id, rows) {
  const target = $(id);
  target.replaceChildren();
  for (const values of rows) {
    const row = element('tr');
    for (const value of values) row.append(element('td', String(value)));
    target.append(row);
  }
  if (!rows.length) {
    const row = element('tr'), cell = element('td', 'No hay resultados para estos filtros.');
    cell.colSpan = target.closest('table').querySelectorAll('th').length;
    row.append(cell); target.append(row);
  }
}

function maturityRows() {
  return Object.entries(labels).map(([id, label]) => ({label, count: selected.filter(r => r.madurez_id === id).length, color: colors[id]}));
}

function percentage(count) {
  return (selected.length ? count / selected.length * 100 : 0).toLocaleString('es-PE', {maximumFractionDigits: 2}) + ' %';
}

function renderCharts() {
  drawTimeline('years-chart', TacnaData.timeSeries(selected).rows);
  drawBars('levels-chart', maturityRows());
}

function renderTime() {
  const series = TacnaData.timeSeries(selected, $('time-unit').value);
  drawTimeline('time-chart', series.rows);
  drawTable('time-table', series.rows.map(r => [r.label, number.format(r.count)]));
  const range = series.rows.length > 60 ? `El gráfico muestra los últimos 60 de ${series.rows.length} periodos; la tabla contiene todos.` : `Se muestran ${series.rows.length} periodos con publicaciones.`;
  $('time-note').textContent = `${number.format(selected.length - series.omitted)} registros con fecha suficiente; ${number.format(series.omitted)} sin el detalle necesario. ${range}`;
}

function renderUniversities() {
  const rows = TacnaData.countBy(selected, 'universidad');
  drawBars('university-chart', rows);
  drawTable('university-table', rows.map(row => {
    const values = selected.filter(r => r.universidad === row.label);
    return [row.label, number.format(row.count), percentage(row.count), number.format(TacnaData.stats(values).applied), number.format(values.filter(r => TacnaData.publicationDate(r).day !== null).length)];
  }));
}

function renderMaturity() {
  const rows = maturityRows();
  drawBars('maturity-chart', rows);
  drawTable('maturity-table', rows.map(r => [r.label, number.format(r.count), percentage(r.count)]));
}

function renderSubjects() {
  const rows = TacnaData.subjectRanking(selected);
  drawBars('subject-chart', rows.slice(0, 10));
  drawTable('subject-table', rows.slice(0, 20).map(r => [r.label, number.format(r.count), percentage(r.count)]));
  $('subject-note').textContent = `${number.format(rows.length)} temas distintos en ${number.format(selected.length)} investigaciones. El gráfico muestra hasta 10 y la tabla hasta 20.`;
}

function formatDate(record) {
  const date = TacnaData.publicationDate(record);
  if (!date.year) return 'Fecha desconocida';
  if (!date.month) return `${date.year} (solo año)`;
  if (!date.day) return `${months[date.month - 1]} de ${date.year} (sin día)`;
  return `${String(date.day).padStart(2, '0')}/${String(date.month).padStart(2, '0')}/${date.year}`;
}

function renderTable() {
  $('results').textContent = number.format(selected.length); $('rows').replaceChildren();
  selected.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).forEach(r => {
    const row = element('tr'), titleCell = element('td');
    titleCell.append(element('p', r.titulo || 'Sin título', 'study-title'), element('p', r.universidad + ' · ' + (r.autores || 'Autor no informado'), 'authors'));
    if (r.abstract) {
      const details = element('details'); details.append(element('summary', 'Leer resumen'), element('p', r.abstract)); titleCell.append(details);
    }
    if (r.evidencia) { const proof = element('details'); proof.append(element('summary', 'Ver señal textual'), element('p', r.evidencia)); titleCell.append(proof); }
    const levelCell = element('td'); levelCell.append(element('span', labels[r.madurez_id], 'badge' + (r.madurez_id === 'produccion' ? ' production' : r.madurez_id === 'piloto' ? ' pilot' : '')));
    const linkCell = element('td'), url = TacnaData.safeLink(r.enlace);
    if (url) { const link = element('a', 'Abrir estudio ↗'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.setAttribute('aria-label', 'Abrir estudio: ' + r.titulo); linkCell.append(link); }
    else linkCell.textContent = 'No disponible';
    row.append(titleCell, element('td', formatDate(r)), element('td', r.materias || 'Sin materias'), levelCell, linkCell); $('rows').append(row);
  });
  if (!selected.length) { const cell = element('td', 'No hay resultados. Prueba otro periodo, nivel o término de búsqueda.'); cell.colSpan = 5; const row = element('tr'); row.append(cell); $('rows').append(row); }
  $('page-info').textContent = selected.length ? `${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, selected.length)} de ${number.format(selected.length)} investigaciones` : '0 investigaciones';
  $('previous').disabled = page === 0; $('next').disabled = (page + 1) * PAGE_SIZE >= selected.length;
}

function syncDateFilters() {
  const month = $('month').value, day = $('day').value;
  const dates = records.filter(r => r.anio === Number($('year').value)).map(TacnaData.publicationDate);
  const availableMonths = [...new Set(dates.map(r => r.month).filter(Boolean))].sort((a,b) => a - b);
  $('month').replaceChildren(new Option('Todos los meses', ''));
  availableMonths.forEach(m => $('month').add(new Option(months[m - 1], m)));
  $('month').disabled = !availableMonths.length;
  if (availableMonths.includes(Number(month))) $('month').value = month;
  const availableDays = [...new Set(dates.filter(r => r.month === Number($('month').value)).map(r => r.day).filter(Boolean))].sort((a,b) => a - b);
  $('day').replaceChildren(new Option('Todos los días', ''));
  availableDays.forEach(d => $('day').add(new Option(d, d)));
  $('day').disabled = !availableDays.length;
  if (availableDays.includes(Number(day))) $('day').value = day;
}

function render() {
  const base = TacnaData.filterRecords(records, $('year').value, $('level').value, $('search').value, $('university').value);
  selected = TacnaData.filterRecords(base, '', '', '', '', $('month').value, $('day').value).sort((a,b) => b.anio - a.anio || String(b.fecha_publicacion).localeCompare(String(a.fecha_publicacion)) || a.titulo.localeCompare(b.titulo, 'es'));
  const stats = TacnaData.stats(selected);
  ['total', 'applied', 'production'].forEach(key => $(key).textContent = number.format(stats[key]));
  $('rate').textContent = stats.rate.toLocaleString('es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' %';
  $('status').textContent = selected.length === records.length
    ? `${number.format(records.length)} investigaciones`
    : `${number.format(selected.length)} de ${number.format(records.length)} investigaciones`;
  const dates = selected.map(TacnaData.publicationDate), complete = dates.filter(d => d.day !== null).length;
  const monthOnly = dates.filter(d => d.month !== null && d.day === null).length;
  const missing = base.filter(r => { const d = TacnaData.publicationDate(r); return $('day').value ? d.day === null : d.month === null; }).length;
  const detail = $('month').value || $('day').value ? ` En el año y los demás filtros, ${number.format(missing)} registros no tienen el detalle de fecha solicitado.` : ' Selecciona un año para habilitar mes y un mes para habilitar día.';
  $('time-coverage').textContent = `Fechas de la selección: ${number.format(complete)} completas, ${number.format(monthOnly)} con mes sin día y ${number.format(selected.length - complete - monthOnly)} solo con año o sin fecha.${detail}`;
  showView(view);
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
    [...new Set(records.map(r => r.anio).filter(Boolean))].sort((a,b) => b - a).forEach(year => $('year').add(new Option(year, year)));
    if (records.some(r => r.anio === null)) $('year').add(new Option('Sin año conocido', 'desconocido'));
    $('university').replaceChildren(new Option('Todas las universidades', ''));
    [...new Set(records.map(r => r.universidad))].sort((a,b) => a.localeCompare(b, 'es')).forEach(u => $('university').add(new Option(u, u)));
    $('coverage').textContent = model.cobertura.map(c => c.universidad + ': ' + (c.alcance.includes('historica') ? 'selección histórica disponible' : 'catálogo recolectado')).join(' · ');
    syncDateFilters(); render();
  } catch (error) {
    $('status').textContent = 'No pudimos descargar los datos. Comprueba tu conexión e intenta de nuevo. No se muestran cifras sin verificar.';
    $('retry').hidden = false; console.error(error);
  }
}

reports.forEach(name => $('nav-' + name).addEventListener('click', () => showView(name)));
$('time-unit').addEventListener('change', () => { if (loaded) renderTime(); });
$('filters').addEventListener('submit', event => event.preventDefault());
$('filters').addEventListener('input', event => {
  if (!loaded) return;
  if (event.target.id === 'year') { $('month').value = ''; $('day').value = ''; }
  if (event.target.id === 'month') $('day').value = '';
  if (['year', 'month'].includes(event.target.id)) syncDateFilters();
  page = 0; render();
});
$('filters').addEventListener('reset', () => { setTimeout(() => { if (loaded) { page = 0; syncDateFilters(); render(); } }, 0); });
$('previous').addEventListener('click', () => { page--; renderTable(); });
$('next').addEventListener('click', () => { page++; renderTable(); });
$('retry').addEventListener('click', load);
load();
