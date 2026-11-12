(function (root) {
  'use strict';
  const columns = ['titulo', 'autores', 'anio', 'abstract', 'enlace', 'materias', 'universidad', 'nivel_madurez'];
  function parseCSV(text) {
    const rows = []; let row = [], field = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      if (char === '"') {
        if (quoted && text[i + 1] === '"') { field += '"'; i++; }
        else if (quoted) quoted = false;
        else if (!field) quoted = true;
        else throw new Error('Comillas invalidas en el CSV.');
      } else if (char === ',' && !quoted) { row.push(field); field = ''; }
      else if ((char === '\n' || char === '\r') && !quoted) {
        if (char === '\r' && text[i + 1] === '\n') i++;
        row.push(field); rows.push(row); row = []; field = '';
      } else field += char;
    }
    if (quoted) throw new Error('CSV incompleto.');
    if (field || row.length) { row.push(field); rows.push(row); }
    const header = rows.shift();
    if (!header || header.map((v, i) => i ? v : v.replace(/^\uFEFF/, '')).join(',') !== columns.join(',')) throw new Error('Columnas del CSV inesperadas.');
    return rows.filter(r => r.length !== 1 || r[0] !== '').map(r => {
      if (r.length !== columns.length || !/^\d{4}$/.test(r[2])) throw new Error('Registro del CSV invalido.');
      const record = Object.fromEntries(columns.map((name, i) => [name, r[i]]));
      record.anio = Number(record.anio);
      if (!['Teorico', 'Prototipo / Piloto', 'En Produccion'].includes(record.nivel_madurez)) throw new Error('Nivel de madurez inesperado.');
      return record;
    });
  }
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  function publicationDate(record) {
    const year = Number(record.anio) || null;
    const match = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(record.fecha_publicacion || '');
    const empty = {year, month: null, day: null};
    if (!match || Number(match[1]) !== year) return empty;
    const precision = record.precision_fecha || (match[3] ? 'dia' : match[2] ? 'mes' : 'anio');
    if (!['mes', 'dia'].includes(precision) || !match[2]) return empty;
    const month = Number(match[2]), day = match[3] ? Number(match[3]) : null;
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (month < 1 || month > 12 || (day !== null && (day < 1 || day > days[month - 1])) || (precision === 'dia' && day === null)) return empty;
    return {year, month, day: precision === 'dia' ? day : null};
  }
  function filterRecords(records, year, level, search, university = '', month = '', day = '') {
    const term = normalize(search.trim());
    return records.filter(r => {
      if (year && (year === 'desconocido' ? r.anio !== null : r.anio !== Number(year))) return false;
      if (month || day) {
        const date = publicationDate(r);
        if ((month && date.month !== Number(month)) || (day && date.day !== Number(day))) return false;
      }
      return (!level || (r.madurez_id || r.nivel_madurez) === level) && (!university || r.universidad === university) && (!term || normalize([r.titulo, r.autores, r.materias, r.abstract].join(' ')).includes(term));
    });
  }
  function countBy(records, key) {
    const counts = new Map();
    for (const record of records) {
      const label = record[key] ?? 'Sin dato';
      counts.set(label, (counts.get(label) || 0) + 1);
    }
    return [...counts].map(([label, count]) => ({label, count})).sort((a,b) => b.count - a.count || String(a.label).localeCompare(String(b.label), 'es'));
  }
  function timeSeries(records, unit = 'anio') {
    if (!['anio', 'mes', 'dia'].includes(unit)) throw new Error('Periodo de tiempo invalido.');
    const counts = new Map();
    let omitted = 0;
    const pad = value => String(value).padStart(2, '0');
    for (const record of records) {
      const date = publicationDate(record);
      if (!date.year || (unit !== 'anio' && !date.month) || (unit === 'dia' && !date.day)) { omitted++; continue; }
      const key = String(date.year) + (unit !== 'anio' ? '-' + pad(date.month) : '') + (unit === 'dia' ? '-' + pad(date.day) : '');
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return {rows: [...counts].sort((a,b) => a[0].localeCompare(b[0])).map(([label,count]) => ({label,count})), omitted};
  }
  function subjectRanking(records) {
    const counts = new Map();
    for (const record of records) {
      const seen = new Set();
      for (const value of record.materias_lista || String(record.materias || '').split(';')) {
        const label = value.trim(), key = label.toLocaleLowerCase('es');
        if (!key || /purl\.org\/pe-repo\/ocde\/ford#/i.test(label) || seen.has(key)) continue;
        seen.add(key);
        if (!counts.has(key)) counts.set(key, {label, count: 0});
        counts.get(key).count++;
      }
    }
    return [...counts.values()].sort((a,b) => b.count - a.count || a.label.localeCompare(b.label, 'es'));
  }
  function stats(records) {
    const production = records.filter(r => r.madurez_id === 'produccion' || r.nivel_madurez === 'En Produccion').length;
    const applied = records.filter(r => ['piloto', 'produccion'].includes(r.madurez_id) || ['Prototipo / Piloto', 'En Produccion'].includes(r.nivel_madurez)).length;
    return {total: records.length, applied, production, rate: records.length ? applied / records.length * 100 : 0};
  }
  function safeLink(value) {
    try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; }
    catch { return null; }
  }
  function fromStar(model) {
    if (!model || model.schema_version !== 1) throw new Error('Version de datos no compatible.');
    const index = (name, key) => {
      if (!Array.isArray(model[name])) throw new Error('Falta tabla: ' + name);
      const result = new Map();
      for (const row of model[name]) {
        if (!row || row[key] === undefined || result.has(row[key])) throw new Error('Clave invalida: ' + name);
        result.set(row[key], row);
      }
      return result;
    };
    const universities = index('universidades', 'universidad_id'), years = index('anios', 'anio_id');
    const levels = index('madurez', 'madurez_id'), catalog = index('registros', 'registro_id');
    const facts = index('hechos', 'registro_id'), authors = index('autores', 'autor_id'), subjects = index('materias', 'materia_id');
    if (facts.size !== catalog.size) throw new Error('Catalogo y hechos no coinciden.');
    const join = (table, dimension, key, ordered) => {
      if (!Array.isArray(model[table])) throw new Error('Falta puente: ' + table);
      const result = new Map(), pairs = new Set();
      const rows = ordered ? [...model[table]].sort((a,b) => a.orden - b.orden) : model[table];
      for (const row of rows) {
        const pair = row.registro_id + ':' + row[key];
        if (!facts.has(row.registro_id) || !dimension.has(row[key]) || pairs.has(pair)) throw new Error('Relacion invalida: ' + table);
        if (typeof dimension.get(row[key]).nombre !== 'string') throw new Error('Nombre invalido: ' + table);
        pairs.add(pair);
        if (!result.has(row.registro_id)) result.set(row.registro_id, []);
        result.get(row.registro_id).push(dimension.get(row[key]).nombre);
      }
      return result;
    };
    const authorNames = join('registro_autor', authors, 'autor_id', true);
    const subjectNames = join('registro_materia', subjects, 'materia_id', false);
    return [...facts.values()].map(fact => {
      const r = catalog.get(fact.registro_id), u = universities.get(fact.universidad_id), m = levels.get(fact.madurez_id);
      if (!r || !u || !m || !years.has(fact.anio_id) || typeof r.titulo !== 'string' || typeof r.abstract !== 'string' || fact.menciona_tacna !== true) throw new Error('Registro o dimension invalida.');
      return {...r, anio: fact.anio_id || null, universidad: u.sigla, madurez_id: fact.madurez_id,
        nivel_madurez: m.nombre, autores: (authorNames.get(r.registro_id) || []).join('; '),
        materias_lista: subjectNames.get(r.registro_id) || [], materias: (subjectNames.get(r.registro_id) || []).join('; ')};
    });
  }
  const api = {parseCSV, fromStar, filterRecords, stats, safeLink, publicationDate, countBy, timeSeries, subjectRanking};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TacnaData = api;
})(globalThis);
