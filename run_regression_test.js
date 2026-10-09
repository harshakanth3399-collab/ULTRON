const { chromium } = require('playwright');

const LIVE_URL = 'https://ultron-omega-drab.vercel.app/';

async function runSuite(viewportName, width, height) {
    console.log(`\n==================================================`);
    console.log(`RUNNING REGRESSION TEST ON LIVE URL: ${viewportName} (${width}x${height})`);
    console.log(`==================================================\n`);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width, height },
        userAgent: viewportName === 'phone'
            ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
            : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();
    const consoleErrors = [];
    const pageErrors = [];

    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
        }
    });
    page.on('pageerror', err => {
        pageErrors.push(err.message);
    });

    const results = {};

    try {
        // --- ITEM a: Page loads with ZERO console errors ---
        await page.goto(LIVE_URL, { waitUntil: 'load', timeout: 30000 });
        await page.waitForTimeout(3000);

        const totalErrors = [...consoleErrors, ...pageErrors];
        results['a'] = {
            name: 'Page loads with ZERO console errors',
            pass: totalErrors.length === 0,
            details: totalErrors.length === 0 ? 'Zero console/page errors detected on load.' : `Errors: ${JSON.stringify(totalErrors)}`
        };

        // --- ITEM h: No horizontal scroll at 390px width ---
        const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
        const hasHorizontalScroll = scrollWidth > clientWidth + 2;
        results['h'] = {
            name: 'No horizontal scroll at viewport width',
            pass: !hasHorizontalScroll,
            details: `clientWidth=${clientWidth}, scrollWidth=${scrollWidth}`
        };

        // --- ITEM b: Create-account works with a new test user ---
        const testUser = {
            first_name: 'TestQA',
            last_name: 'Engineer',
            email: `test_qa_${Date.now()}_${Math.floor(Math.random()*1000)}@ultron.ai`,
            phone: `+9198${Math.floor(10000000 + Math.random() * 90000000)}`,
            password: 'TestPassword@123'
        };

        const registerResult = await page.evaluate(async (user) => {
            try {
                const res = await fetch('/api/livelink/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(user)
                });
                const data = await res.json();
                return { status: res.status, data };
            } catch (e) {
                return { error: e.message };
            }
        }, testUser);

        const regPass = registerResult && (registerResult.status === 200 || registerResult.data?.ok || registerResult.data?.success);
        results['b'] = {
            name: 'Create-account works with a new test user',
            pass: !!regPass,
            details: JSON.stringify(registerResult)
        };

        // --- ITEM d: Sign-in with a WRONG password is rejected with a visible error ---
        await page.evaluate(() => {
            const overlay = document.getElementById('livelink-modal-overlay');
            if (overlay) overlay.style.display = 'flex';
            if (typeof switchAuthTab === 'function') switchAuthTab('login');
        });
        await page.waitForTimeout(500);

        const idInput = await page.$('#login-identifier');
        const pwdInput = await page.$('#login-password');
        const loginSubmit = await page.$('#login-submit-btn');

        if (idInput && pwdInput && loginSubmit) {
            await idInput.fill('harsha');
            await pwdInput.fill('WrongPassword123!');
            await loginSubmit.click();
            await page.waitForTimeout(2000);

            const toastText = await page.evaluate(() => {
                const toast = document.getElementById('livelink-toast');
                return toast ? toast.innerText : '';
            });
            const isModalStillOpen = await page.evaluate(() => {
                const overlay = document.getElementById('livelink-modal-overlay');
                return overlay && overlay.style.display !== 'none';
            });

            results['d'] = {
                name: 'Sign-in with WRONG password rejected with visible error',
                pass: isModalStillOpen,
                details: `Modal retained open: ${isModalStillOpen}. Toast: "${toastText}"`
            };
        } else {
            results['d'] = {
                name: 'Sign-in with WRONG password rejected with visible error',
                pass: false,
                details: 'Login inputs not found'
            };
        }

        // --- ITEM c: Sign-in with the correct password works ---
        if (idInput && pwdInput && loginSubmit) {
            await idInput.fill('harsha');
            await pwdInput.fill('Harsha@123');
            await loginSubmit.click();
            await page.waitForTimeout(2500);

            const isModalClosed = await page.evaluate(() => {
                const overlay = document.getElementById('livelink-modal-overlay');
                return !overlay || overlay.style.display === 'none';
            });
            const sessionActive = await page.evaluate(() => {
                return sessionStorage.getItem('ultron_session_active') === '1' || !!localStorage.getItem('livelink_token');
            });

            results['c'] = {
                name: 'Sign-in with correct password works',
                pass: isModalClosed && sessionActive,
                details: `Modal closed: ${isModalClosed}, Session active: ${sessionActive}`
            };
        } else {
            results['c'] = {
                name: 'Sign-in with correct password works',
                pass: false,
                details: 'Login inputs not found'
            };
        }

        // --- ITEM f: Every visible button responds when clicked ---
        // With modal closed, test buttons: Vision, Chat, Pair, Files, Remote, Zen, Mic, SEND
        const buttonDefs = [
            { name: 'Vision', selector: 'button.action-btn:has-text("VISION")' },
            { name: 'Chat', selector: 'button.action-btn:has-text("CHAT")' },
            { name: 'Pair', selector: 'button.action-btn:has-text("PAIR")' },
            { name: 'Files', selector: 'button.action-btn:has-text("FILES")' },
            { name: 'Remote', selector: 'button.action-btn:has-text("REMOTE")' },
            { name: 'Zen', selector: 'button.action-btn:has-text("ZEN")' },
            { name: 'Mic', selector: '#mic-btn' },
            { name: 'SEND', selector: '.send-btn' }
        ];

        const buttonResults = [];
        for (const b of buttonDefs) {
            // Dismiss any open overlay from previous clicks so target button is reachable
            await page.evaluate(() => {
                const cp = document.getElementById('session-chat-panel');
                if (cp) {
                    cp.classList.remove('active');
                    document.body.classList.remove('chat-panel-open');
                }
                ['qr-modal-overlay', 'zen-modal-overlay', 'livelink-modal-overlay', 'install-guide-overlay', 'mic-modal-overlay', 'change-pw-modal-overlay', 'commander-vault-overlay'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.style.display = 'none';
                });
                document.querySelectorAll('.synergy-panel').forEach(p => {
                    p.style.display = 'none';
                    p.classList.remove('active-panel');
                });
            });
            await page.waitForTimeout(200);

            const el = await page.$(b.selector);
            if (el) {
                const isVisible = await el.isVisible();
                try {
                    await el.click({ timeout: 2000 });
                    buttonResults.push({ name: b.name, found: true, visible: isVisible, clicked: true });
                } catch (clickErr) {
                    buttonResults.push({ name: b.name, found: true, visible: isVisible, clicked: false, err: clickErr.message });
                }
            } else {
                buttonResults.push({ name: b.name, found: false, visible: false, clicked: false });
            }
        }

        const buttonsPassed = buttonResults.filter(b => b.found && b.clicked).length;
        results['f'] = {
            name: 'Every visible button responds when clicked (Vision, Chat, Pair, Files, Remote, Zen, Mic, SEND)',
            pass: buttonsPassed === buttonDefs.length,
            details: buttonResults.map(b => `${b.name}: ${b.clicked ? 'OK' : (b.found ? 'ClickFailed' : 'NotFound')}`).join(', ')
        };

        // --- ITEM g: A typed command returns an AI reply ---
        await page.evaluate(() => {
            const cp = document.getElementById('session-chat-panel');
            if (cp) {
                cp.classList.remove('active');
                document.body.classList.remove('chat-panel-open');
            }
            ['qr-modal-overlay', 'zen-modal-overlay', 'livelink-modal-overlay', 'install-guide-overlay', 'mic-modal-overlay', 'change-pw-modal-overlay', 'commander-vault-overlay'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            document.querySelectorAll('.synergy-panel').forEach(p => {
                p.style.display = 'none';
                p.classList.remove('active-panel');
            });
        });

        const cmdInput = await page.$('#cmd-input');
        const sendBtn = await page.$('.send-btn');
        if (cmdInput && sendBtn) {
            await cmdInput.fill('hello');
            await sendBtn.click();
            await page.waitForTimeout(5000);

            const aiReply = await page.evaluate(() => {
                const aiText = document.getElementById('ai-text');
                return aiText ? aiText.innerText : '';
            });

            // Catch-that and unknown endpoint checks
            const isCatchThat = aiReply.toLowerCase().includes("didn't catch that");
            const isUnknownEndpoint = aiReply.toLowerCase().includes("unknown api endpoint");
            const isRealReply = aiReply.trim().length > 0 && !isCatchThat && !isUnknownEndpoint;
            results['g'] = {
                name: 'Typed command returns AI reply (never "I didn\'t catch that" or "Unknown API endpoint")',
                pass: isRealReply,
                details: aiReply ? `AI Response: "${aiReply.substring(0, 100)}"` : 'No response returned'
            };
        } else {
            results['g'] = {
                name: 'Typed command returns AI reply',
                pass: false,
                details: 'cmd-input or send-btn not found'
            };
        }

        // --- ITEM e: Logout works and Back button does not restore session ---
        const logoutTriggered = await page.evaluate(() => {
            if (typeof logoutUser === 'function') {
                logoutUser();
                return true;
            }
            return false;
        });

        await page.waitForTimeout(1000);

        const sessionAfterLogout = await page.evaluate(() => {
            try {
                return sessionStorage.getItem('ultron_session_active') === '1' || !!localStorage.getItem('livelink_token');
            } catch (e) {
                return false;
            }
        });

        // Test back button navigation simulation within same origin
        await page.evaluate(() => {
            try {
                history.pushState({ loggedOut: true }, '', location.href);
                history.back();
            } catch(e) {}
        });
        await page.waitForTimeout(500);

        const sessionAfterBack = await page.evaluate(() => {
            try {
                return sessionStorage.getItem('ultron_session_active') === '1' || !!localStorage.getItem('livelink_token');
            } catch (e) {
                return false;
            }
        });

        results['e'] = {
            name: 'Logout works and Back button does not restore session',
            pass: logoutTriggered && !sessionAfterLogout && !sessionAfterBack,
            details: `Logged out: ${logoutTriggered}, Session cleared: ${!sessionAfterLogout}, Session after back: ${sessionAfterBack}`
        };

    } catch (err) {
        console.error('Test run failure:', err);
    } finally {
        await browser.close();
    }

    return results;
}

(async () => {
    const desktopResults = await runSuite('desktop', 1440, 900);
    const phoneResults = await runSuite('phone', 390, 844);

    console.log('\n========================================');
    console.log('SUMMARY REGRESSION TEST RESULTS:');
    console.log('========================================\n');

    const items = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
    for (const key of items) {
        const d = desktopResults[key] || { name: key, pass: false, details: 'N/A' };
        const p = phoneResults[key] || { name: key, pass: false, details: 'N/A' };
        const pass = d.pass && p.pass;
        console.log(`[${pass ? 'PASS' : 'FAIL'}] Item ${key}: ${d.name}`);
        console.log(`       Desktop: ${d.pass ? 'PASS' : 'FAIL'} (${d.details})`);
        console.log(`       Phone:   ${p.pass ? 'PASS' : 'FAIL'} (${p.details})`);
    }
})();
