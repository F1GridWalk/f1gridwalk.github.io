const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:670}});
for(const k of ['N1','N2','N3']){await p.goto('file://'+process.cwd()+'/'+k+'.html');await p.waitForTimeout(500);await p.screenshot({path:k+'.png'});}
await b.close();})();
