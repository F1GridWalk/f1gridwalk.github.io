const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const d=process.argv[2];
let p=await b.newPage({viewport:{width:430,height:932},deviceScaleFactor:2});
await p.goto('http://localhost:8765/lens/singapore-odd-records-20261013/',{waitUntil:'networkidle'});await p.waitForTimeout(500);
await p.emulateMedia({media:'screen'});
await p.pdf({path:d+'/a.pdf',width:'430px',height:'932px',printBackground:true});
p=await b.newPage({viewport:{width:430,height:932}});await p.goto('file://'+d+'/opts.html');await p.waitForTimeout(400);
await p.pdf({path:d+'/b.pdf',width:'430px',height:'932px',printBackground:true});await b.close();})();
