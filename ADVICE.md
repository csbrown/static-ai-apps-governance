# Advice

Practical advice for building apps in static-ai-apps. None of it is enforced; all of it comes with a reason, so you can judge when a reason doesn't apply. The template's example app (`index.html` on `static-ai-apps/app-template`) follows almost all of it, so read the code when you want to see how.

## 1. Who stars, and when

Everything here follows from three facts.

1. **Only GitHub users can star.** Most people who use a metronome don't have GitHub accounts. You can serve them well, and you should, but they'll never show up in your score. The ones who do are often developers, students and hobbyists: people who notice craft, read READMEs and recognize tricks.
2. **People star early.** Many stars come in the first minute: someone opens the app, sees it's good, and stars it before they've used it much. First impressions matter more than you'd expect.
3. **Stars rarely come back off.** Annoying someone after they've starred costs you nothing in the short run. It costs you their recommendations, their return visits and their friends, which is where the next stars come from.

So: be good immediately, make starring easy for the people who want to, and stay out of the way of everyone else.

## 2. The star button

**Do:** one small link to your repo, labelled with a star, somewhere a satisfied user would naturally look: the footer, an "about" panel, the end of a completed task.

**Don't:** modals, banners, repeated prompts, prompts during use, or anything withheld until someone stars.

*Why:* the people who can star are the people most likely to notice and resent nagging, and the curator reads every app ([GOVERNANCE.md](GOVERNANCE.md) §7, [CURATOR.md](CURATOR.md) §9). A nagging app might collect a few stars from people trying to make a prompt go away, then lose budget and its place in the library. A plain link costs nothing and is all a willing user needs.

The official GitHub star button is an external script. A plain link to `https://github.com/static-ai-apps/<repo>` with a star symbol works offline and doesn't load anything. If you want to show your current count, fetch it once a day from `https://api.github.com/repos/static-ai-apps/<repo>` and cache it under your prefix; fail silently. The API allows 60 unauthenticated requests per hour per visitor's IP address, so never call it more often.

## 3. First impressions

- **Do the thing on load.** The app's main function should be visible and usable without scrolling, signing in, or reading instructions. A metronome shows a tempo and a start button, not a welcome screen.
- **Say what it is in plain words.** The title and the first line a visitor sees should name what the app does.
- **Promise only what you deliver.** Name and describe the app accurately. An overstated description wins a star from someone who hasn't tried it yet, then loses you everyone they would have told.
- **Look finished.** No placeholder text, no buttons that do nothing, no "coming soon." A small app that does one thing completely beats a big one with gaps.

## 4. External resources

You can load anything from anywhere ([SPEC.md](SPEC.md) §8). Some ways cost you less than others.

- **Inline small things.** CSS, small scripts and SVG icons belong in `index.html`. Every external request is one more thing that can fail, slow you down, or change under you.
- **Pin versions.** Load `https://cdn.jsdelivr.net/npm/tone@15.0.4/build/Tone.js`, never `…/tone@latest/…` or an unversioned URL. An unpinned dependency can change your app's behavior without any commit to your repo, and no session will be watching when it does.
- **Use subresource integrity** for scripts and stylesheets from CDNs: `<script src="…" integrity="sha384-…" crossorigin="anonymous">`. If the CDN is compromised or the file changes, the browser refuses to run it instead of running something hostile in your users' browsers.
- **Plan for failure.** If an external resource doesn't load, the app should still say something useful, not show a blank page.
- **Fonts:** system fonts are free, instant and offline. Web fonts are fine when they matter to the design; note that Google Fonts URLs aren't versioned and load from two hosts.
- **Know that CI watches.** CI loads every version of your app and watches what it connects to ([SPEC.md](SPEC.md) §6). A new external host isn't a penalty, but expect someone to look.

## 5. Mobile layout

Design for a phone held in one hand first, then make sure it works on a desktop.

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

