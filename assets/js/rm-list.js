/* Client-side filter / search / sort / count for generated lists.
   Markup: [data-rm-list] containing li.rm-item (data-year, data-date, data-type,
   data-ref, data-inv, data-intl, data-sel, data-text), optional .rm-yg (year
   groups) and .rm-sec (sections), and controls [data-f=q|year|type|ref|inv|intl|sel|sort]. */
(function () {
  function init(root) {
    var items = [].slice.call(root.querySelectorAll("li.rm-item"));
    var groups = [].slice.call(root.querySelectorAll(".rm-yg"));
    var secs = [].slice.call(root.querySelectorAll(".rm-sec"));
    var ctl = function (n) { return root.querySelector('[data-f="' + n + '"]'); };
    var q = ctl("q"), year = ctl("year"), type = ctl("type"), sort = ctl("sort");
    var flags = ["ref", "inv", "intl", "sel"];
    function fill(sel, key, numeric) {
      if (!sel) return;
      var vals = {};
      items.forEach(function (li) { var v = li.dataset[key]; if (v) vals[v] = 1; });
      var keys = Object.keys(vals).sort();
      if (numeric) keys.reverse();
      keys.forEach(function (v) { var o = document.createElement("option"); o.value = v; o.textContent = v; sel.appendChild(o); });
      if (keys.length < 2) sel.hidden = true;
    }
    fill(year, "year", true); fill(type, "type", false);
    flags.forEach(function (f) {
      var c = ctl(f); if (!c) return;
      if (!items.some(function (li) { return li.dataset[f]; })) c.closest("label").hidden = true;
    });
    items.forEach(function (li, i) { li._i = i; });
    var total = root.querySelector("[data-total]"); if (total) total.textContent = items.length;
    var n = root.querySelector("[data-n]"), empty = root.querySelector(".rm-empty");
    function apply() {
      var words = q ? q.value.toLowerCase().split(/\s+/).filter(Boolean) : [];
      var shown = 0;
      items.forEach(function (li) {
        var d = li.dataset, ok = true;
        if (year && year.value && d.year !== year.value) ok = false;
        if (type && type.value && d.type !== type.value) ok = false;
        flags.forEach(function (f) { var c = ctl(f); if (c && c.checked && !d[f]) ok = false; });
        for (var k = 0; ok && k < words.length; k++) if ((d.text || "").indexOf(words[k]) < 0) ok = false;
        li.hidden = !ok; if (ok) shown++;
      });
      groups.forEach(function (g) { g.hidden = !g.querySelector("li.rm-item:not([hidden])"); });
      secs.forEach(function (s) { s.hidden = !s.querySelector("li.rm-item:not([hidden])"); });
      [].forEach.call(root.querySelectorAll(".rm-toc a"), function (a) {
        var t = root.querySelector(a.getAttribute("href")); if (t) a.hidden = !!t.closest("[hidden]");
      });
      if (n) n.textContent = shown;
      if (empty) empty.hidden = shown > 0;
    }
    function order() {
      if (!sort) return;
      var dir = sort.value === "old" ? 1 : -1;   // 1 = ascending
      function cmp(x, y) { return x < y ? -dir : x > y ? dir : 0; }
      var byParent = new Map();
      groups.forEach(function (g) {
        var p = g.parentNode;
        if (!byParent.has(p)) byParent.set(p, []);
        byParent.get(p).push(g);
      });
      byParent.forEach(function (gs, p) {
        gs.sort(function (a, b) { return cmp(a.dataset.year, b.dataset.year); });
        gs.forEach(function (g) { p.appendChild(g); });
      });
      groups.forEach(function (g) {
        var ol = g.querySelector("ol"), lis = [].slice.call(ol.children);
        lis.sort(function (a, b) { return cmp(a.dataset.date, b.dataset.date) || a._i - b._i; });
        lis.forEach(function (li) { ol.appendChild(li); });
      });
    }
    [q, year, type, sort].concat(flags.map(ctl)).forEach(function (c) {
      if (!c) return;
      c.addEventListener(c === q ? "input" : "change", function () { if (c === sort) order(); apply(); });
    });
    apply();
  }
  [].forEach.call(document.querySelectorAll("[data-rm-list]"), init);
})();
