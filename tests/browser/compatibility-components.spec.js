const { test, expect } = require('@playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');
const scripts = path.resolve(__dirname, '../../src/main/resources/static/scripts');

test.beforeEach(async ({ page }) => {
  await page.setContent('<!doctype html><html><body><canvas width="3" height="2"></canvas></body></html>');
  await page.addScriptTag({ path: path.join(scripts, 'logPanel.js') });
  await page.addScriptTag({ path: path.join(scripts, 'canvasExport.js') });
});

test('log panel retains text, levels, row limits and visibility controls without jQuery', async ({ page }) => {
  await page.evaluate(() => {
    Logger.show(); Logger.clear(); Logger.setMaxRows(3);
    log('<img src=x onerror="window.injected=true">', 'LogServerInfo');
    logWarn('two\r\nthree');
  });
  await expect(page.locator('.loggerRow')).toHaveCount(3);
  await expect(page.locator('.loggerMsg').first()).toHaveText('<img\u00a0src=x\u00a0onerror="window.injected=true">');
  await expect(page.locator('.LogServerInfo img')).toHaveCount(0);
  await expect(page.locator('.LogWarn')).toHaveCount(2);
  await page.evaluate(() => { Logger.disable(); log('ignored'); Logger.enable(); Logger.error('failure', new Error('details')); });
  await expect(page.locator('.loggerRow')).toHaveCount(3);
  await expect(page.locator('.LogError')).toHaveText('failure\u00a0Error:\u00a0details');
  await page.evaluate(() => Logger.open());
  await expect(page.locator('#loggerContainer')).toHaveCSS('bottom', '0px');
  await expect(page.locator('#logger')).toHaveCSS('visibility', 'visible');
  await page.evaluate(() => { Logger.close(); Logger.open(); Logger.close(); });
  await expect(page.locator('#loggerContainer')).toHaveCSS('bottom', '-215px');
  await expect(page.locator('#logger')).toHaveCSS('visibility', 'hidden');
  await page.locator('#loggerTab').press('Enter');
  await expect(page.locator('#loggerContainer')).toHaveCSS('bottom', '0px');
  await page.evaluate(() => Logger.hide());
  await expect(page.locator('#loggerContainer')).toBeHidden();
  await page.evaluate(() => { Logger.show(); Logger.clear(); });
  await expect(page.locator('#loggerContainer')).toBeVisible();
  await expect(page.locator('.loggerRow')).toHaveCount(0);
});

test('logger initialization is idempotent and handles absent values and bounded rows', async ({ page }) => {
  const result = await page.evaluate(() => {
    Logger.init(); Logger.init(); Logger.clear();
    log(); Logger.print(undefined); Logger.print(null); log(42); log(false);
    const messages = [...document.querySelectorAll('.loggerMsg')].map(e => e.textContent);
    Logger.setMaxRows(2);
    return { messages, rows: document.querySelectorAll('.loggerRow').length, panels: document.querySelectorAll('#loggerContainer').length };
  });
  expect(result).toEqual({ messages: ['', 'undefined', 'null', '42', 'false'], rows: 2, panels: 1 });
});

for (const [format, mime] of [['PNG','image/png'],['JPEG','image/jpeg'],['BMP','image/bmp']]) {
  test(`${format} exports decode with correct dimensions and pixels`, async ({ page }) => {
    const result = await page.evaluate(async format => {
      const canvas = document.querySelector('canvas');
      const context = canvas.getContext('2d');
      context.fillStyle = '#ff0000'; context.fillRect(0,0,3,1);
      context.fillStyle = '#0000ff'; context.fillRect(0,1,3,1);
      const image = Canvas2Image['saveAs'+format](canvas, true);
      await image.decode();
      const copy = document.createElement('canvas'); copy.width=image.width; copy.height=image.height;
      const target = copy.getContext('2d'); target.drawImage(image,0,0);
      const scaled = Canvas2Image['saveAs'+format](canvas,true,6,4); await scaled.decode();
      return { src:image.src.slice(0,30),width:image.width,height:image.height,scaled:[scaled.width,scaled.height],pixels:[...target.getImageData(0,0,3,2).data] };
    },format);
    expect(result.src).toMatch(new RegExp('^data:'+mime+';base64,'));
    expect([result.width,result.height]).toEqual([3,2]);
    expect(result.scaled).toEqual([6,4]);
    if(format!=='JPEG') {
      expect(result.pixels.slice(0,4)).toEqual([255,0,0,255]);
      expect(result.pixels.slice(12,16)).toEqual([0,0,255,255]);
    }
  });
}