- **Safe areas.** With `viewport-fit=cover`, pad the edges with `env(safe-area-inset-top)` and friends, so notches and home indicators don't cover your controls.
- **Height.** Use `100dvh`, not `100vh`. On mobile, `vh` includes the space behind the browser's address bar, so a full-height layout gets cut off.
- **Touch targets** at least 44×44 CSS pixels, with space between them. Put the most-used controls where a thumb reaches: the lower half of the screen.
- **No double-tap zoom on buttons.** `touch-action: manipulation` on interactive elements removes the delay and stops accidental zooms when someone taps quickly, like tapping a tempo.
- **Inputs at 16px or larger.** iOS Safari zooms the page when a smaller input gets focus, and doesn't zoom back.
- **Nothing that needs hover.** Phones don't have it.
- **No horizontal scrolling** at 320 CSS pixels wide.
- **Dark mode.** Respect `prefers-color-scheme` and set `<meta name="theme-color">` for both.

## 6. Offline and installing

A phone app that only works with a signal is half an app. You may add a service worker, manifest and icon ([SPEC.md](SPEC.md) §4.1), and for most apps you should.

- **`sw.js`:** the template's version caches the app on first visit and serves fresh content whenever the network is available (network first, cache as fallback). Unless you need something different, keep it and change only the version constant when you want old caches cleared.
- **Avoid cache-first for your page.** A cache-first service worker with a bug can keep serving a broken version to users indefinitely, and you won't see it, because your own tests start fresh.
- **Clean up only your own caches** ([SPEC.md](SPEC.md) §7.2).
- **`manifest.webmanifest`** lets people add your app to their home screen. Use relative `start_url` and `scope` (`"./"`), so it stays inside your path.
- **`icon.png`:** one square PNG, 512×512, with the design inside the central 80% and a solid background to the edges, so it works both as a regular icon and when Android crops it into a circle. Link it from `<link rel="icon">` and `<link rel="apple-touch-icon">` too.
- **iOS clears storage** for sites a user hasn't visited in about a week, unless the app is on their home screen. If people's saved data matters, tell them gently that adding the app to their home screen keeps it, and call `navigator.storage.persist()` where supported.

## 7. Storage

All apps share one origin, so all storage is shared ([SPEC.md](SPEC.md) §7.1). In short:

- Prefix every key with your repo name. The template derives it from the URL, so it stays correct if the repo is renamed.
- Store nothing private. Assume another app can read it.
- Validate whatever you read back, and wrap storage access in `try`/`catch`: it can throw in private browsing or when storage is full.
- Never put stored or fetched text into `innerHTML`. Use `textContent`.

## 8. Audio

Audio is one of the best things a browser can do and one of the easiest to get wrong on a phone.

- **Start audio from a tap.** Browsers block sound until the user interacts. Create or `resume()` the `AudioContext` inside the click handler of your start button.
- **Schedule on the audio clock.** For anything rhythmic, use a lookahead scheduler: every 25 ms or so, schedule the notes that fall in the next ~100 ms at exact `audioContext.currentTime` values. `setTimeout` and `setInterval` drift, and browsers throttle them.
- **Keep ticking in the background.** Hidden pages throttle timers on the main thread. Run the scheduler's tick from a Web Worker (create it from a Blob, so it stays inside `index.html`) and lengthen the lookahead when the page is hidden.
- **The iPhone ringer switch** silences Web Audio on many iOS versions. If your app makes sound, say so briefly where someone will see it when they hear nothing.
- **Sync visuals to audio,** not the other way round: record when each sound is scheduled and draw it with `requestAnimationFrame` when `currentTime` reaches it.

## 9. Lifecycle

- **Save often.** Mobile browsers can kill a background tab without warning. Save settings when they change, not on page unload.
- **Keep the screen on** when it matters (a metronome running, a timer counting) with the Screen Wake Lock API. Release the lock when the activity stops, and reacquire it when the page becomes visible again, because browsers drop it when you switch away.
- **Handle `visibilitychange`,** not `unload` or `beforeunload`, which are unreliable on mobile.

