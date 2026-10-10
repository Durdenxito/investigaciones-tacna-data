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
  function filterRecords(records, year, level, search) {
    const term = normalize(search.trim());
    return records.filter(r => (!year || r.anio === Number(year)) && (!level || r.nivel_madurez === level) && (!term || normalize([r.titulo, r.autores, r.materias, r.abstract].join(' ')).includes(term)));
  }
  function stats(records) {
    const production = records.filter(r => r.nivel_madurez === 'En Produccion').length;
    const applied = records.filter(r => r.nivel_madurez !== 'Teorico').length;
    return {total: records.length, applied, production, rate: records.length ? applied / records.length * 100 : 0};
  }
  function safeLink(value) {
    try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; }
    catch { return null; }
  }
  const api = {parseCSV, filterRecords, stats, safeLink};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TacnaData = api;
})(globalThis);
