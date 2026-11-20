// Player browser (tab 10) and watchlist (tab 11).
// The player payload is embedded in the page as JSON; following is kept in the
// artifact's own store when the page has it, and in this browser otherwise.
(function () {
  'use strict';

  var raw = document.getElementById('player-data');
  if (!raw) { return; }
  var DATA;
  try {
    // the build wraps the payload in HTML comment markers so a refresh can
    // replace it; they are not JSON, so strip them before parsing
    var text = (raw.textContent || '').replace(/<!--[\s\S]*?-->/g, '').trim();
    DATA = JSON.parse(text || '{}');
  } catch (e) {
    var warn = document.getElementById('browser-count');
    if (warn) { warn.textContent = 'Player data could not be read.'; }
    return;
  }
  if (!DATA.players || !DATA.players.length) { return; }

  var MAX_ROWS = 200;
  var teamById = {};
  DATA.teams.forEach(function (t) { teamById[t.id] = t; });
  var posById = {};
  DATA.positions.forEach(function (p) { posById[p.id] = p; });
  var playerById = {};
  DATA.players.forEach(function (p) { playerById[p.i] = p; });

  // ---------------------------------------------------------------- storage
  // db when the viewer has it, localStorage otherwise. Same four methods.
  var LS_KEY = 'fpl_following';
  var store = {
    ready: false, rows: {}, listeners: [], mode: 'local', note: ''
  };

  function emit() {
    store.listeners.forEach(function (fn) {
      try { fn(store.rows); } catch (e) { /* a bad listener must not stop the rest */ }
    });
  }

  function localRead() {
    try { return JSON.parse(window.localStorage.getItem(LS_KEY) || '{}'); }
    catch (e) { return {}; }
  }
  function localWrite(rows) {
    try { window.localStorage.setItem(LS_KEY, JSON.stringify(rows)); } catch (e) {}
  }

  function startLocal(message) {
    store.mode = 'local';
    store.rows = localRead();
    store.ready = true;
    store.note = message || 'Saved in this browser only.';
    emit();
  }

  function startDb(db) {
    store.mode = 'db';
    var collection = db.collection('follow');
    var loading = window.setTimeout(function () {
      if (!store.ready) {
        store.note = 'Still reaching your saved list - it may be out of date.';
        emit();
      }
    }, 10000);

    collection.onSnapshot(function (snap) {
      window.clearTimeout(loading);
      var rows = {};
      snap.docs.forEach(function (doc) {
        var body = doc.data();
        if (body) { rows[doc.id] = body; }
      });
      store.rows = rows;
      store.ready = true;
      store.note = snap.metadata && snap.metadata.fromCache
        ? 'Saved with your artifact. Showing a cached copy.'
        : 'Saved with your artifact, so it survives a refresh of the page.';
      emit();
    }, function () {
      window.clearTimeout(loading);
      startLocal('Could not reach the saved list, so this browser is keeping it instead.');
    });

    store.write = function (id, body) { return collection.doc(String(id)).set(body); };
    store.erase = function (id) { return collection.doc(String(id)).delete(); };
    store.ready = store.ready || false;
  }

  store.write = function (id, body) {
    store.rows[id] = body; localWrite(store.rows); emit();
    return Promise.resolve();
  };
  store.erase = function (id) {
    delete store.rows[id]; localWrite(store.rows); emit();
    return Promise.resolve();
  };

  store.follow = function (player, note) {
    var body = {
      player_id: player.i,
      name: player.w,
      team: (teamById[player.t] || {}).short || '',
      position: (posById[player.p] || {}).short || '',
      price: player.c,
      note: note || '',
      added: new Date().toISOString().slice(0, 10)
    };
    if (store.mode === 'local') { return store.write(player.i, body); }
    store.rows[player.i] = body; emit();            // show it at once
    return store.write(player.i, body);
  };
  store.unfollow = function (id) {
    if (store.mode === 'local') { return store.erase(id); }
    delete store.rows[id]; emit();
    return store.erase(id);
  };
  store.onChange = function (fn) { store.listeners.push(fn); fn(store.rows); };

  // The capability resolves later than this script's first run, never within it.
  startLocal('');
  if (window.claude && typeof window.claude.use === 'function') {
    window.claude.use('db').then(function (db) {
      if (db) { startDb(db); }
    }, function () { /* keep the local list */ });
  }

  // ----------------------------------------------------------------- browser
  var els = {
    team: document.getElementById('f-team'),
    pos: document.getElementById('f-pos'),
    sort: document.getElementById('f-sort'),
    search: document.getElementById('f-search'),
    available: document.getElementById('f-available'),
    played: document.getElementById('f-played'),
    clear: document.getElementById('f-clear'),
    head: document.getElementById('browser-head'),
    body: document.getElementById('browser-body'),
    count: document.getElementById('browser-count')
  };
  if (!els.body) { return; }

  DATA.teams.forEach(function (t) {
    var o = document.createElement('option');
    o.value = String(t.id); o.textContent = t.name;
    els.team.appendChild(o);
  });
  DATA.positions.forEach(function (p) {
    var o = document.createElement('option');
    o.value = String(p.id); o.textContent = p.name;
    els.pos.appendChild(o);
  });
  DATA.columns.forEach(function (c, i) {
    var o = document.createElement('option');
    o.value = String(i); o.textContent = c.label;
    els.sort.appendChild(o);
  });
  var priceOpt = document.createElement('option');
  priceOpt.value = 'price'; priceOpt.textContent = 'Price';
  els.sort.appendChild(priceOpt);
  els.sort.value = '0';                              // total points

  var sortIndex = 0, sortDesc = true;

  var fixed = [
    { label: '', key: 'star' },
    { label: 'Player', key: 'name' },
    { label: 'Team', key: 'team' },
    { label: 'Pos', key: 'pos' },
    { label: 'Price', key: 'price', num: true }
  ];

  function buildHead() {
    els.head.textContent = '';
    fixed.forEach(function (c) {
      var th = document.createElement('th');
      th.textContent = c.label;
      if (c.num) { th.className = 'num'; }
      els.head.appendChild(th);
    });
    DATA.columns.forEach(function (c, i) {
      var th = document.createElement('th');
      th.textContent = c.label;
      th.className = 'num sortable' + (i === sortIndex ? ' sorted' + (sortDesc ? '' : ' asc') : '');
      th.title = c.key;
      th.addEventListener('click', function () {
        if (sortIndex === i) { sortDesc = !sortDesc; } else { sortIndex = i; sortDesc = true; }
        els.sort.value = String(i);
        buildHead(); render();
      });
      els.head.appendChild(th);
    });
  }

  function value(player, index) {
    var v = player.v[index];
    return (v === null || v === undefined) ? null : v;
  }

  function filtered() {
    var team = els.team.value, pos = els.pos.value;
    var q = (els.search.value || '').trim().toLowerCase();
    var list = DATA.players.filter(function (p) {
      if (team && String(p.t) !== team) { return false; }
      if (pos && String(p.p) !== pos) { return false; }
      if (els.available.checked && p.st !== 'a') { return false; }
      if (els.played.checked && !value(p, minutesIndex)) { return false; }
      if (q && p.w.toLowerCase().indexOf(q) < 0 && p.n.toLowerCase().indexOf(q) < 0) {
        return false;
      }
      return true;
    });
    var key = els.sort.value;
    list.sort(function (a, b) {
      var av, bv;
      if (key === 'price') { av = a.c; bv = b.c; }
      else { av = value(a, sortIndex); bv = value(b, sortIndex); }
      if (av === null) { av = -Infinity; }
      if (bv === null) { bv = -Infinity; }
      if (typeof av === 'string' || typeof bv === 'string') {
        av = String(av); bv = String(bv);
        return sortDesc ? bv.localeCompare(av) : av.localeCompare(bv);
      }
      return sortDesc ? bv - av : av - bv;
    });
    return list;
  }

  var minutesIndex = (function () {
    for (var i = 0; i < DATA.columns.length; i++) {
      if (DATA.columns[i].key === 'minutes') { return i; }
    }
    return 0;
  })();

  function render() {
    var list = filtered();
    var shown = list.slice(0, MAX_ROWS);
    var frag = document.createDocumentFragment();

    shown.forEach(function (p) {
      var tr = document.createElement('tr');

      var starCell = document.createElement('td');
      var star = document.createElement('button');
      star.type = 'button';
      star.className = 'star';
      star.setAttribute('aria-pressed', store.rows[p.i] ? 'true' : 'false');
      star.setAttribute('aria-label', 'Follow ' + p.w);
      star.title = store.rows[p.i] ? 'Following - press to stop' : 'Follow this player';
      star.textContent = store.rows[p.i] ? '★' : '☆';
      star.addEventListener('click', function () {
        if (store.rows[p.i]) { store.unfollow(p.i); } else { store.follow(p); }
      });
      starCell.appendChild(star);
      tr.appendChild(starCell);

      var nameCell = document.createElement('td');
      nameCell.className = 'team';
      var nm = document.createElement('span');
      nm.className = 'short';
      nm.textContent = p.w;
      nm.title = p.n;
      nameCell.appendChild(nm);
      if (p.d && (p.p === 1 || p.p === 2)) {
        var d = document.createElement('span');
        d.className = 'dmark small';
        d.textContent = 'D';
        d.title = 'Plays for one of the eight teams conceding fewest goals';
        nameCell.appendChild(document.createTextNode(' '));
        nameCell.appendChild(d);
      }
      if (p.st !== 'a' || (p.cp !== null && p.cp !== undefined && p.cp < 100)) {
        var warn = document.createElement('span');
        warn.className = 'flagwarn';
        warn.textContent = ' ' + (p.cp === null || p.cp === undefined ? 'OUT' : p.cp + '%');
        warn.title = p.news || 'Not fully available';
        nameCell.appendChild(warn);
      }
      tr.appendChild(nameCell);

      var teamCell = document.createElement('td');
      teamCell.className = 'mid quiet';
      teamCell.textContent = (teamById[p.t] || {}).short || '';
      tr.appendChild(teamCell);

      var posCell = document.createElement('td');
      posCell.className = 'mid quiet';
      posCell.textContent = (posById[p.p] || {}).short || '';
      tr.appendChild(posCell);

      var priceCell = document.createElement('td');
      priceCell.className = 'num';
      priceCell.textContent = '£' + p.c.toFixed(1) + 'm';
      tr.appendChild(priceCell);

      DATA.columns.forEach(function (c, i) {
        var td = document.createElement('td');
        td.className = 'num' + (i === sortIndex ? ' strong' : '');
        var v = value(p, i);
        td.textContent = (v === null) ? '–' : v;
        tr.appendChild(td);
      });

      frag.appendChild(tr);
    });

    els.body.textContent = '';
    els.body.appendChild(frag);
    els.count.textContent = list.length === shown.length
      ? list.length + ' players'
      : 'Showing the first ' + shown.length + ' of ' + list.length
        + ' players - narrow the filters or sort to see others';
  }

  [els.team, els.pos, els.available, els.played].forEach(function (el) {
    el.addEventListener('change', render);
  });
  els.sort.addEventListener('change', function () {
    if (els.sort.value !== 'price') { sortIndex = parseInt(els.sort.value, 10); }
    sortDesc = true;
    buildHead(); render();
  });
  var searchTimer;
  els.search.addEventListener('input', function () {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(render, 150);
  });
  els.clear.addEventListener('click', function () {
    els.team.value = ''; els.pos.value = ''; els.search.value = '';
    els.available.checked = false; els.played.checked = false;
    els.sort.value = '0'; sortIndex = 0; sortDesc = true;
    buildHead(); render();
  });

  // ---------------------------------------------------------------- watchlist
  var followBody = document.getElementById('follow-body');
  var followWrap = document.getElementById('follow-wrap');
  var followEmpty = document.getElementById('follow-empty');
  var followNote = document.getElementById('follow-note');
  var followCount = document.getElementById('follow-count');

  function renderFollow(rows) {
    var ids = Object.keys(rows);
    if (followCount) { followCount.textContent = ids.length ? String(ids.length) : ''; }
    if (!followBody) { return; }

    followWrap.hidden = ids.length === 0;
    followEmpty.hidden = ids.length > 0;
    followNote.textContent = ids.length ? store.note : '';

    ids.sort(function (a, b) {
      return (rows[b].added || '').localeCompare(rows[a].added || '');
    });

    var frag = document.createDocumentFragment();
    ids.forEach(function (id) {
      var row = rows[id];
      var live = playerById[row.player_id] || null;
      var tr = document.createElement('tr');

      function cell(text, cls) {
        var td = document.createElement('td');
        if (cls) { td.className = cls; }
        td.textContent = text;
        tr.appendChild(td);
        return td;
      }

      var nameCell = cell('', 'team');
      var nm = document.createElement('span');
      nm.className = 'short';
      nm.textContent = row.name;
      nameCell.appendChild(nm);

      cell(row.team || '', 'mid quiet');
      cell(row.position || '', 'mid quiet');
      cell('£' + (live ? live.c : row.price).toFixed(1) + 'm', 'num');
      cell(live ? String(value(live, 0)) : '–', 'num strong');
      cell(live ? String(value(live, 2)) : '–', 'num');

      var noteCell = document.createElement('td');
      var input = document.createElement('input');
      input.type = 'text';
      input.className = 'note-input';
      input.value = row.note || '';
      input.placeholder = 'why you are watching';
      input.setAttribute('aria-label', 'Note about ' + row.name);
      var noteTimer;
      input.addEventListener('input', function () {
        window.clearTimeout(noteTimer);
        noteTimer = window.setTimeout(function () {
          var body = {};
          Object.keys(row).forEach(function (k) { body[k] = row[k]; });
          body.note = input.value;
          store.write(id, body);
        }, 600);
      });
      noteCell.appendChild(input);
      tr.appendChild(noteCell);

      cell(row.added || '', 'quiet');

      var actionCell = document.createElement('td');
      var remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'copy-btn';
      remove.textContent = 'Remove';
      remove.addEventListener('click', function () { store.unfollow(id); });
      actionCell.appendChild(remove);
      tr.appendChild(actionCell);

      frag.appendChild(tr);
    });

    followBody.textContent = '';
    followBody.appendChild(frag);
  }

  store.onChange(function (rows) {
    renderFollow(rows);
    render();            // keep the stars in the browser in step
  });

  buildHead();
  render();
})();