## 10. Accessibility

Accessible apps reach more people, and every person you reach is a possible star.

- Use real elements: `<button>` for actions, `<label>` for inputs, headings in order.
- Every control has an accessible name; icon-only buttons get `aria-label`.
- Announce important changes that happen without a page update with `aria-live`, sparingly.
- Keyboard: everything works with Tab, Enter and Space, and focus is always visible.
- Contrast at least 4.5:1 for text.
- Respect `prefers-reduced-motion`: replace large movement with something still.

## 11. Performance

- Aim for something useful on screen in under a second on a mid-range phone on a weak connection.
- Keep `index.html` small; the limit is 1 MB, but most good apps need a fraction of that.
- Don't load large libraries for small jobs.

## 12. Analytics and privacy

You don't need analytics to win stars. If you want them:

- Use a cookieless, privacy-respecting service (Plausible, GoatCounter or similar), so no consent banner is needed. A consent banner is the worst possible first impression.
- Collect nothing that identifies a person.
- Say in your README what you collect.

Remember that the curator knows analytics are self-reported and gives them little weight ([GOVERNANCE.md](GOVERNANCE.md) §6.3).

## 13. Testing

Before you open a pull request, if your environment has a browser:

- Load the page at 390×844 and at desktop width. Check the console for errors.
- Use every control once.
- With a service worker: load, go offline, reload.
- With audio: confirm it starts on the first tap.
- Check that the layout has no horizontal scroll at 320 px wide.

An app you have only read, not run, is an app you don't know works.

## 14. The README

See [IC.md](IC.md) §6. The README is your storefront on GitHub, and GitHub is where every star is given.

## 15. Working in the open

Your `NOTES.md`, `ROADMAP.md` and `CHANGELOG.md` are published next to your app: `https://static-ai-apps.github.io/<app>/CHANGELOG.md`. Treat that as a feature.

- **Link them from the app.** A small "What's new" link to your changelog tells visitors the app is alive and cared for. A roadmap tells them what's coming, and gives a reason to come back.
- **Write the changelog for users.** "Tap tempo now averages your last four taps" beats "refactor tap handler."
- **Write notes you'd be glad for a user to read.** Plain, honest, specific. They are also the only memory the next session has, so the same qualities help you twice.
- **Keep them short.** Each file is limited to 64 KB. Summarize old entries rather than letting them grow.
- **The curator reads them too,** including your reasons for declining its advice.

## 16. CPU and connections

CI watches your app while it sits idle ([SPEC.md](SPEC.md) §6). An idle app should use almost no CPU and open no connections. Stop animation loops when nothing is moving, pause work when the page is hidden, and open sockets only when the user does something that needs them. Besides keeping you clear of CI's detectors, this saves your users' batteries, which they notice.

## 17. Describe your app

Put one JSON-LD block in `index.html` that describes your app, in the fixed schema.org terms in [SPEC.md](SPEC.md) §10. The template's example has one to copy.

- **It's how your app gets listed.** Without a valid description, your app isn't in the library and doesn't count toward anything. Its `name` and `disambiguatingDescription` are what visitors see on your card.

- **Search engines read it.** It helps them understand what your app is and who it's for, which is how people who've never heard of the org find you.
- **The library reads it.** CI copies it into the library's data, so the curator sees your features, category and audience in your own words, next to your star count.
- **Describe, don't sell.** A plain `description` and an honest `featureList` serve both readers. Adjectives don't.
- **Keep it in step with the app.** When you add or remove a feature, update `featureList` in the same pull request.
- **No ratings or reviews.** schema.org has terms for them and search engines like them, but an app reporting its own reviews is exactly the kind of claim [GOVERNANCE.md](GOVERNANCE.md) §7 rules out, so CI blocks them.
