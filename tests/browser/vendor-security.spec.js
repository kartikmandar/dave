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