test('BMP includes padding in file size and pixel offset; invalid dimensions fail safely', async ({ page }) => {
  const data = await page.evaluate(() => {
    const canvas=document.querySelector('canvas');
    const src=Canvas2Image.saveAsBMP(canvas,true).src;
    const bytes=Uint8Array.from(atob(src.split(',')[1]),c=>c.charCodeAt(0));
    const header=new DataView(bytes.buffer);
    return { length:bytes.length,size:header.getUint32(2,true),offset:header.getUint32(10,true),pixels:header.getUint32(34,true),invalid:Canvas2Image.saveAsPNG(canvas,true,-1,2),empty:Canvas2Image.saveAsBMP(document.createElement('canvas'),true,0,0) };
  });
  expect(data).toEqual({ length:78,size:78,offset:54,pixels:24,invalid:false,empty:false });
});

test('native PNG download keeps the page and its workspace state in place', async ({ page }) => {
  const before=page.url();
  const downloadPromise=page.waitForEvent('download');
  await page.evaluate(() => { window.workspaceMarker='retained'; Canvas2Image.saveAsPNG(document.querySelector('canvas')); });
  const download=await downloadPromise;
  const bytes=await fs.readFile(await download.path());
  expect([...bytes.subarray(0,8)]).toEqual([137,80,78,71,13,10,26,10]);
  expect(page.url()).toBe(before);
  expect(await page.evaluate(()=>window.workspaceMarker)).toBe('retained');
  expect(download.suggestedFilename()).toBe('download.png');
});

test('actual plot PNG and PDF exports retain plotted content through Plotly', async ({ page }) => {
  for (const script of ['external/jquery-4.0.0.min.js','external/jquery-ui-1.14.1.min.js','config.js','common.js','htmlControls.js','tabPanels/tabpanel.js','plots/plotter.js','plots/plot.js','external/plotly-3.6.0.min.js','external/jspdf_1_3_3.min.js']) {
    await page.addScriptTag({path:path.join(scripts,script)});
  }
  await page.evaluate(async()=>{
    const element=document.createElement('div'); document.body.append(element);
    await Plotly.newPlot(element,[{x:[0,1,2],y:[0,1,0],line:{color:'rgb(0,0,255)',width:5}}],{width:500,height:300,title:{text:'DAVE export'}});
    window.exportPlot=new Plot('nativeExport',{styles:{title:'Native export'}}); exportPlot.plotElem=element;
  });
  for (const [action,magic] of [['saveAsPNG',[137,80,78,71]],['saveAsPDF',[37,80,68,70]]]) {
    const pending=page.waitForEvent('download');
    await page.evaluate(action=>exportPlot[action](),action);
    const download=await pending;
    const bytes=await fs.readFile(await download.path());
    expect([...bytes.subarray(0,4)]).toEqual(magic);
    const raster=action==='saveAsPDF' ? bytes.subarray(bytes.indexOf(Buffer.from([255,216,255])),bytes.lastIndexOf(Buffer.from([255,217]))+2) : bytes;
    const content=await page.evaluate(async ({base64,mime})=>{
      const image=new Image(); image.src='data:'+mime+';base64,'+base64; await image.decode();
      const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
      const context=canvas.getContext('2d');context.drawImage(image,0,0);
      const rgba=context.getImageData(0,0,canvas.width,canvas.height).data;
      let blue=0;for(let i=0;i<rgba.length;i+=4)if(rgba[i+2]>rgba[i]+60&&rgba[i+2]>rgba[i+1]+60)blue++;
      return {width:canvas.width,height:canvas.height,blue};
    },{base64:raster.toString('base64'),mime:action==='saveAsPDF'?'image/jpeg':'image/png'});
    expect([content.width,content.height]).toEqual([500,300]);
    expect(content.blue).toBeGreaterThan(300);
  }
});
