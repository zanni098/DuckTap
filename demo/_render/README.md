# How `demo/ducktap.gif` was made

The GIF is a **styled replay of real DuckTap output** — not a mockup. The numbers
(19 operations, 11/5/3 files, 87/100 (B) scorecard, per-dimension scores) come
from an actual run on this machine:

```bash
ducktap press tests/fixtures/petstore.yaml --name petstore
```

Captured output is in `run_petstore.txt`.

## Reproduce / regenerate

1. The session text lives in `session.js` (`window.SESSION`). Update it if the
   real CLI output changes — keep it matching a real run, never hand-edited numbers.
2. `terminal.html` renders the session into a terminal with a typing/reveal
   animation, exposing `window.setFrame(i)` and `window.FRAME_COUNT`.
3. Serve this folder and screenshot each frame, e.g. with Playwright:
   ```js
   await page.goto('http://127.0.0.1:8791/terminal.html');
   const n = await page.evaluate(() => window.FRAME_COUNT);
   for (let i = 0; i < n; i++) {
     await page.evaluate((k) => window.setFrame(k), i);
     await page.locator('#term').screenshot({ path: `frames/frame_${String(i).padStart(3,'0')}.png` });
   }
   ```
4. Assemble the frames into a GIF with Pillow (fast typing, ~210ms per output
   line, long final hold).

`frames/`, `out/`, and `out2/` are scratch and git-ignored.

A terminal-recorded alternative (asciinema-style) is described in `../DEMO.md`
via a [VHS](https://github.com/charmbracelet/vhs) tape (`../demo.tape`).
