const assert = require('node:assert/strict');
const fs = require('node:fs');
const data = require('../docs/core.js');
const header = 'titulo,autores,anio,abstract,enlace,materias,universidad,nivel_madurez';
const sample = `${header}\r\n"Tacna, estudio","Autor ""A""",2020,"Linea 1\nLinea 2",https://example.test,Tacna,UNJBG,Teorico\r\n`;
const rows = data.parseCSV(sample);
assert.equal(rows[0].titulo, 'Tacna, estudio');
assert.equal(rows[0].autores, 'Autor "A"');
assert.equal(rows[0].abstract, 'Linea 1\nLinea 2');
assert.throws(() => data.parseCSV(header + '\n"incompleto'));
assert.throws(() => data.parseCSV('columna\nvalor'));
assert.equal(data.safeLink('javascript:alert(1)'), null);
assert.equal(data.safeLink('https://example.test/'), 'https://example.test/');
assert.deepEqual(data.stats([]), {total: 0, applied: 0, production: 0, rate: 0});
assert.equal(data.filterRecords(rows, '2020', 'Teorico', 'línea').length, 1);
assert.equal(data.filterRecords(rows, '2021', '', '').length, 0);
assert.deepEqual(data.stats([...rows, {...rows[0], nivel_madurez: 'Prototipo / Piloto'}, {...rows[0], nivel_madurez: 'En Produccion'}]), {total: 3, applied: 2, production: 1, rate: 2 / 3 * 100});
const records = data.parseCSV(fs.readFileSync('data/investigaciones_tacna.csv', 'utf8'));
assert.ok(records.length > 0);
assert.ok(records.every(r => /\btacna\b/i.test([r.titulo, r.abstract, r.materias].join(' '))));
console.log('OK: parser CSV real, filtros, indicadores, resultados vacíos y enlaces seguros.');

const model = JSON.parse(fs.readFileSync('data/modelo_web.json', 'utf8'));
const hydrated = data.fromStar(model);
assert.equal(hydrated.length, model.hechos.length);
assert.equal(new Set(hydrated.map(r => r.registro_id)).size, hydrated.length);
assert.ok(data.filterRecords(hydrated, '', '', '', 'UPT').length > 0);
assert.ok(data.filterRecords(hydrated, '', '', '', 'UNJBG').length > 0);
assert.equal(data.stats([{madurez_id:'sin_resumen'}, {madurez_id:'sin_evidencia'}]).applied, 0);
const bad = {...model, hechos: model.hechos.map((r,i) => i ? r : {...r, universidad_id:'inexistente'})};
assert.throws(() => data.fromStar(bad));
assert.throws(() => data.fromStar({...model, registro_autor:[...model.registro_autor, model.registro_autor[0]]}));
assert.throws(() => data.fromStar({...model, materias:model.materias.map((r,i)=>i?r:{...r,nombre:42})}));
console.log('OK: estrella, puentes, grano, universidad, nulos y referencias invalidas.');

const dated = [
  {registro_id:'a',anio:2024,fecha_publicacion:'2024',precision_fecha:'anio',universidad:'UNJBG',madurez_id:'sin_evidencia',materias_lista:['Tacna','TACNA','Agua','http://purl.org/pe-repo/ocde/ford#2.01.01']},
  {registro_id:'b',anio:2024,fecha_publicacion:'2024-02',precision_fecha:'mes',universidad:'UPT',madurez_id:'piloto',materias_lista:['Tacna','Suelo']},
  {registro_id:'c',anio:2024,fecha_publicacion:'2024-02-29',precision_fecha:'dia',universidad:'UPT',madurez_id:'produccion',materias_lista:['Agua']},
  {registro_id:'d',anio:2024,fecha_publicacion:'2024-03-01',precision_fecha:'dia',universidad:'UPT',madurez_id:'sin_evidencia',materias_lista:[]},
  {registro_id:'e',anio:2023,fecha_publicacion:'2023-02-28',precision_fecha:'dia',universidad:'UPT',madurez_id:'piloto',materias_lista:['Suelo']},
  {registro_id:'f',anio:null,fecha_publicacion:'',precision_fecha:'desconocida',universidad:'UPT',madurez_id:'sin_resumen',materias_lista:[]}
].map(r=>({...r,titulo:'Estudio',abstract:'Resumen',autores:'',materias:''}));
assert.deepEqual(data.publicationDate(dated[0]),{year:2024,month:null,day:null});
assert.deepEqual(data.publicationDate(dated[1]),{year:2024,month:2,day:null});
assert.deepEqual(data.publicationDate(dated[2]),{year:2024,month:2,day:29});
assert.equal(data.publicationDate({...dated[2],fecha_publicacion:'2024-02-30'}).day,null);
assert.equal(data.publicationDate({...dated[2],anio:2023,fecha_publicacion:'2023-02-29'}).month,null);
assert.equal(data.publicationDate({...dated[2],fecha_publicacion:'2024-13-01'}).month,null);
assert.equal(data.publicationDate({...dated[2],precision_fecha:'anio'}).month,null);
assert.equal(data.publicationDate({...dated[2],fecha_publicacion:'2023-02-28'}).day,null);
assert.equal(data.filterRecords(dated,'2024','','').length,4);
assert.deepEqual(data.filterRecords(dated,'2024','','','','2').map(r=>r.registro_id),['b','c']);
assert.deepEqual(data.filterRecords(dated,'2024','','','','2','29').map(r=>r.registro_id),['c']);
assert.equal(data.filterRecords(dated,'2024','','','UNJBG','2').length,0);
assert.equal(data.filterRecords(dated,'desconocido','','').length,1);
assert.deepEqual(data.timeSeries(dated,'anio'),{rows:[{label:'2023',count:1},{label:'2024',count:4}],omitted:1});
assert.deepEqual(data.timeSeries(dated,'mes'),{rows:[{label:'2023-02',count:1},{label:'2024-02',count:2},{label:'2024-03',count:1}],omitted:2});
assert.equal(data.timeSeries(dated,'dia').omitted,3);
assert.throws(()=>data.timeSeries(dated,'hora'));
assert.deepEqual(data.timeSeries([]),{rows:[],omitted:0});
assert.deepEqual(data.subjectRanking(dated),[{label:'Agua',count:2},{label:'Suelo',count:2},{label:'Tacna',count:2}]);
assert.equal(data.countBy(dated,'universidad').reduce((n,r)=>n+r.count,0),dated.length);
assert.equal(data.countBy(dated,'madurez_id').reduce((n,r)=>n+r.count,0),dated.length);
for (const unit of ['anio','mes','dia']) {
  const series=data.timeSeries(hydrated,unit);
  assert.equal(series.rows.reduce((n,r)=>n+r.count,0)+series.omitted,hydrated.length);
}
assert.ok(data.subjectRanking(hydrated).every(r=>r.count<=hydrated.length));
assert.ok(data.filterRecords(hydrated,'','','','UNJBG').every(r=>data.publicationDate(r).month===null));
assert.ok(data.filterRecords(hydrated,'2026','','','UPT','5').every(r=>r.fecha_publicacion.startsWith('2026-05')));
console.log('OK: filtros de año/mes/día, fechas parciales y bisiestas, series y conteos sin duplicados.');
