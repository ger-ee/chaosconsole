# Rationale

- I cut the broken Daily Pulse entirely because a missing `pulse.json` should not occupy the top of the landing page or throw a console error in production.
- I rewrote the hero to explain the product in one sentence: this is a personal command center for finances, wellness, reading, media, and systems maintenance. The old hero never earned that understanding.
- I added explicit CTA hierarchy with `See core dashboards` and `Browse all 11 tools` because the old page offered no opinion about where a user should start.
- I corrected the information architecture around the real inventory: **11 tools**, grouped into **6 categories**, with four featured entry points that explain the product fastest.
- I removed the PNG preview gallery from the landing page even though it added personality. The tradeoff is less illustration and far better clarity, scanning, and payload discipline.
- I kept the dark + brass direction because it already felt closest to the product, but I stripped out glassy layers, sparkles, and decorative flourishes that made the old page feel scrapbooked.
- I used a system serif + system sans combination instead of loading three webfont families. The tradeoff is less bespoke typography and much better performance control.
- I dropped the theme toggle because it did not help the landing page do its job. The page needed hierarchy and clarity more than a preference switch in the highest-attention corner.
- I kept every real tool name and every existing destination URL. The presentation changed; the product map did not.
- I moved the page toward a product index instead of a portfolio grid. The tradeoff is less visual novelty and stronger orientation.
- I added a skip link, a real `<main>`, stronger focus states, AA-safe type contrast, and reduced-motion handling because the original page missed basic accessibility structure.
- I kept the access gate, but inlined it so `index.html` stays self-contained. The tradeoff is a larger HTML file in exchange for meeting the no-external-JS constraint.
- I chose static semantic HTML over client-side rendering because this page is content and navigation, not application state. Less machinery is the right answer here.
