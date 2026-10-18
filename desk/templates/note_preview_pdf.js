const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:430,height:932},deviceScaleFactor:2});
await p.goto('file://'+process.cwd()+'/_prev.html');await p.waitForTimeout(500);
await p.pdf({path:process.argv[2],width:'430px',height:'932px',printBackground:true});await b.close();})();
