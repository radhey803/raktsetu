const puppeteer = require('puppeteer');

(async () => {
    console.log("Launching browser...");
    const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
    const page = await browser.newPage();
    
    await page.setRequestInterception(true);
    
    page.on('request', request => {
        const url = request.url();
        if (url.includes('blood') || url.includes('api') || url.includes('.cnt') || url.includes('eraktkosh/master') || url.includes('search')) {
            console.log(`[REQUEST] ${request.method()} ${url}`);
            if (request.method() === 'POST' || request.method() === 'PUT') {
                console.log(`[PAYLOAD] ${request.postData()}`);
            }
        }
        request.continue();
    });

    console.log("Navigating to eRaktKosh search page...");
    await page.goto('https://eraktkosh.mohfw.gov.in/eraktkoshPortal/#/publicPages/bloodAvailabilitySearch', { waitUntil: 'networkidle2' });
    
    try {
        console.log("Selecting state 'Delhi'...");
        // Wait for the state dropdown to appear
        await page.waitForSelector('select[name="stateCode"]', {timeout: 5000});
        // Delhi is usually code '94' or similar, let's just select the second option
        await page.select('select[name="stateCode"]', '94'); 
        
        console.log("Waiting for District to populate...");
        await new Promise(r => setTimeout(r, 2000)); // wait for network

        console.log("Clicking Search...");
        // If there's a search button, click it. 
        // eRaktkosh usually has a button with text "Search"
        await page.evaluate(() => {
            let btns = document.querySelectorAll('button');
            for(let btn of btns) {
                if(btn.innerText.includes('Search')) {
                    btn.click();
                    break;
                }
            }
        });

        console.log("Waiting 5 seconds for results to load...");
        await new Promise(r => setTimeout(r, 5000));
    } catch(e) {
        console.log("Error interacting:", e);
    }
    
    await browser.close();
    console.log("Done.");
})();
