(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var csrf = ($('meta[name="csrf-token"]') || {}).content || "";
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  // ---------- API helper ----------
  function api(path, options) {
    options = options || {};
    var init = { method: options.method || "GET", headers: {}, credentials: "same-origin" };
    if (options.body !== undefined) {
      init.method = "POST";
      init.headers["Content-Type"] = "application/json";
      init.headers["X-CSRF-Token"] = csrf;
      init.body = JSON.stringify(options.body);
    }
    return fetch(path, init).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) throw new Error(data.error || "Something went wrong. Please try again.");
        return data;
      });
    }, function () { throw new Error("Cannot reach the server. Check your connection."); });
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;  // textContent, never innerHTML: safe against XSS
    return e;
  }

  // ---------- 18/14: UTM capture (kept in this tab only, sent with feedback) ----------
  var utm = store.get("utm", {});
  (function () {
    var params = new URLSearchParams(location.search);
    ["utm_source", "utm_medium", "utm_campaign"].forEach(function (k) {
      var v = params.get(k);
      if (v && /^[A-Za-z0-9_.\-]{1,60}$/.test(v)) utm[k] = v;
    });
    try { sessionStorage.setItem("utm", JSON.stringify(utm)); } catch (e) {}
  })();

  // ---------- 2: cookie notice ----------
  var cookie = $("#cookie-banner");
  if (cookie && !store.get("cookie_ok", false)) {
    cookie.hidden = false;
    $("#cookie-ok").addEventListener("click", function () { store.set("cookie_ok", true); cookie.hidden = true; });
  }

  // ---------- 17: confirmation modal ----------
  var confirmDlg = $("#confirm-dialog");
  function confirmAction(message) {
    return new Promise(function (resolve) {
      if (!confirmDlg || !confirmDlg.showModal) { resolve(window.confirm(message)); return; }
      $("#confirm-message").textContent = message;
      confirmDlg.addEventListener("close", function onClose() {
        confirmDlg.removeEventListener("close", onClose);
        resolve(confirmDlg.returnValue === "ok");
      });
      confirmDlg.showModal();
    });
  }

  // ---------- filters ----------
  var genreSel = $("#genre"), minSel = $("#min-ratings"), countSel = $("#count");
  function filterQuery() {
    var q = new URLSearchParams({ n: countSel.value, min_ratings: minSel.value });
    if (genreSel.value !== "Any") q.set("genre", genreSel.value);
    return q;
  }
  api("/api/meta").then(function (meta) {
    meta.genres.forEach(function (g) { var o = el("option", "", g); o.value = g; genreSel.appendChild(o); });
  }).catch(function () {});

  // ---------- results rendering ----------
  var lastText = { similar: "", taste: "", top: "" };
  function skeletons(container) {
    container.replaceChildren();
    for (var i = 0; i < 4; i++) container.appendChild(el("div", "skeleton"));  // 6: loading animation
    container.setAttribute("aria-busy", "true");
  }
  function showError(container, key, message) {
    container.removeAttribute("aria-busy");
    container.replaceChildren(el("div", "error-box", message));
    lastText[key] = "";
    setCopyVisible(key, false);
  }
  function setCopyVisible(key, visible) {
    var b = $('.copy-btn[data-copy-target="' + key + '"]');
    if (b) b.hidden = !visible;
  }
  function renderResults(container, key, rows, opts) {
    opts = opts || {};
    container.removeAttribute("aria-busy");
    container.replaceChildren();
    if (!rows.length) {
      container.appendChild(el("div", "empty", "No movies match these filters. Try relaxing them."));
      lastText[key] = ""; setCopyVisible(key, false);
      return;
    }
    var max = opts.max || 1;
    rows.forEach(function (r, i) {
      var card = el("article", "movie");
      card.appendChild(el("div", "rank", String(i + 1)));
      var info = el("div");
      info.appendChild(el("h3", "", r.title));
      info.appendChild(el("div", "genres", r.genres));
      if (r.why) info.appendChild(el("p", "why", r.why));
      card.appendChild(info);

      var pct = Math.max(0, Math.min(100, Math.round((r.score / max) * 100)));
      var col = el("div", "score-col");
      var label = el("div", "meter-label");
      label.appendChild(el("span", "", opts.label || "Similarity"));
      label.appendChild(el("strong", "", opts.raw ? r.score.toFixed(2) : pct + "%"));
      col.appendChild(label);
      var meter = el("div", "meter");
      meter.setAttribute("role", "img");
      meter.setAttribute("aria-label", (opts.label || "Similarity") + " " + pct + " percent");
      var fill = el("span"); fill.style.width = pct + "%";
      meter.appendChild(fill); col.appendChild(meter);
      col.appendChild(el("div", "stars", "⭐ " + r.avg_rating.toFixed(2) + " · " + r.n_ratings.toLocaleString() + " ratings"));
      card.appendChild(col);
      container.appendChild(card);
    });
    lastText[key] = rows.map(function (r, i) {
      return (i + 1) + ". " + r.title + " (" + r.genres + ")";
    }).join("\n");
    setCopyVisible(key, true);
  }

  // ---------- 9: copy button ----------
  document.querySelectorAll(".copy-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = lastText[btn.dataset.copyTarget] || "";
      var done = function () { var o = btn.textContent; btn.textContent = "Copied ✓"; setTimeout(function () { btn.textContent = o; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () {});
      else { var t = el("textarea"); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand("copy"); done(); } catch (e) {} t.remove(); }
    });
  });

  // ---------- 3: search with suggestions ----------
  function attachSuggest(input, list, onPick) {
    var items = [], active = -1, timer = null;
    function close() { list.hidden = true; input.setAttribute("aria-expanded", "false"); active = -1; }
    function highlight(i) {
      Array.prototype.forEach.call(list.children, function (li, idx) { li.setAttribute("aria-selected", String(idx === i)); });
      active = i;
    }
    function render() {
      list.replaceChildren();
      items.forEach(function (title, i) {
        var li = el("li", "", title);
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", "false");
        li.addEventListener("mousedown", function (e) { e.preventDefault(); pick(title); });
        list.appendChild(li);
      });
      list.hidden = !items.length;
      input.setAttribute("aria-expanded", String(!!items.length));
    }
    function pick(title) { input.value = title; close(); onPick(title); }
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var q = input.value.trim();
      if (q.length < 2) { items = []; render(); return; }
      timer = setTimeout(function () {
        api("/api/search?q=" + encodeURIComponent(q)).then(function (d) {
          if (input.value.trim() === q) { items = d.suggestions; render(); }
        }).catch(close);
      }, 200);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" && items.length) { e.preventDefault(); highlight((active + 1) % items.length); }
      else if (e.key === "ArrowUp" && items.length) { e.preventDefault(); highlight((active - 1 + items.length) % items.length); }
      else if (e.key === "Enter" && active >= 0) { e.preventDefault(); pick(items[active]); }
      else if (e.key === "Escape") close();
    });
    input.addEventListener("blur", function () { setTimeout(close, 120); });
  }

  // ---------- tabs ----------
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  var topLoaded = false;
  function showTab(name) {
    tabs.forEach(function (t) {
      var on = t.dataset.tab === name;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      $("#panel-" + t.dataset.tab).hidden = !on;
    });
    if (name === "top") loadTop();
  }
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { showTab(t.dataset.tab); });
    t.addEventListener("keydown", function (e) {
      var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) { var n = tabs[(i + d + tabs.length) % tabs.length]; n.focus(); showTab(n.dataset.tab); }
    });
  });
  document.querySelectorAll("[data-tab-link]").forEach(function (a) {
    a.addEventListener("click", function () { showTab(a.dataset.tabLink); });
  });

  // ---------- similar movies ----------
  var searchInput = $("#search-input"), resultsSimilar = $("#results-similar");
  function runSimilar(title) {
    showTab("similar");
    skeletons(resultsSimilar);
    api("/api/recommend?title=" + encodeURIComponent(title) + "&" + filterQuery()).then(function (d) {
      $("#similar-title").textContent = "Because you liked " + d.query;
      renderResults(resultsSimilar, "similar", d.results);
      $("#recommend").scrollIntoView({ behavior: "smooth" });
    }).catch(function (e) { showError(resultsSimilar, "similar", e.message); });
  }
  attachSuggest(searchInput, $("#suggestions"), runSimilar);
  $("#search-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var q = searchInput.value.trim();
    if (q) runSimilar(q);
  });

  // ---------- top rated ----------
  var resultsTop = $("#results-top");
  function loadTop() {
    skeletons(resultsTop);
    api("/api/top?" + filterQuery()).then(function (d) {
      renderResults(resultsTop, "top", d.results, { label: "Weighted rating", max: 5, raw: true });
    }).catch(function (e) { showError(resultsTop, "top", e.message); });
  }

  // ---------- taste profile (stored in this browser only) ----------
  var profile = store.get("profile", {});
  var tasteList = $("#taste-list"), tasteEmpty = $("#taste-empty"), resultsTaste = $("#results-taste");
  function renderProfile() {
    tasteList.replaceChildren();
    var titles = Object.keys(profile);
    tasteEmpty.hidden = titles.length > 0;
    titles.forEach(function (title) {
      var li = el("li");
      li.appendChild(el("span", "", title));
      var sel = el("select"); sel.setAttribute("aria-label", "Your rating for " + title);
      [5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5].forEach(function (v) {
        var o = el("option", "", "★ " + v); o.value = String(v); if (Number(profile[title]) === v) o.selected = true; sel.appendChild(o);
      });
      sel.addEventListener("change", function () { profile[title] = Number(sel.value); store.set("profile", profile); });
      var rm = el("button", "btn ghost small", "Remove"); rm.type = "button";
      rm.addEventListener("click", function () { delete profile[title]; store.set("profile", profile); renderProfile(); });
      var right = el("span", "row"); right.appendChild(sel); right.appendChild(rm);
      li.appendChild(right); tasteList.appendChild(li);
    });
  }
  renderProfile();
  attachSuggest($("#taste-input"), $("#taste-suggestions"), function (title) {
    if (Object.keys(profile).length >= 30) { showError(resultsTaste, "taste", "You can rate up to 30 movies."); return; }
    profile[title] = profile[title] || 4; store.set("profile", profile); renderProfile();
    $("#taste-input").value = "";
  });
  $("#taste-go").addEventListener("click", function () {
    if (!Object.keys(profile).length) { showError(resultsTaste, "taste", "Add at least one movie first."); return; }
    skeletons(resultsTaste);
    api("/api/profile?" + filterQuery(), { body: { ratings: profile } }).then(function (d) {
      renderResults(resultsTaste, "taste", d.results);
    }).catch(function (e) { showError(resultsTaste, "taste", e.message); });
  });
  $("#taste-clear").addEventListener("click", function () {
    if (!Object.keys(profile).length) return;
    confirmAction("Remove all movies from your taste profile?").then(function (ok) {
      if (ok) { profile = {}; store.set("profile", profile); renderProfile(); resultsTaste.replaceChildren(); setCopyVisible("taste", false); }
    });
  });

  // re-run the visible list when filters change
  [genreSel, minSel, countSel].forEach(function (s) {
    s.addEventListener("change", function () {
      var active = (tabs.filter(function (t) { return t.getAttribute("aria-selected") === "true"; })[0] || {}).dataset;
      if (active && active.tab === "top") loadTop();
      else if (active && active.tab === "similar" && searchInput.value.trim()) runSimilar(searchInput.value.trim());
    });
  });

  // ---------- 20/15/16: contact dialog with success + error states ----------
  var dlg = $("#contact-dialog"), form = $("#contact-form");
  if (dlg && form) {
  var errBox = $("#contact-error"), okBox = $("#contact-success"), fields = $("#contact-fields");
  function openContact() {
    form.reset(); errBox.hidden = true; okBox.hidden = true; fields.hidden = false;
    $("#contact-submit").disabled = false; $("#contact-submit").textContent = "Send";
    if (dlg.showModal) dlg.showModal();
  }
  $("#contact-fab").addEventListener("click", openContact);
  $("#nav-contact").addEventListener("click", function (e) { e.preventDefault(); openContact(); });
  $("#contact-cancel").addEventListener("click", function () { dlg.close(); });
  $("#contact-close").addEventListener("click", function () { dlg.close(); });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    errBox.hidden = true;
    var data = {
      name: $("#c-name").value.trim(), email: $("#c-email").value.trim(), message: $("#c-message").value.trim(),
      website: form.querySelector('input[name="website"]').value, utm_source: utm.utm_source, utm_medium: utm.utm_medium, utm_campaign: utm.utm_campaign
    };
    if (!data.name || !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(data.email) || data.message.length < 10) {
      errBox.textContent = "Please enter your name, a valid email and a message of at least 10 characters.";
      errBox.hidden = false; return;
    }
    var btn = $("#contact-submit"); btn.disabled = true; btn.textContent = "Sending…";
    api("/api/feedback", { body: data }).then(function () {
      fields.hidden = true; okBox.hidden = false;
    }).catch(function (err) {
      errBox.textContent = err.message; errBox.hidden = false;
      btn.disabled = false; btn.textContent = "Send";
    });
  });
  }
})();