// Click-to-sort for any server-rendered table marked .sortable-table.
// Numbers are read out of the cell text, so prices, percentages and the
// en-dash used for "no value" all sort sensibly.
(function () {
  'use strict';

  function numberIn(text) {
    var cleaned = String(text)
      .replace(/\u2212/g, '-')          // minus sign
      .replace(/[^0-9.\-]/g, '');
    if (!cleaned || cleaned === '-' || cleaned === '.') { return null; }
    var n = parseFloat(cleaned);
    return isNaN(n) ? null : n;
  }

  function sortTable(table, index, desc) {
    var body = table.tBodies[0];
    if (!body) { return; }
    var rows = Array.prototype.slice.call(body.rows);
    var numeric = rows.some(function (r) {
      return r.cells[index] && numberIn(r.cells[index].textContent) !== null;
    });

    rows.sort(function (a, b) {
      var at = a.cells[index] ? a.cells[index].textContent.trim() : '';
      var bt = b.cells[index] ? b.cells[index].textContent.trim() : '';
      if (numeric) {
        var an = numberIn(at), bn = numberIn(bt);
        if (an === null && bn === null) { return 0; }
        if (an === null) { return 1; }      // blanks always last
        if (bn === null) { return -1; }
        return desc ? bn - an : an - bn;
      }
      return desc ? bt.localeCompare(at) : at.localeCompare(bt);
    });

    rows.forEach(function (r) { body.appendChild(r); });
  }

  Array.prototype.forEach.call(
    document.querySelectorAll('table.sortable-table'),
    function (table) {
      var head = table.tHead && table.tHead.rows[table.tHead.rows.length - 1];
      if (!head) { return; }
      var state = { index: -1, desc: true };

      Array.prototype.forEach.call(head.cells, function (th, index) {
        if (th.dataset.nosort !== undefined) { return; }
        th.classList.add('sortable');
        th.tabIndex = 0;
        th.setAttribute('role', 'button');
        var label = th.textContent.trim() || 'this column';
        th.title = 'Sort by ' + label;

        function apply() {
          if (state.index === index) { state.desc = !state.desc; }
          else { state.index = index; state.desc = true; }
          Array.prototype.forEach.call(head.cells, function (c) {
            c.classList.remove('sorted', 'asc');
          });
          th.classList.add('sorted');
          if (!state.desc) { th.classList.add('asc'); }
          sortTable(table, index, state.desc);
        }

        th.addEventListener('click', apply);
        th.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); apply(); }
        });
      });
    });
})();
