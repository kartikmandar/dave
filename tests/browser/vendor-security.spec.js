const {test,expect}=require('@playwright/test');
const path=require('node:path');
const fs=require('node:fs/promises');
const scripts=path.resolve(__dirname,'../../src/main/resources/static/scripts/external');

test('Async mapValues rejects prototype pollution while retaining waterfall behavior',async({page})=>{
  await page.addScriptTag({path:path.join(scripts,'async-2.6.4.min.js')});
  const result=await page.evaluate(async()=>{
    const polluted=await new Promise((resolve,reject)=>async.mapValues(JSON.parse('{"__proto__":{"polluted":true},"safe":1}'),(value,key,callback)=>callback(null,value),(err,value)=>err?reject(err):resolve(value)));
    const value=await new Promise((resolve,reject)=>async.waterfall([cb=>cb(null,7),(value,cb)=>cb(null,value*3)],(err,value)=>err?reject(err):resolve(value)));
    return {value,prototypeClean:!Object.getPrototypeOf(polluted).polluted,globalClean:({}).polluted===undefined};
  });
  expect(result).toEqual({value:21,prototypeClean:true,globalClean:true});
});

test('MathJax keeps TeX SVG rendering local and filters javascript links',async({page})=>{
  const requested=[],missing=[];
  await page.route('http://dave.test/**',async route=>{
    const url=new URL(route.request().url());requested.push(url.pathname);
    const file=path.resolve(scripts,'.'+decodeURIComponent(url.pathname));
    if(!file.startsWith(scripts+path.sep))return route.abort();
    try {await route.fulfill({body:await fs.readFile(file),contentType:file.endsWith('.js')?'text/javascript':'text/plain'});}catch(_){if(url.pathname!=='/empty')missing.push(url.pathname);await route.fulfill({status:404,body:'missing'});}
  });
  await page.goto('http://dave.test/empty');
  await page.evaluate(()=>{document.body.innerHTML='<div id="equation">\\(x^2 + \\alpha\\)</div><div id="unsafe">\\(\\href{javascript:alert(1)}{x}\\)</div>';});
  await page.addScriptTag({path:path.join(scripts,'../mathJaxConfig.js')});
  await page.addScriptTag({url:'http://dave.test/MathJax/MathJax.js?config=TeX-AMS-MML_SVG'});
  await page.evaluate(()=>new Promise(resolve=>MathJax.Hub.Queue(['Typeset',MathJax.Hub],resolve)));
  expect(await page.evaluate(()=>MathJax.version)).toBe('2.7.9');
  await expect(page.locator('#equation svg')).toHaveCount(1);
  expect(await page.locator('#unsafe').evaluate(el=>[...el.querySelectorAll('[href]')].some(a=>(a.getAttribute('href')||'').startsWith('javascript:')))).toBe(false);
  expect(requested.every(name=>name==='/empty'||name.startsWith('/MathJax/'))).toBe(true);
  expect(missing).toEqual([]);
});

test('single-image PDF has correct cross references, portrait bounds and no active content',async({page})=>{
  await page.addScriptTag({path:path.join(scripts,'../imagePDF.js')});
  const result=await page.evaluate(async()=>{
    const canvas=document.createElement('canvas');canvas.width=40;canvas.height=900;
    canvas.getContext('2d').fillRect(0,0,40,900);
    const pdf=await DAVEImagePDF.create(canvas.toDataURL('image/jpeg'));
    let invalidRejected=false;try{await DAVEImagePDF.create('data:text/html;base64,PHNjcmlwdD4=');}catch(_){invalidRejected=true;}
    return {bytes:[...new Uint8Array(await pdf.arrayBuffer())],invalidRejected};
  });
  expect(result.invalidRejected).toBe(true);
  const bytes=Buffer.from(result.bytes),text=bytes.toString('latin1');
  const offset=Number(/startxref\n(\d+)\n%%EOF/.exec(text)[1]);
  expect(text.slice(offset,offset+4)).toBe('xref');
  const entries=text.slice(offset).split('\n');
  for(let id=1;id<=5;id++){
    const position=Number(entries[id+2].slice(0,10));
    expect(bytes.toString('ascii',position,position+7)).toBe(id+' 0 obj');
  }
  expect(text).toContain('/MediaBox [0 0 595.28 841.89]');
  expect(text).not.toMatch(/\/(JavaScript|OpenAction|Encrypt|URI)\b/);
  const matrix=/q\n([\d.]+) 0 0 ([\d.]+) ([\d.]+) ([\d.]+) cm/.exec(text);
  const [width,height,left,bottom]=matrix.slice(1).map(Number);
  expect(left).toBeCloseTo(28.3465,3);expect(bottom).toBeCloseTo(28.3465,3);
  expect(left+width).toBeLessThan(595.28);expect(bottom+height).toBeLessThan(841.89);
});
