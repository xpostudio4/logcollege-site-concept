(function () {
  'use strict';

  // Mobile menu (full screen)
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('site-nav');
  var closeBtn = document.querySelector('.menu-close');
  function setMenu(open) {
    nav.classList.toggle('open', open);
    document.body.classList.toggle('menu-open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) { (closeBtn || nav).focus(); } else { btn.focus(); }
  }
  if (btn && nav) {
    btn.addEventListener('click', function () { setMenu(true); });
    if (closeBtn) closeBtn.addEventListener('click', function () { setMenu(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('open')) setMenu(false);
    });
    window.addEventListener('resize', function () {
      if (window.innerWidth > 980 && nav.classList.contains('open')) setMenu(false);
    });
  }

  // Desktop dropdowns
  var groups = document.querySelectorAll('.nav-group');
  function closeAll(except) {
    groups.forEach(function (g) { if (g !== except) { g.classList.remove('open'); g.querySelector('.nav-top').setAttribute('aria-expanded', 'false'); } });
  }
  groups.forEach(function (g) {
    var b = g.querySelector('.nav-top');
    b.addEventListener('click', function () {
      if (window.innerWidth <= 980) return;
      var open = !g.classList.contains('open');
      closeAll(g);
      g.classList.toggle('open', open);
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    var timer;
    function hoverable() { return window.innerWidth > 980 && window.matchMedia('(hover: hover)').matches; }
    g.addEventListener('mouseenter', function () {
      if (!hoverable()) return;
      clearTimeout(timer); closeAll(g); g.classList.add('open'); b.setAttribute('aria-expanded', 'true');
    });
    g.addEventListener('mouseleave', function () {
      if (!hoverable()) return;
      timer = setTimeout(function () { g.classList.remove('open'); b.setAttribute('aria-expanded', 'false'); }, 250);
    });
  });
  document.addEventListener('click', function (e) { if (!e.target.closest('.nav-group')) closeAll(null); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeAll(null); });

  // Expand / collapse all courses
  document.querySelectorAll('[data-toggle-all]').forEach(function (t) {
    t.addEventListener('click', function () {
      var list = document.querySelectorAll('details.course');
      var anyClosed = Array.prototype.some.call(list, function (d) { return !d.open; });
      list.forEach(function (d) { d.open = anyClosed; });
      t.textContent = anyClosed ? 'Collapse all' : 'Expand all';
    });
  });

  // Open a course when arriving at its anchor
  function openHash() {
    if (!location.hash) return;
    var el = document.getElementById(location.hash.slice(1));
    if (el && el.tagName === 'DETAILS') { el.open = true; el.scrollIntoView({ block: 'start' }); }
  }
  window.addEventListener('hashchange', openHash);
  openHash();

  // Table of contents highlight
  var tocLinks = document.querySelectorAll('.toc a');
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var map = {};
    tocLinks.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          tocLinks.forEach(function (a) { a.classList.remove('active'); });
          var a = map[en.target.id];
          if (a) a.classList.add('active');
        }
      });
    }, { rootMargin: '-30% 0px -60% 0px' });
    Object.keys(map).forEach(function (id) { var s = document.getElementById(id); if (s) io.observe(s); });
  }

  // Filterable lists (catalog + library)
  document.querySelectorAll('[data-filter-root]').forEach(function (root) {
    var items = Array.prototype.slice.call(root.querySelectorAll(root.getAttribute('data-item')));
    var q = root.querySelector('[data-q]');
    var count = root.querySelector('[data-count]');
    var empty = root.querySelector('[data-empty]');
    var more = root.querySelector('[data-more]');
    var pageSize = parseInt(root.getAttribute('data-page') || '0', 10);
    var limit = pageSize;
    var noun = root.querySelector('.lib') ? ['resource', 'resources'] : ['course', 'courses'];

    function radio(name) {
      var sel = root.querySelector('select[name="' + name + '"]');
      if (sel) return sel.value;
      var r = root.querySelector('input[name="' + name + '"]:checked');
      return r ? r.value : '';
    }

    function apply() {
      var term = (q && q.value || '').trim().toLowerCase();
      var words = term ? term.split(/\s+/) : [];
      var dept = radio('dept'), level = radio('level'), kind = radio('kind');
      var shown = 0, matched = 0;
      items.forEach(function (el) {
        var s = el.getAttribute('data-search') || '';
        var ok = words.every(function (w) { return s.indexOf(w) !== -1; });
        if (ok && dept) ok = el.getAttribute('data-dept') === dept;
        if (ok && level) ok = (' ' + el.getAttribute('data-levels') + ' ').indexOf(' ' + level + ' ') !== -1;
        if (ok && kind) ok = el.getAttribute('data-kind') === kind;
        if (ok) matched++;
        var visible = ok && (!limit || shown < limit);
        if (visible) shown++;
        el.hidden = !visible;
      });
      if (count) count.textContent = matched === items.length
        ? 'Showing ' + (limit && matched > limit ? shown + ' of ' : 'all ') + matched.toLocaleString() + ' ' + noun[1]
        : matched.toLocaleString() + ' ' + (matched === 1 ? noun[0] : noun[1]) + ' match' + (limit && matched > shown ? ' (showing ' + shown + ')' : '');
      if (empty) empty.hidden = matched !== 0;
      if (more) more.parentNode.hidden = !(limit && matched > shown);
    }

    var t;
    if (q) q.addEventListener('input', function () { clearTimeout(t); t = setTimeout(function () { limit = pageSize; apply(); }, 120); });
    root.querySelectorAll('input[type="radio"], select').forEach(function (r) { r.addEventListener('change', function () { limit = pageSize; apply(); }); });
    if (more) more.addEventListener('click', function () { limit += pageSize * 2; apply(); });
    root.querySelectorAll('[data-clear]').forEach(function (c) {
      c.addEventListener('click', function () {
        if (q) q.value = '';
        root.querySelectorAll('input[type="radio"][value=""]').forEach(function (r) { r.checked = true; });
        root.querySelectorAll('select').forEach(function (sl) { sl.value = ''; });
        limit = pageSize; apply(); if (q) q.focus();
      });
    });
    // deep link: ?q=term
    var pq = new URLSearchParams(location.search).get('q');
    if (pq && q) q.value = pq;
    apply();
  });
})();
