(function () {
  var path = window.location.pathname.replace(/\/index\.html$/, "/");
  if (path === "/" || path === "/index.html") return;
  if (document.querySelector(".cc-console-bar")) return;

  var pages = [
    { title: "Hearing Room", short: "Hearing", href: "/hearing-room/", color: "#f0524d", note: "Counsel, calendar, deadlines." },
    { title: "Ledger", short: "Ledger", href: "/the-ledger/", color: "#ef3b86", note: "Debt, cash flow, accounts, APRs." },
    { title: "Blindspot Almanac", short: "Almanac", href: "/production-almanac/", color: "#f4c51d", note: "Production chapters, cases, sources." },
    { title: "Notebook", short: "Notebook", href: "/notes/", color: "#2fc5b7", note: "Fragments, drafts, links, open loops." },
    { title: "Workflow Wrench", short: "Wrench", href: "/the-workflow-wrench/", color: "#f0601d", note: "Prompts, automations, SOPs." },
    { title: "Playlist Tracker", short: "Playlists", href: "/playlist-tracker/", color: "#36a3df", note: "Spotify portfolio and momentum." },
    { title: "Wellness", short: "Wellness", href: "/wellness-dashboard/", color: "#82ca55", note: "Apple Health and RingConn signal." },
    { title: "Readwise", short: "Readwise", href: "/readwise-highlights/", color: "#9b72d9", note: "Highlights, marginalia, sources." },
    { title: "AI Intelligence", short: "AI Intel", href: "/ai-intelligence/", color: "#a77adf", note: "Conversation patterns and exports." },
    { title: "Binder", short: "Binder", href: "/the-blindspot-binder/", color: "#f0524d", note: "Channel operating manual." },
    { title: "Eastern Front", short: "E. Front", href: "/easternfront/", color: "#f0563c", note: "Assembly bench, highlight map, revenge arc." },
    { title: "Color Bible", short: "Color", href: "/the-color-bible/", color: "#f0524d", note: "Five-color taxonomy." },
    { title: "Digital Ecosystem", short: "Ecosystem", href: "/digital-ecosystem-refresh/", color: "#69d6e4", note: "Maintenance routines and risks." },
    { title: "Screenwriting & Film Production", short: "Film Prod", href: "/screenwriting-and-film-production/", color: "#2fc5b7", note: "Story, directing, production." }
  ];

  function normalized(href) {
    return href.replace(/\/index\.html$/, "/");
  }

  var current = pages.find(function (page) {
    return path === normalized(page.href) || path.indexOf(normalized(page.href)) === 0;
  }) || { title: document.title || "Chaos Console", short: "Console", color: "#ef3b86" };

  document.documentElement.style.setProperty("--cc-page-color", current.color);

  var bar = document.createElement("nav");
  bar.className = "cc-console-bar";
  bar.setAttribute("aria-label", "Chaos Console");
  bar.innerHTML =
    '<a class="cc-console-brand" href="/">' +
      '<span class="cc-console-mark" aria-hidden="true">C</span>' +
      '<span class="cc-console-name">Chaos Console</span>' +
    '</a>' +
    '<div class="cc-console-links">' +
      pages.slice(0, 7).map(function (page) {
        return '<a href="' + page.href + '">' + page.short + "</a>";
      }).join("") +
    '</div>' +
    '<div class="cc-console-actions">' +
      '<span class="cc-console-current">' + current.short + '</span>' +
      '<button class="cc-map-button" type="button" aria-expanded="false" aria-controls="cc-console-map">Map</button>' +
    '</div>';

  var map = document.createElement("section");
  map.className = "cc-console-map";
  map.id = "cc-console-map";
  map.setAttribute("aria-label", "Console map");
  map.innerHTML =
    '<div class="cc-map-inner">' +
      '<div class="cc-map-grid">' +
        pages.map(function (page) {
          return '<a class="cc-map-link" style="--cc-tile-color:' + page.color + '" href="' + page.href + '">' +
            '<strong>' + page.title + '</strong>' +
            '<span>' + page.note + '</span>' +
          '</a>';
        }).join("") +
      '</div>' +
      '<div class="cc-map-meta"><span>Private console</span><span>Gary / 2026</span></div>' +
    '</div>';

  document.body.insertBefore(map, document.body.firstChild);
  document.body.insertBefore(bar, document.body.firstChild);

  var button = bar.querySelector(".cc-map-button");
  function closeMap() {
    map.classList.remove("is-open");
    button.setAttribute("aria-expanded", "false");
  }

  button.addEventListener("click", function () {
    var open = map.classList.toggle("is-open");
    button.setAttribute("aria-expanded", open ? "true" : "false");
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeMap();
  });

  document.addEventListener("click", function (event) {
    if (!map.classList.contains("is-open")) return;
    if (bar.contains(event.target) || map.contains(event.target)) return;
    closeMap();
  });
})();
