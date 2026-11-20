(function(){
  var LANG = {
    en:{code:'EN',name:'English'}, it:{code:'IT',name:'Italiano'}, de:{code:'DE',name:'Deutsch'},
    es:{code:'ES',name:'Español'}, fr:{code:'FR',name:'Français'}, pt:{code:'PT',name:'Português'},
    nl:{code:'NL',name:'Nederlands'}, pl:{code:'PL',name:'Polski'}, fi:{code:'FI',name:'Suomi'},
    sv:{code:'SV',name:'Svenska'}, da:{code:'DA',name:'Dansk'}, hu:{code:'HU',name:'Magyar'},
    zh:{code:'ZH',name:'中文'}, ko:{code:'KO',name:'한국어'}, ja:{code:'JA',name:'日本語'}
  };
  var ORDER = ['en','it','de','es','fr','pt','nl','pl','fi','sv','da','hu','zh','ko'];
  var NS = 'http://www.w3.org/2000/svg';
  var state = { lang:'all', team:'all', kind:'all', src:'all', q:'', view:'latest', data:null, circuits:{}, teams:{}, teamOrder:[], season:null, standTab:'d' };
  function teamTag(key, count){
    var t = state.teams[key]; if (!t) return null;
    var b = mk('button','teamtag'); b.type = 'button';
    b.setAttribute('aria-pressed', String(state.team === key));
    var dot = mk('span','tdot'); dot.style.setProperty('--t1', t.c1); dot.style.setProperty('--t2', t.c2); dot.style.setProperty('--t3', t.c3 || t.c2);
    b.appendChild(dot);
    b.appendChild(document.createTextNode(t.en + (count != null ? ' ' + count : '')));
    b.title = t.en + '（' + t.name + '）の記事だけを表示';
    b.addEventListener('click', function(){ state.team = state.team === key ? 'all' : key; renderAll(); });
    return b;
  }
  function tagsFor(a){
    var ks = (a.teams || []).filter(function(k){ return state.teams[k]; });
    if (!ks.length) return null;
    var w = mk('div','teamtags');
    ks.forEach(function(k){ w.appendChild(teamTag(k)); });
    return w;
  }
  // outlet colour = the flag of the outlet's country (region in articles.json)
  var FLAG = {
    '日本':'jp','イギリス':'gb','アメリカ':'us','ドイツ':'de','イタリア':'it','スペイン':'es','フランス':'fr',
    'オランダ':'nl','ブラジル':'br','アルゼンチン':'ar','メキシコ':'mx','オーストラリア':'au','ベルギー':'be',
    'オーストリア':'at','スイス':'ch','ポルトガル':'pt','カナダ':'ca','ポーランド':'pl','フィンランド':'fi',
    'デンマーク':'dk','スウェーデン':'se','ノルウェー':'no','モナコ':'mc','インドネシア':'mc','中国':'cn',
    '韓国':'kr','インド':'in','ニュージーランド':'nz','アイルランド':'ie','ハンガリー':'hu','チェコ':'cz',
    'コロンビア':'co','チリ':'cl','タイ':'th','シンガポール':'sg','アラブ首長国連邦':'ae','サウジアラビア':'sa',
    'トルコ':'tr','ロシア':'ru','ウクライナ':'ua','ギリシャ':'gr','ルーマニア':'ro','南アフリカ':'za','台湾':'tw','香港':'hk','カタール':'qa'
  };
  function colorOf(src){ var r = state.srcRegion && state.srcRegion[src]; return (r && FLAG[r]) || 'xx'; }
  function unq(s){ return String(s || '').replace(/^["“„«»\s]+|["”«»\s]+$/g, ''); }
  function slug(src){ return 'src-' + src.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  function badge(src){ var b = mk('span','srcbadge', src); b.setAttribute('data-c', colorOf(src)); return b; }
  var el = function(id){ return document.getElementById(id); };

  function mk(tag, cls, text){
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function sv(tag, attrs){
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function jst(iso, withTime){
    try{
      var o = { timeZone:'Asia/Tokyo', month:'numeric', day:'numeric' };
      if (withTime){ o.hour = '2-digit'; o.minute = '2-digit'; o.hour12 = false; }
      return new Intl.DateTimeFormat('ja-JP', o).format(new Date(iso));
    }catch(e){ return ''; }
  }
  function ago(iso){
    var d = (Date.now() - new Date(iso).getTime()) / 60000;
    if (isNaN(d)) return '';
    if (d < 60) return Math.max(1, Math.round(d)) + '分前';
    if (d < 60*24) return Math.round(d/60) + '時間前';
    if (d < 60*24*7) return Math.round(d/1440) + '日前';
    return jst(iso, false);
  }
  function langName(k){ return (LANG[k] && LANG[k].name) || String(k).toUpperCase(); }
  function langCode(k){ return (LANG[k] && LANG[k].code) || String(k).toUpperCase(); }
  /* click counting (GoatCounter, public site only; no cookies) */
  document.addEventListener('click', function(e){
    var link = e.target.closest && e.target.closest('a[href^="http"]');
    if (!link || !window.goatcounter || !window.goatcounter.count) return;
    var art = (state.byUrl || {})[link.href] || (state.noteByUrl || {})[link.href];
    if (!art) return;
    try { window.goatcounter.count({ path:'click/' + art.id, title:art.source + ' | ' + art.title, event:true }); } catch(err){}
  }, true);
  /* article titles open our own summary page first; the original is one tap away from there */
  function artLink(a, text, cls){
    if (a && !a.isNote && /^[a-z0-9][a-z0-9-]*$/.test(a.id || '')){ var l = mk('a', cls, text); l.href = '/news/' + a.id + '/'; return l; }
    return extLink(a.url, text, cls);
  }
  function extLink(url, text, cls){
    var a = mk('a', cls, text);
    a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer';
    return a;
  }
  function timeEl(iso){
    var t = mk('time', null, ago(iso)); t.dateTime = iso; t.title = jst(iso, true) + '（日本時間）';
    return t;
  }
  function circuitSvg(c, big){
    var s = sv('svg', { viewBox:'0 0 100 100', preserveAspectRatio:'xMidYMid meet' });
    s.appendChild(sv('path', { 'class':'trk-under', d:c.path, 'stroke-width': big ? 9 : 7 }));
    s.appendChild(sv('path', { 'class':'trk', d:c.path, 'stroke-width': big ? 3.2 : 2.4 }));
    s.appendChild(sv('circle', { 'class':'trk-start', cx:c.start[0], cy:c.start[1], r: big ? 2.6 : 3.4 }));
    return s;
  }

  function trending(all){
    var weekAgo = Date.now() - 7 * 864e5, g = {};
    all.forEach(function(a){
      if (!a.topic || new Date(a.published).getTime() < weekAgo) return;
      (g[a.topic] = g[a.topic] || []).push(a);
    });
    var best = null;
    Object.keys(g).forEach(function(k){
      var items = g[k], srcs = {};
      items.forEach(function(a){ srcs[a.source] = 1; });
      var n = Object.keys(srcs).length;
      var newest = Math.max.apply(null, items.map(function(a){ return new Date(a.published).getTime(); }));
      if (n >= 2 && (!best || n > best.n || (n === best.n && newest > best.newest))) best = { key:k, items:items, n:n, newest:newest };
    });
    return best;
  }
  var LANG_JA = { en:'英語', it:'イタリア語', de:'ドイツ語', es:'スペイン語', fr:'フランス語', pt:'ポルトガル語', nl:'オランダ語', pl:'ポーランド語', fi:'フィンランド語', sv:'スウェーデン語', da:'デンマーク語', hu:'ハンガリー語', zh:'中国語', ko:'韓国語', ja:'日本語' };
  var SCOPE_TAG = { country:'国別の傾向', outlet:'1媒体', wire:'通信社', official:'公式', others:'単独媒体' };
  var ICON = {
    wire:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.6 3.8 5.6 3.8 9s-1.2 6.4-3.8 9c-2.6-2.6-3.8-5.6-3.8-9S9.4 5.6 12 3z"/></svg>',
    official:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 21V4"/><path d="M5 4h6v3h8v9h-6v-3H5"/></svg>',
    others:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="4" width="18" height="5" rx="1.5"/><rect x="3" y="11" width="18" height="5" rx="1.5"/><path d="M6 20h12"/></svg>'
  };
  function lensFlag(g){
    var f = mk('span','lens-flag');
    if (g.scope === 'country' || g.scope === 'outlet'){ f.setAttribute('data-c', FLAG[g.region] || 'xx'); }
    else { f.className = 'lens-flag icon'; f.innerHTML = ICON[g.scope] || ICON.others; }
    return f;
  }
  function stepHead(n, text, en, small){
    var h = mk('h2','tw-h'); h.appendChild(document.createTextNode(text));
    if (en) h.appendChild(mk('span','en', en));
    if (small) h.appendChild(mk('small', null, small));
    return h;
  }
  function twRow(a){
    var li = mk('li'); li.setAttribute('data-c', colorOf(a.source));
    var m = mk('div','m'); m.appendChild(kindChip(a)); m.appendChild(badge(a.source)); m.appendChild(timeEl(a.published)); li.appendChild(m);
    li.appendChild(artLink(a, a.title, 't'));
    if (a.summary) li.appendChild(mk('p', null, a.summary));
    return li;
  }
  function renderTrending(t){
    var info = (state.data.topics || {})[t.key] || {};
    var lens = info.lens && info.lens.groups && info.lens.groups.length ? info.lens : null;
    var byId = {}; state.all.forEach(function(a){ byId[a.id] = a; });
    var lead = t.items.filter(function(a){ return a.featured; })[0] || t.items[0];
    var withMap = t.items.filter(function(a){ return a.circuit && state.circuits[a.circuit]; })[0];
    var ha = el('hero-art'); ha.textContent = ''; ha.removeAttribute('data-c');
    var plate = mk('div','plate');
    if (withMap){
      var c = state.circuits[withMap.circuit];
      var s = circuitSvg(c, true); s.setAttribute('role','img'); s.setAttribute('aria-label', c.name + 'のコース図');
      plate.appendChild(s); ha.appendChild(plate);
      var lab = mk('div','circuit-label'); lab.appendChild(mk('b', null, c.name)); lab.appendChild(mk('span', null, c.gp)); ha.appendChild(lab);
    } else { plate.appendChild(mk('span','catword', lead.cat || 'NEWS')); ha.appendChild(plate); }

    var media = t.items.filter(function(a){ return a.kind !== 'fan' && a.kind !== 'voice'; });
    var mediaSrc = {}; media.forEach(function(a){ mediaSrc[a.source] = 1; });
    var nMedia = Object.keys(mediaSrc).length || t.n;
    var weekAgo = Date.now() - 7 * 864e5;
    var circ = withMap && withMap.circuit;
    function near(a){ return a.topic === t.key || (circ && a.circuit === circ && new Date(a.published).getTime() >= weekAgo); }
    var techs = state.all.filter(function(a){ return a.kind === 'tech' && near(a); })
      .sort(function(a,b){ return (b.topic === t.key) - (a.topic === t.key) || new Date(b.published) - new Date(a.published); }).slice(0, 3);
    var fans = state.all.filter(function(a){ return a.kind === 'fan' && near(a); })
      .sort(function(a,b){ return (b.topic === t.key) - (a.topic === t.key) || new Date(b.published) - new Date(a.published); }).slice(0, 3);

    var box = el('hero'); box.textContent = '';
    var chips = mk('div','chips');
    chips.appendChild(mk('span','chip-feature','今週の注目'));
    chips.appendChild(mk('span','chip-cat','世界の' + nMedia + '媒体が報道'));
    box.appendChild(chips);

    var stepNo = 0;

    /* 1. facts */
    stepNo++;
    var facts = mk('div','tw-sec'); facts.id = 'tw-facts';
    var pick = t.items.filter(function(a){ return a.featured; })[0] || t.items.filter(function(a){ return a.kind === 'news' || a.kind === 'tech'; }).sort(function(a,b){ return new Date(a.published) - new Date(b.published); })[0] || lead;
    var h1 = mk('h2'); h1.id = 'hero-title'; h1.className = 'hero-h';
    h1.appendChild(artLink(pick, info.title || pick.title));
    facts.appendChild(h1);
    box.appendChild(facts);

    /* 2. world articles */
    stepNo++;
    var arts = mk('section','tw-sec'); arts.id = 'tw-articles';
    arts.appendChild(stepHead(stepNo, '世界の記事', null, nMedia + '媒体 · ' + media.length + '本'));
    var ul = mk('ul','trend-list tw-list');
    var TL_FIRST = wide.matches ? 3 : 4;
    media.slice().sort(function(a,b){ return new Date(b.published) - new Date(a.published); }).forEach(function(a, i){
      var li = mk('li'); li.setAttribute('data-c', colorOf(a.source));
      if (i >= TL_FIRST) li.classList.add('cut');
      var top = mk('div','tl-top');
      top.appendChild(badge(a.source));
      if (a.region) top.appendChild(mk('span','dot rgn', a.region));
      top.appendChild(mk('span','dot', LANG_JA[a.lang] || langName(a.lang)));
      if (a.lens && a.lens.type) top.appendChild(mk('span','dot', a.lens.type));
      li.appendChild(top);
      var tt2 = artLink(a, a.title, 'tl-title');
      { var kt = kindChip(a); kt.style.marginRight = '6px'; tt2.insertBefore(kt, tt2.firstChild); }
      li.appendChild(tt2);
      if (a.lens && (a.lens.lead || a.lens.focus)){
        var an = mk('div','tl-angle'); an.appendChild(mk('b', null, '主要焦点'));
        an.appendChild(document.createTextNode([a.lens.lead, a.lens.focus].filter(Boolean).join('／')));
        li.appendChild(an);
      }
      if (a.provider){
        var pv = mk('div','tl-prov');
        pv.appendChild(document.createTextNode('掲載：')); pv.appendChild(mk('b', null, a.source));
        pv.appendChild(document.createTextNode('　記事提供：')); pv.appendChild(mk('b', null, a.provider));
        li.appendChild(pv);
      }
      ul.appendChild(li);
    });
    arts.appendChild(ul);
    arts.hidden = true;
    var tlCut = ul.querySelectorAll('li.cut').length;
    if (tlCut){
      var tm = mk('button','feed-more tl-more', 'ほかの媒体の記事をもっと見る（残り' + tlCut + '本）'); tm.type = 'button';
      tm.addEventListener('click', function(){ [].forEach.call(ul.querySelectorAll('li.cut'), function(x){ x.classList.remove('cut'); }); tm.parentNode.removeChild(tm); });
      arts.appendChild(tm);
    }

    /* 3. world media lens: only the 総評 guide (owner's decision, 3 Oct 2026) */
    if (lens && (lens.guide || []).length){
      stepNo++;
      var ls = mk('section','tw-sec lens'); ls.id = 'tw-lens';
      // the line from 今週の注目 ends at the 総評 button itself (owner's decision, 3 Oct 2026)
      ls.appendChild(mk('p','lv-link','↓ このニュースを、世界はどう伝えた？'));
      var lh = mk('h2','tw-h tw-h-lens'); lh.appendChild(mk('span','tw-dot')); ls.appendChild(lh);
      // the 4-axis table (主役・焦点・原因の説明・見出しの強調点) was removed (owner's decision, 3 Oct 2026); only the 総評 guide is shown
      // 総評：読みたいことで選ぶなら (owner's choice 案3, 3 Oct 2026). Shown even when the table is closed.
      var GD = (lens.guide || []).filter(function(x){ return x && x.want && (x.ids || []).some(function(id){ return byId[id]; }); });
      if (GD.length){
        var vb = mk('div','lens-verdict'); vb.id = 'lens-guide'; vb.hidden = true;
        var ul2 = mk('ul');
        var vbt = mk('button','lv-btn'); vbt.type = 'button'; vbt.setAttribute('aria-expanded','false'); vbt.setAttribute('aria-controls','lens-guide');
        var vbl = mk('span', null, '総評：読みたいことで選ぶ'); vbl.appendChild(mk('small', null, GD.length + 'つの切り口から、記事を選べます')); vbt.appendChild(vbl);
        var vpm = mk('span','pm','+'); vbt.appendChild(vpm);
        vbt.addEventListener('click', function(){ var op = vb.hidden; vb.hidden = !op; vbt.setAttribute('aria-expanded', String(op)); vpm.textContent = op ? '−' : '+'; });
        lh.appendChild(vbt);
        GD.forEach(function(x){
          var li2 = mk('li'); li2.appendChild(mk('b', null, x.want));
          var sp = mk('span'); var seen2 = {};
          (x.ids || []).map(function(id){ return byId[id]; }).filter(Boolean).forEach(function(a, n){
            if (seen2[a.source]) return; seen2[a.source] = 1;
            if (n) sp.appendChild(document.createTextNode('・'));
            var lk = artLink(a, a.source); lk.title = a.title; sp.appendChild(lk);
          });
          if (x.note) sp.appendChild(mk('small', null, x.note));
          li2.appendChild(sp); ul2.appendChild(li2);
        });
        vb.appendChild(ul2); ls.appendChild(vb);
      }
      box.appendChild(ls);
    }

    var teams = {}; t.items.forEach(function(a){ (a.teams || []).forEach(function(k){ teams[k] = 1; }); });
  }

  function renderHubArt(key){
    var ha = el('hero-art'); if (!ha) return; ha.textContent = ''; ha.removeAttribute('data-c');
    var c = key && state.circuits[key], plate = mk('div','plate');
    if (c){
      var s = circuitSvg(c, true); s.setAttribute('role','img'); s.setAttribute('aria-label', c.name + 'のコース図');
      plate.appendChild(s); ha.appendChild(plate);
      var lab = mk('div','circuit-label'); lab.appendChild(mk('b', null, c.name)); lab.appendChild(mk('span', null, c.gp)); ha.appendChild(lab);
    } else { plate.appendChild(mk('span','catword', 'TOPIC')); ha.appendChild(plate); }
  }
  function renderHero(a){
    var ha = el('hero-art'); ha.textContent = '';
    ha.setAttribute('data-c', colorOf(a.source));
    var c = a.circuit && state.circuits[a.circuit];
    var plate = mk('div','plate');
    if (c){
      var s = circuitSvg(c, true);
      s.setAttribute('role','img'); s.setAttribute('aria-label', c.name + 'のコース図');
      plate.appendChild(s);
      ha.appendChild(plate);
      var lab = mk('div','circuit-label');
      lab.appendChild(mk('b', null, c.name));
      lab.appendChild(mk('span', null, c.gp));
      ha.appendChild(lab);
    } else {
      plate.appendChild(mk('span','catword', a.cat || 'NEWS'));
      ha.appendChild(plate);
    }
    var box = el('hero'); box.textContent = '';
    var chips = mk('div','chips');
    chips.appendChild(mk('span','chip-feature','今日の一本'));
    if (a.cat) chips.appendChild(mk('span','chip-cat', a.cat));
    chips.appendChild(mk('span','chip-lang', langName(a.lang) + ' → 日本語'));
    box.appendChild(chips);
    var h1 = mk('h2'); h1.id = 'hero-title'; h1.className = 'hero-h';
    h1.appendChild(artLink(a, a.title));
    box.appendChild(h1);
    box.appendChild(mk('p','hero-sum', a.summary));
    box.appendChild(mk('p','orig','原題 — “' + unq(a.orig) + '”'));
    var meta = mk('div','meta');
    meta.appendChild(badge(a.source));
    meta.appendChild(mk('span', null, a.region + '発'));
    meta.appendChild(timeEl(a.published));
    var r = extLink(a.url, '原文を読む ↗', 'read');
    meta.appendChild(r);
    box.appendChild(meta);
    var ht = tagsFor(a); if (ht) box.appendChild(ht);
  }

  function thumbFor(a, withBadge){
    var c = a.circuit && state.circuits[a.circuit];
    var th = artLink(a, null, 'thumb' + (c ? '' : ' nocircuit'));
    th.setAttribute('aria-hidden','true'); th.tabIndex = -1;
    if (c){
      var d = mk('div','draw'); d.appendChild(circuitSvg(c, false)); th.appendChild(d);
      var cn = mk('div','cname'); cn.appendChild(mk('b', null, c.name)); if (c.gp && c.gp !== c.name) cn.appendChild(document.createTextNode(' · ' + c.gp));
      th.appendChild(cn);
    } else if (a.teams && a.teams.length && state.teams[a.teams[0]]){
      var tks = a.teams.filter(function(k){ return state.teams[k]; }).slice(0, 3);
      th.classList.add('nocircuit'); th.appendChild(mk('span','catword', a.cat || 'NEWS'));
      var cn2 = mk('div','cname'); tks.forEach(function(k, i){ if (i) cn2.appendChild(document.createTextNode('　')); cn2.appendChild(teamSwatch(k)); cn2.appendChild(mk('b', null, state.teams[k].en)); }); th.appendChild(cn2);
    } else {
      th.appendChild(mk('span','catword', a.cat || 'NEWS'));
    }
    if (withBadge) th.appendChild(badge(a.source));
    th.appendChild(mk('span','code', langCode(a.lang)));
    return th;
  }
  /* 「同じ話題をほかの媒体で読む」: other outlets' articles on the same topic, opened inside the card.
     Counted only on real actions: compare/open/<from> when opened, compare/go/<from>/<to> when a link is followed. */
  var cmpSeq = 0;
  function cmpEv(path){ try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path:path, title:'', event:true }); } catch(e){} }
  function compareBox(a){
    if (a.isNote || a.kind === 'fan' || a.kind === 'voice' || !a.topic || !state.byTopic) return null;
    var seen = {}; seen[a.source] = 1;
    var others = (state.byTopic[a.topic] || []).filter(function(x){
      if (x.id === a.id || seen[x.source]) return false;
      seen[x.source] = 1; return true;
    });
    if (!others.length) return null;
    var box = mk('div','cmp'), id = 'cmp-' + (++cmpSeq);
    var btn = mk('button','cmp-btn'); btn.type = 'button';
    btn.setAttribute('aria-expanded','false'); btn.setAttribute('aria-controls', id);
    btn.appendChild(mk('span', null, '同じ話題をほかの媒体で読む'));
    var ar = mk('span','cmp-ar','▾'); ar.setAttribute('aria-hidden','true'); btn.appendChild(ar);
    var ul = mk('ul','cmp-list'); ul.id = id; ul.hidden = true;
    var FIRST = 3;
    others.forEach(function(x, i){
      var li = mk('li'); if (i >= FIRST) li.hidden = true;
      var l = mk('a'); l.href = '/news/' + x.id + '/';
      l.appendChild(badge(x.source)); l.appendChild(mk('span','cmp-t', x.title));
      l.addEventListener('click', function(){ cmpEv('compare/go/' + a.id + '/' + x.id); });
      li.appendChild(l); ul.appendChild(li);
    });
    if (others.length > FIRST){
      var more = mk('li','cmp-more'); var mb = mk('button', null, 'この話題のほかの記事（あと' + (others.length - FIRST) + '本）'); mb.type = 'button';
      mb.addEventListener('click', function(){ [].forEach.call(ul.querySelectorAll('li[hidden]'), function(n){ n.hidden = false; }); more.remove(); });
      more.appendChild(mb); ul.appendChild(more);
    }
    btn.addEventListener('click', function(){
      var open = btn.getAttribute('aria-expanded') !== 'true';
      btn.setAttribute('aria-expanded', String(open)); ul.hidden = !open; ar.textContent = open ? '▴' : '▾';
      if (open) cmpEv('compare/open/' + a.id);
    });
    box.appendChild(btn); box.appendChild(ul);
    return box;
  }
  function card(a){
    var it = mk('article','card');
    it.setAttribute('data-c', colorOf(a.source));
    it.appendChild(thumbFor(a, false));
    var meta = mk('div','card-meta');
    var kc = kindChip(a); if (kc) meta.appendChild(kc);
    if (a.isNote){
      var pfl = { note:'note', substack:'Substack', blog:'個人ブログ' }[a.platform] || a.platform;
      meta.appendChild(mk('span', 'plat plat-' + a.platform, a.platform === 'blog' && a.site ? a.site : pfl));
      meta.appendChild(mk('span', 'author', a.author + (a.platform !== 'blog' && a.site && a.site !== a.author ? '（' + a.site + '）' : '')));
    } else {
      /* press the outlet name to see only that outlet's news (owner's request, 18 Oct 2026) */
      var sb = mk('button', 'src-btn'); sb.type = 'button'; sb.appendChild(badge(a.source));
      var on = state.src === a.source;
      sb.title = on ? 'すべての媒体に戻す' : a.source + 'のニュースだけを表示';
      sb.setAttribute('aria-pressed', String(on));
      sb.addEventListener('click', function(){ state.src = state.src === a.source ? 'all' : a.source; try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: 'click/card/src', title: '', event: true }); } catch(e){} renderAll(); goNews(); });
      meta.appendChild(sb);
      meta.appendChild(mk('span', 'rg', a.region));
    }
    meta.appendChild(timeEl(a.published));
    it.appendChild(meta);
    var h = mk('h3'); h.appendChild(artLink(a, a.title)); it.appendChild(h);
    it.appendChild(mk('p', null, a.summary));
    if (a.orig) it.appendChild(mk('span','orig','“' + unq(a.orig) + '”'));
    { var cmp = compareBox(a); if (cmp) it.appendChild(cmp); }
    if (a.isNote){ var host = ''; try { host = new URL(a.url).hostname.replace(/^www\./, ''); } catch(e){} var dst = mk('p','note-dest'); dst.appendChild(document.createTextNode('個人の見解です · リンク先 ')); dst.appendChild(extLink(a.url, host + ' ↗')); it.appendChild(dst); }
    var tt = tagsFor(a); if (tt) it.appendChild(tt);
    var foot = mk('div','card-foot');
    foot.appendChild(mk('span','cat', a.cat || 'ニュース'));
    foot.appendChild(extLink(a.url, '原文へ ↗'));
    it.appendChild(foot);
    return it;
  }

  var KIND_TABS = [['all','すべて'],['news','ニュース'],['tech','テック'],['rumor','パドック（うわさ）'],['fan','掲示板まとめ'],['voice','ファンの声'],['analysis','個人分析']];
  function notePass(n){
    if (state.lang !== 'all' && (n.lang || 'ja') !== state.lang) return false;
    if (state.team !== 'all' && (n.teams || []).indexOf(state.team) < 0) return false;
    if (state.q){ var hay = [n.title, n.summary, n.orig, n.author, n.site, n.cat].join(' ').toLowerCase(); var ws = state.q.toLowerCase().split(/[\s　]+/).filter(Boolean); for (var i = 0; i < ws.length; i++) if (hay.indexOf(ws[i]) < 0) return false; }
    return true;
  }
  function noteList(){ return ((state.notes || {}).notes || []).filter(notePass).sort(function(a, b){ return new Date(b.published) - new Date(a.published); }); }
  function pass(a, skip){
    if (skip !== 'lang' && state.lang !== 'all' && a.lang !== state.lang) return false;
    if (skip !== 'team' && state.team !== 'all' && (a.teams || []).indexOf(state.team) < 0) return false;
    if (skip !== 'kind' && state.kind !== 'all' && (a.kind || 'news') !== state.kind) return false;
    if (skip !== 'src' && state.src !== 'all' && a.source !== state.src) return false;
    if (skip !== 'q' && state.q){
      var hay = [a.title, a.summary, a.orig, a.source, a.cat, a.region].join(' ').toLowerCase();
      (a.teams || []).forEach(function(k){ var t = state.teams[k]; if (t) hay += ' ' + t.name + ' ' + t.en.toLowerCase() + ' ' + t.drivers.join(' '); });
      var c = a.circuit && state.circuits[a.circuit]; if (c) hay += ' ' + c.name + ' ' + c.gp;
      var ws = state.q.toLowerCase().split(/[\s　]+/).filter(Boolean);
      for (var i = 0; i < ws.length; i++) if (hay.indexOf(ws[i]) < 0) return false;
    }
    return true;
  }
  function renderKinds(list){
    var box = el('kindfilter'); box.textContent = '';
    var pool = list.filter(function(a){ return pass(a, 'kind'); }), cnt = { all:pool.length };
    pool.forEach(function(a){ var k = a.kind || 'news'; cnt[k] = (cnt[k] || 0) + 1; });
    KIND_TABS.forEach(function(t){
      if (t[0] !== 'all' && !cnt[t[0]] && state.kind !== t[0]) return;
      var b = mk('button', 'k-' + t[0]); b.type = 'button';
      b.setAttribute('aria-pressed', String(state.kind === t[0]));
      b.appendChild(document.createTextNode(t[1])); b.appendChild(mk('span','n', String(cnt[t[0]] || 0)));
      b.addEventListener('click', function(){ state.kind = t[0]; renderAll(); });
      box.appendChild(b);
    });
  }
  function activeBar(){
    var items = [];
    if (state.q) items.push(['「' + state.q + '」を含む', function(){ state.q = ''; el('q').value = ''; }]);
    if (state.kind !== 'all') items.push([(KIND_TABS.filter(function(t){ return t[0] === state.kind; })[0] || [0,''])[1], function(){ state.kind = 'all'; }]);
    if (state.team !== 'all' && state.teams[state.team]) items.push([state.teams[state.team].en, function(){ state.team = 'all'; }]);
    if (state.src !== 'all') items.push([state.src, function(){ state.src = 'all'; }]);
    if (state.lang !== 'all') items.push([langName(state.lang), function(){ state.lang = 'all'; }]);
    if (!items.length) return null;
    var bar = mk('div','active-bar'); bar.appendChild(mk('span', null, '絞り込み中:'));
    items.forEach(function(x){
      var c = mk('span','af', x[0]); var b = mk('button', null, '×'); b.type = 'button'; b.setAttribute('aria-label', x[0] + 'の絞り込みを外す');
      b.addEventListener('click', function(){ x[1](); renderAll(); }); c.appendChild(b); bar.appendChild(c);
    });
    if (items.length > 1){ var all = mk('button','clear','すべて解除'); all.type = 'button'; all.addEventListener('click', function(){ state.q = ''; el('q').value = ''; state.kind = 'all'; state.team = 'all'; state.src = 'all'; state.lang = 'all'; renderAll(); }); bar.appendChild(all); }
    return bar;
  }
  function goNews(){ if (window.__gwView) window.__gwView('news'); var n = el('news'); if (n) n.scrollIntoView({ behavior:'smooth', block:'start' }); }
  var qTimer = null;
  el('q').addEventListener('input', function(){ clearTimeout(qTimer); var v = this.value.trim(); qTimer = setTimeout(function(){ state.q = v; renderAll(); }, 150); });
  function renderFilters(list){
    renderKinds(list);
    list = list.filter(function(a){ return pass(a, 'lang'); });
    var counts = {};
    list.forEach(function(a){ counts[a.lang] = (counts[a.lang]||0) + 1; });
    var keys = ORDER.filter(function(k){ return counts[k]; })
      .concat(Object.keys(counts).filter(function(k){ return ORDER.indexOf(k) < 0; }));
    var f = el('filters'); f.textContent = '';
    [['all','すべて',list.length]].concat(keys.map(function(k){ return [k, langName(k), counts[k]]; }))
      .forEach(function(x){
        var b = mk('button'); b.type = 'button';
        b.setAttribute('aria-pressed', String(state.lang === x[0]));
        b.appendChild(document.createTextNode(x[1]));
        b.appendChild(mk('span','n', String(x[2])));
        b.addEventListener('click', function(){ state.lang = x[0]; renderAll(); });
        f.appendChild(b);
      });
    var bars = el('bars'); bars.textContent = '';
    var max = 0; keys.forEach(function(k){ if (counts[k] > max) max = counts[k]; });
    keys.forEach(function(k){
      var row = mk('div','bar');
      row.appendChild(mk('span', null, langName(k)));
      var tr = mk('div','bar-track'); var fi = mk('div','bar-fill');
      fi.style.width = Math.round(counts[k]/max*100) + '%';
      tr.appendChild(fi); row.appendChild(tr);
      row.appendChild(mk('span','num', String(counts[k])));
      bars.appendChild(row);
    });
  }

  // desktop: rumour / forum / tech each get their own chapter under the news
  /* after "もっと見る": keep the reader where they were and put focus on the first new item, so the page doesn't jump to the bottom */
  function revealAt(node){
    if (!node) return;
    var link = node.querySelector('h3 a, h4 a, a');
    if (link && link.focus) { try { link.focus({ preventScroll:true }); } catch(e){} }
    var r = node.getBoundingClientRect(), vh = window.innerHeight || 800;
    if (r.top < 60 || r.top > vh - 120) window.scrollBy({ top: r.top - 90, behavior:'smooth' });
  }
  function withMore(parent, g, nodes, first, step){
    nodes.forEach(function(n, i){ if (i >= first) n.classList.add('cut'); g.appendChild(n); });
    parent.appendChild(g);
    if (nodes.length <= first) return;
    var mb = mk('button','feed-more'); mb.type = 'button';
    var left = function(){ return [].filter.call(g.children, function(c){ return c.classList.contains('cut'); }); };
    var lbl = function(){ mb.textContent = 'もっと見る（残り' + left().length + '本）'; };
    lbl();
    mb.addEventListener('click', function(){ var nx = left(); nx.slice(0, step).forEach(function(c){ c.classList.remove('cut'); }); revealAt(nx[0]); if (!left().length) mb.parentNode.removeChild(mb); else lbl(); });
    parent.appendChild(mb);
  }
  function renderKindSecs(all){
    var base = all.filter(function(a){ return pass(a, 'kind'); });
    [['rumor','rumor-grid'],['fan','fan-grid'],['tech','tech-grid']].forEach(function(x){
      var box = el(x[1]); if (!box) return; box.textContent = '';
      var items = base.filter(function(a){ return (a.kind || 'news') === x[0]; });
      box.parentNode.classList.toggle('empty', !items.length);
      withMore(box, mk('div','grid kgrid'), items.map(card), 6, 9);
    });
  }
  function renderFeed(list){
    var deskSplit = false;
    var shown = list.filter(function(a){ return pass(a) && (!deskSplit || (a.kind || 'news') === 'news'); });
    var feed = el('feed'); feed.textContent = '';
    var ab = activeBar(); if (ab) feed.appendChild(ab);
    if (state.view === 'team'){
      var byTeam = {};
      var pool = state.all.filter(function(a){ return pass(a, 'team'); });
      pool.forEach(function(a){ (a.teams || []).forEach(function(k){ (byTeam[k] = byTeam[k] || []).push(a); }); });
      var keys = state.teamOrder.filter(function(k){ return state.team === 'all' || k === state.team; });
      keys.sort(function(x, y){ return (byTeam[y] || []).length - (byTeam[x] || []).length; });
      el('count').textContent = keys.length + 'チーム · 記事のあるチームから順に';
      var tg = mk('div','teams');
      keys.forEach(function(k){
        var t = state.teams[k], items = byTeam[k] || [];
        var sec = mk('section','team'); sec.id = 'team-' + k;
        sec.style.setProperty('--t1', t.c1); sec.style.setProperty('--t2', t.c2); sec.style.setProperty('--t3', t.c3 || t.c2);
        sec.appendChild(mk('div','team-band'));
        var inner = mk('div','team-in');
        var head = mk('div','team-head');
        head.appendChild(mk('h3', null, t.en));
        head.appendChild(mk('span','en', t.en));
        inner.appendChild(head);
        var facts = mk('div','team-facts');
        var f1 = mk('span'); f1.appendChild(document.createTextNode('ドライバー ')); f1.appendChild(mk('b', null, t.drivers.join('・'))); facts.appendChild(f1);
        var f2 = mk('span'); f2.appendChild(document.createTextNode('PU ')); f2.appendChild(mk('b', null, t.pu)); facts.appendChild(f2);
        var f3 = mk('span'); f3.appendChild(document.createTextNode('記事 ')); f3.appendChild(mk('b', null, items.length + '本')); facts.appendChild(f3);
        inner.appendChild(facts);
        if (!items.length) inner.appendChild(mk('p','none','今はこのチームの記事はありません。'));
        items.forEach(function(a){ inner.appendChild(miniRow(a, true)); });
        sec.appendChild(inner);
        tg.appendChild(sec);
      });
      feed.appendChild(tg);
      return;
    }
    if (state.view === 'list'){
      var pool2 = state.all.filter(function(a){ return pass(a); });
      if (!pool2.length){ el('count').textContent = ''; feed.appendChild(mk('p','empty','この条件の記事は、今はまだありません。')); return; }
      el('count').textContent = pool2.length + '本の記事 · 新しい順（日本時間）';
      var lst = mk('div','list'); var lastDay = '';
      pool2.forEach(function(a){
        var dayLabel = '';
        try { dayLabel = new Intl.DateTimeFormat('ja-JP', { timeZone:'Asia/Tokyo', month:'long', day:'numeric', weekday:'short' }).format(new Date(a.published)); } catch(e){}
        if (dayLabel !== lastDay){ lst.appendChild(mk('h3','day', dayLabel)); lastDay = dayLabel; }
        var row = mk('article','li'); row.setAttribute('data-c', colorOf(a.source));
        var hm = '';
        try { hm = new Intl.DateTimeFormat('ja-JP', { timeZone:'Asia/Tokyo', hour:'2-digit', minute:'2-digit', hour12:false }).format(new Date(a.published)); } catch(e){}
        var t = mk('time','li-time', hm); t.dateTime = a.published; row.appendChild(t);
        var src = mk('div','li-src');
        src.appendChild(badge(a.source));
        var c = a.circuit && state.circuits[a.circuit];
        src.appendChild(mk('span','sub', langName(a.lang) + ' · ' + (a.cat || '') + (c ? ' · ' + c.gp : '')));
        var kl = kindChip(a); if (kl){ kl.style.alignSelf = 'flex-start'; src.appendChild(kl); }
        row.appendChild(src);
        var main = mk('div','li-main');
        var h = mk('h3'); h.appendChild(artLink(a, a.title)); main.appendChild(h);
        main.appendChild(mk('p', null, a.summary));
        var tt = tagsFor(a); if (tt) main.appendChild(tt);
        row.appendChild(main);
        var go = mk('div','li-go'); go.style.display = 'flex'; go.style.flexDirection = 'column'; go.style.alignItems = 'flex-end'; go.style.gap = '8px';
        go.appendChild(extLink(a.url, '原文 ↗'));
        go.appendChild(copyButton(a.title + '\n' + a.url, 'リンクをコピー', true));
        row.appendChild(go);
        lst.appendChild(row);
      });
      feed.appendChild(lst);
      return;
    }
    if (!shown.length){ el('count').textContent = ''; feed.appendChild(mk('p','empty','この条件の記事は、今はまだありません。')); return; }
    if (state.view === 'latest'){
      el('count').textContent = shown.length + (deskSplit ? '本のニュース · 新しい順 · うわさ・掲示板・テックは下の章に' : '本の記事 · 新しい順');
      var g = mk('div','grid');
      var lead = -1; for (var li = 0; li < shown.length; li++){ var kk = shown[li].kind || 'news'; if (kk === 'news' || kk === 'tech'){ lead = li; break; } }
      var ordered = lead > 0 ? [shown[lead]].concat(shown.slice(0, lead), shown.slice(lead + 1)) : shown;
      // first rows: desktop 8 (3 full rows with the wide lead card), phones 9; then 15 / 14 more per tap so rows stay full
      var PAGE = 30; if (!state.newsShown) state.newsShown = wide.matches ? 8 : 30;  // phones: 30 first, 30 more per tap (owner, 25 Oct 2026)
      ordered.forEach(function(a, i){ var c = card(a); if (i >= state.newsShown) c.classList.add('cut'); g.appendChild(c); });
      feed.appendChild(g);
      if (ordered.length > state.newsShown){
        var mb = mk('button','feed-more'); mb.type = 'button';
        var lbl = function(){ mb.textContent = 'もっと見る（残り' + g.querySelectorAll('.card.cut').length + '本）'; };
        lbl();
        mb.addEventListener('click', function(){
          var cs = g.querySelectorAll('.card.cut'), firstNew = cs[0];
          for (var j = 0; j < cs.length && j < PAGE; j++) cs[j].classList.remove('cut');
          revealAt(firstNew);
          state.newsShown += PAGE;
          if (!g.querySelector('.card.cut')) mb.parentNode.removeChild(mb); else lbl();
        });
        feed.appendChild(mb);
      }
    } else {
      var groups = {}, order = [];
      shown.forEach(function(a){
        if (!groups[a.source]){ groups[a.source] = []; order.push(a.source); }
        groups[a.source].push(a);
      });
      order.sort(function(x, y){ return groups[y].length - groups[x].length; });
      el('count').textContent = order.length + '媒体 · ' + shown.length + '本の記事 · 記事の多い媒体から順に';
      var legend = mk('nav','legend'); legend.setAttribute('aria-label','媒体へ移動');
      order.forEach(function(src){
        var l = mk('a'); l.href = '#' + slug(src);
        l.appendChild(badge(src));
        l.appendChild(mk('span', null, ' ' + groups[src].length));
        l.addEventListener('click', function(e){ var t = el(slug(src)); if (t){ e.preventDefault(); t.scrollIntoView({ behavior:'smooth', block:'start' }); } });
        legend.appendChild(l);
      });
      feed.appendChild(legend);
      var wrapG = mk('div','groups');
      order.forEach(function(src){
        var items = groups[src].slice(), first = items[0];
        var pi = 0;
        for (var i = 0; i < items.length; i++){ if (items[i].pick){ pi = i; break; } }
        var pick = items.splice(pi, 1)[0];
        var sec = mk('section','group'); sec.id = slug(src);
        sec.setAttribute('data-c', colorOf(src));
        var head = mk('div','group-head');
        var h3s = mk('h3', null, src); h3s.title = src + 'の記事だけを表示'; h3s.addEventListener('click', function(){ state.src = state.src === src ? 'all' : src; renderAll(); goNews(); }); head.appendChild(h3s);
        head.appendChild(mk('span', null, langName(first.lang) + ' · ' + first.region + ' · ' + groups[src].length + '本'));
        sec.appendChild(head);
        groups[src].forEach(function(a){ sec.appendChild(miniRow(a, false)); });

        wrapG.appendChild(sec);
      });
      feed.appendChild(wrapG);
    }
  }

  function miniRow(a, withSource){
    var c = a.circuit && state.circuits[a.circuit];
    var row = mk('div','mini');
    row.setAttribute('data-c', colorOf(a.source));
    var ar = artLink(a, null, 'mini-art'); ar.setAttribute('aria-hidden','true'); ar.tabIndex = -1;
    if (c) ar.appendChild(circuitSvg(c, false)); else if (a.teams && a.teams.length && state.teams[a.teams[0]]){ a.teams.filter(function(k){ return state.teams[k]; }).slice(0, 3).forEach(function(k){ ar.appendChild(teamSwatch(k)); }); ar.classList.add('has-tsw'); } else ar.appendChild(mk('span','catword', a.cat || 'NEWS'));
    row.appendChild(ar);
    var body = mk('div');
    var h = mk('h4'); h.appendChild(artLink(a, a.title)); body.appendChild(h);
    var meta = mk('div','card-meta');
    var km = kindChip(a); if (km) meta.appendChild(km);
    if (withSource) meta.appendChild(badge(a.source));
    if (c) meta.appendChild(mk('span', null, c.gp));
    meta.appendChild(mk('span', null, a.cat || ''));
    meta.appendChild(timeEl(a.published));
    body.appendChild(meta);
    row.appendChild(body);
    return row;
  }

  function renderAll(){
    var d = state.data; if (!d) return;
    var PLAT_JA = { note:'note', substack:'Substack', blog:'個人ブログ' };
    var notesAsArts = ((state.notes || {}).notes || []).filter(function(n){ return !n.paid; }).map(function(n){
      return { id:n.id, isNote:true, platform:n.platform || 'note', site:n.site, author:n.author, kind:'analysis', lang:n.lang || 'ja', source:n.author, region:PLAT_JA[n.platform || 'note'] || n.platform, cat:n.cat, circuit:n.circuit, teams:n.teams, title:n.title, summary:n.summary, orig:n.orig, url:n.url, published:n.published };
    });
    var all = (d.articles || []).concat(notesAsArts).slice().sort(function(a,b){ return new Date(b.published) - new Date(a.published); });
    state.all = all;
    // same story, other outlets (読み比べ, owner's OK 13 Oct 2026): news/tech/rumor articles grouped by topic, newest first
    state.byTopic = {};
    all.forEach(function(a){ if (a.isNote || a.kind === 'fan' || a.kind === 'voice' || !a.topic) return; (state.byTopic[a.topic] = state.byTopic[a.topic] || []).push(a); });
    state.srcRegion = {}; all.forEach(function(a){ if (a.region && !state.srcRegion[a.source]) state.srcRegion[a.source] = a.region; });
    state.byUrl = {}; all.forEach(function(a){ state.byUrl[a.url] = a; });
    var tr = trending(all), rest, ht = el('hub-top');
    if (ht){ renderHubArt(ht.getAttribute('data-circuit')); rest = all; }  // 読み解き stays at the top (owner's decision, 12 Oct 2026)
    else if (tr){ renderTrending(tr); rest = all; }
    else {
      var hero = all.filter(function(a){ return a.featured; })[0] || all[0];
      rest = all.filter(function(a){ return a !== hero; });
      if (hero) renderHero(hero);
    }
    renderFilters(rest);
    renderTeamFilter(all);
    renderFeed(rest);
    renderKindSecs(all);
    el('view-latest').setAttribute('aria-pressed', String(state.view === 'latest' && state.kind === 'all'));
    ['tech','rumor','voice','analysis'].forEach(function(k){ el('view-' + k).setAttribute('aria-pressed', String(state.view === 'latest' && state.kind === k)); });
    el('view-ja').setAttribute('aria-pressed', String(state.lang === 'ja'));
    { var fnum = (state.kind !== 'all') + (state.lang !== 'all') + (state.team !== 'all') + (state.src !== 'all'); var fb = el('filt-n'); if (fb){ fb.hidden = !fnum; fb.textContent = fnum ? String(fnum) : ''; } }
    if (d.updatedAt){
      var up = el('updated'); up.textContent = '';
      if (state.fromSnapshot) up.appendChild(document.createTextNode('保存済みの記事 '));
      else { up.appendChild(mk('span','upd-long','最終更新 ')); up.appendChild(mk('span','upd-short','更新 ')); }
      up.appendChild(document.createTextNode(jst(d.updatedAt, true)));
    }
    renderBand();
    renderGeek();
  }

  el('view-latest').addEventListener('click', function(){ state.view = 'latest'; state.kind = 'all'; renderAll(); });
  ['tech','rumor','voice','analysis'].forEach(function(k){ el('view-' + k).addEventListener('click', function(){ state.view = 'latest'; state.kind = state.kind === k ? 'all' : k; state.newsShown = 0; renderAll(); }); });
  el('view-ja').addEventListener('click', function(){ state.lang = state.lang === 'ja' ? 'all' : 'ja'; renderAll(); });

  var SITE_URL = 'https://f1gridwalk.github.io/';
  function copyText(text, btn, label){
    function done(){ btn.textContent = 'コピーしました'; btn.classList.add('done'); setTimeout(function(){ btn.textContent = label; btn.classList.remove('done'); }, 2000); }
    function fallback(){
      var next = btn.nextElementSibling;
      if (next && next.classList.contains('copy-fallback')){ next.select(); return; }
      var inp = mk('input','copy-fallback'); inp.readOnly = true; inp.value = text; inp.setAttribute('aria-label','コピーするテキスト');
      btn.insertAdjacentElement('afterend', inp); inp.focus(); inp.select();
      btn.textContent = '下の文字を長押し（選択）してコピー';
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(done, fallback); }
      else fallback();
    } catch(e){ fallback(); }
  }
  function copyButton(text, label, small){
    var b = mk('button','copybtn' + (small ? ' small' : ''), label); b.type = 'button';
    b.addEventListener('click', function(){ copyText(text, b, label); });
    return b;
  }
  if (SITE_URL.indexOf('github.io') < 0){
    var nb = mk('div','copy-note');
    nb.appendChild(document.createTextNode('これは作業用のコピーです。自動更新は公開サイトに入ります → '));
    var nl = extLink('https://f1gridwalk.github.io/', '公開サイトを開く'); nb.appendChild(nl);
    document.body.insertBefore(nb, document.body.firstChild);
  }
  // share menu: X / LINE / Threads / Facebook / Hatena / copy / native share sheet
  (function(){
    var btn = el('share-btn'), menu = el('share-menu'); if (!btn || !menu) return;
    function shareText(){
      var h = el('hero-title'), t = h ? h.textContent.trim() : '';
      return (t && t.indexOf('読み込んでいます') < 0 ? (el('hub-top') ? 'STORY：' : '今週の注目：') + t + ' | ' : '') + 'F1 Grid Walk — 世界のF1ニュースを日本語で';
    }
    function hrefFor(k){
      var u = encodeURIComponent(SITE_URL), t = encodeURIComponent(shareText());
      return {
        x: 'https://x.com/intent/tweet?text=' + t + '&url=' + u,
        line: 'https://social-plugins.line.me/lineit/share?url=' + u + '&text=' + t,
        threads: 'https://www.threads.net/intent/post?text=' + encodeURIComponent(shareText() + ' ' + SITE_URL),
        facebook: 'https://www.facebook.com/sharer/sharer.php?u=' + u,
        hatena: 'https://b.hatena.ne.jp/add?mode=confirm&url=' + u + '&title=' + t
      }[k];
    }
    function open(on){ menu.hidden = !on; btn.setAttribute('aria-expanded', on ? 'true' : 'false'); }
    function track(k){ try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path:'share/' + k, title:'共有: ' + k, event:true }); } catch(e){} }
    if (navigator.share) el('share-native').hidden = false;
    btn.addEventListener('click', function(e){ e.stopPropagation(); open(menu.hidden); });
    [].forEach.call(menu.querySelectorAll('a[data-share]'), function(a){
      a.addEventListener('click', function(){ a.href = hrefFor(a.getAttribute('data-share')); track(a.getAttribute('data-share')); setTimeout(function(){ open(false); }, 0); });
      a.href = hrefFor(a.getAttribute('data-share'));
    });
    var cp = el('copy-site'), cpLabel = cp.innerHTML;
    cp.addEventListener('click', function(){
      track('copy');
      var done = function(){ cp.innerHTML = '<b>リンク</b><span>コピーしました</span>'; setTimeout(function(){ cp.innerHTML = cpLabel; open(false); }, 1200); };
      try { navigator.clipboard.writeText(SITE_URL).then(done, function(){ window.prompt('このURLをコピーしてください', SITE_URL); }); }
      catch(e){ window.prompt('このURLをコピーしてください', SITE_URL); }
    });
    el('share-native').addEventListener('click', function(){
      track('native'); open(false);
      navigator.share({ title:'F1 Grid Walk', text:shareText(), url:SITE_URL }).catch(function(){});
    });
    document.addEventListener('click', function(e){ if (!menu.hidden && !menu.contains(e.target)) open(false); });
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && !menu.hidden){ open(false); btn.focus(); } });
  })();


  function teamSwatch(key){
    var t = state.teams[key] || { c1:'#888', c2:'#ccc' };
    var d = mk('span','tdot'); d.setAttribute('aria-hidden','true'); d.title = t.en || t.name || '';
    d.style.setProperty('--t1', t.c1); d.style.setProperty('--t2', t.c2); d.style.setProperty('--t3', t.c3 || t.c2);
    return d;
  }
  // one short label on every item, so what kind of information it is shows at a glance
  var KIND = { primary:'一次情報', news:'報道', tech:'技術', rumor:'噂', fan:'ファン投稿', voice:'ファンの声', analysis:'個人分析' };
  var KIND_TIP = { primary:'F1・FIA・チームなど当事者の公式発表', news:'報道機関の記事', tech:'技術の解説・分析記事', rumor:'報道で出たうわさ・未確認の話', fan:'ファン掲示板で話題の投稿（未確認を含む）', voice:'日本と海外のファンの反応を、F1 Grid Walk がまとめたもの（ファンの意見です）', analysis:'個人による分析・考察（note・Substack・個人ブログ。報道ではなく個人の見解です）' };
  var PRIMARY_SRC = /^(Formula1\.com|F1公式|FIA)(\s|$)/i;
  function kindOf(a){ var k = a.kind || 'news'; if (k === 'news' && (a.primary || PRIMARY_SRC.test(a.source || ''))) return 'primary'; return KIND[k] ? k : 'news'; }
  function kindChip(a){ var k = a === 'analysis' ? 'analysis' : kindOf(a); var c = mk('span', 'kind ' + k, KIND[k]); c.title = KIND_TIP[k]; return c; }
  function geekRow(a){
    var c = a.circuit && state.circuits[a.circuit];
    var row = mk('div','grow'); row.setAttribute('data-c', colorOf(a.source));
    var ar = artLink(a, null, 'mini-art'); ar.setAttribute('aria-hidden','true'); ar.tabIndex = -1;
    if (c) ar.appendChild(circuitSvg(c, false));
    else if (a.teams && a.teams.length && state.teams[a.teams[0]]){ a.teams.filter(function(k){ return state.teams[k]; }).slice(0, 3).forEach(function(k){ ar.appendChild(teamSwatch(k)); }); ar.classList.add('has-tsw'); }
    else ar.appendChild(mk('span','catword', a.cat || 'NEWS'));
    row.appendChild(ar);
    var body = mk('div');
    var h = mk('h4'); h.appendChild(artLink(a, a.title)); body.appendChild(h);
    body.appendChild(mk('p', null, a.summary));
    var meta = mk('div','card-meta');
    var k = kindChip(a); if (k) meta.appendChild(k);
    meta.appendChild(badge(a.source));
    meta.appendChild(mk('span', null, langCode(a.lang)));
    meta.appendChild(timeEl(a.published));
    (a.teams || []).filter(function(k){ return state.teams[k]; }).forEach(function(k){ var tm = mk('span'); tm.appendChild(teamSwatch(k)); tm.appendChild(document.createTextNode(' ' + state.teams[k].en)); meta.appendChild(tm); });
    body.appendChild(meta);
    row.appendChild(body);
    return row;
  }
  function renderGeek(){
    var all = state.all || [];
    var tech = all.filter(function(a){ return a.kind === 'tech'; }).slice(0, 40);
    var gos = all.filter(function(a){ return a.kind === 'rumor' || a.kind === 'fan' || a.kind === 'voice'; }).slice(0, 40);
    var tl = el('tech-list'), gl = el('gossip-list'); tl.textContent = ''; gl.textContent = '';
    tech.forEach(function(a){ tl.appendChild(geekRow(a)); });
    gos.forEach(function(a){ gl.appendChild(geekRow(a)); });
    if (!tech.length) tl.appendChild(mk('p','empty','今はテクニカル記事がありません。'));
    if (!gos.length) gl.appendChild(mk('p','empty','今はパドックの話題はありません。'));
    function more(box, label, kind){ var b = mk('button','more-link', label); b.type = 'button'; b.addEventListener('click', function(){ state.kind = kind; renderAll(); goNews(); }); box.appendChild(b); }
    more(tl, 'テックの記事をすべて見る →', 'tech');
    var mw = mk('div','more-row'); more(mw, 'うわさを全部 →', 'rumor'); more(mw, '掲示板まとめを全部 →', 'fan'); gl.appendChild(mw);
    el('geek').hidden = !(tech.length || gos.length);
  }
  var PLAT = { note:'note', substack:'Substack', blog:'ブログ' };
  function noteRow(n){
    var row = mk('div','nrow');
    var h = mk('h4'); h.appendChild(extLink(n.url, n.title)); row.appendChild(h);
    if (n.orig && n.orig !== n.title) row.appendChild(mk('div','norig', n.orig));
    row.appendChild(mk('p', null, n.summary));
    var meta = mk('div','card-meta');
    meta.appendChild(kindChip('analysis'));
    meta.appendChild(mk('span', 'fee ' + (n.paid ? 'paid' : 'free'), n.paid ? '有料' : '無料'));
    var pf = n.platform || 'note';
    meta.appendChild(mk('span', 'plat plat-' + pf, PLAT[pf] || pf));
    meta.appendChild(mk('span','author', n.author + (n.site && n.site !== n.author ? '（' + n.site + '）' : '')));
    if (n.lang && n.lang !== 'ja') meta.appendChild(mk('span', null, langCode(n.lang)));
    if (n.cat) meta.appendChild(mk('span', null, n.cat));
    meta.appendChild(timeEl(n.published));
    if (n.paid && n.price) meta.appendChild(mk('span','price', n.price));
    (n.teams || []).filter(function(k){ return state.teams[k]; }).forEach(function(k){ var tm = mk('span','tm'); tm.appendChild(teamSwatch(k)); tm.appendChild(document.createTextNode(' ' + state.teams[k].en)); meta.appendChild(tm); });
    row.appendChild(meta);
    return row;
  }
  function renderNotes(){
    var list = ((state.notes || {}).notes || []).slice().sort(function(a, b){ return new Date(b.published) - new Date(a.published); });
    var fr = list.filter(function(n){ return !n.paid; }).slice(0, 50), pd = list.filter(function(n){ return n.paid; }).slice(0, 30);
    var fl = el('notes-free'), pl = el('notes-paid'); fl.textContent = ''; pl.textContent = '';
    state.noteByUrl = {};
    list.forEach(function(n){ state.noteByUrl[n.url] = { id:n.id, source:(n.platform || 'note') + ' ' + n.author, title:n.title }; });
    fr.forEach(function(n){ fl.appendChild(noteRow(n)); });
    pd.forEach(function(n){ pl.appendChild(noteRow(n)); });
    if (!fr.length) fl.appendChild(mk('p','empty','今は無料の記事がありません。'));
    if (!pd.length) pl.appendChild(mk('p','empty','今は有料の記事がありません。'));
    el('notes').hidden = !list.length;
  }
  function renderNumbers(){
    var s = state.season; if (!s || !s.calendar) return;
    var teamOf = {}; (s.drivers || []).forEach(function(d){ teamOf[d.name] = d.team; });
    var done = 0, left = 0, off = 0, dw = {}, tw = {};
    s.calendar.forEach(function(r){
      if (r.cancelled){ off++; return; }
      if (r.winner){ done++; dw[r.winner] = (dw[r.winner] || 0) + 1; var tm = teamOf[r.winner]; if (tm) tw[tm] = (tw[tm] || 0) + 1; }
      else left++;
    });
    if (!done) return;
    var box = el('nums'); box.textContent = '';
    function tile(big, unit, label, teamKey){
      var t = mk('div','num-t'), b = mk('b');
      if (teamKey && state.teams[teamKey]){ var d = mk('span','tdot'); d.style.setProperty('--t1', state.teams[teamKey].c1); d.style.setProperty('--t2', state.teams[teamKey].c2); d.style.setProperty('--t3', state.teams[teamKey].c3 || state.teams[teamKey].c2); b.appendChild(d); }
      b.appendChild(document.createTextNode(big)); if (unit) b.appendChild(mk('small', null, unit));
      t.appendChild(b); t.appendChild(mk('span', null, label)); box.appendChild(t);
    }
    var bestT = Object.keys(tw).sort(function(a, b){ return tw[b] - tw[a]; })[0];
    if (bestT) tile(tw[bestT] + '/' + done, '勝', (state.teams[bestT] || {}).en + 'の勝率 ' + Math.round(tw[bestT] / done * 100) + '%', bestT);
    var bestD = Object.keys(dw).sort(function(a, b){ return dw[b] - dw[a]; })[0];
    if (bestD) tile(String(dw[bestD]), '勝', bestD + 'の今季の優勝', teamOf[bestD]);
    var dr = s.drivers || [];
    if (dr.length > 1) tile(String(dr[0].pts - dr[1].pts), '点', '首位' + dr[0].name + 'と2位' + dr[1].name + 'の差', dr[0].team);
    tile(String(Object.keys(dw).length), '人', 'ここまでの優勝ドライバー');
    tile(String(left), '戦', '残りのレース（今週を含む）');
    tile(String(off), '戦', '中止になったグランプリ');
    el('num-note').textContent = done + '戦終了時点';
    el('numbers').hidden = false;
  }
  function renderBand(){
    if (!state.teamOrder.length) return;
    el('teams-band').hidden = false;
    var all = state.all || [], cnt = {}, cpts = {};
    all.forEach(function(a){ (a.teams || []).forEach(function(k){ cnt[k] = (cnt[k] || 0) + 1; }); });
    ((state.season || {}).constructors || []).forEach(function(c){ cpts[c.team] = c; });
    var g = el('teamgrid'); g.textContent = '';
    var order = state.teamOrder.slice().sort(function(a, b){ return ((cpts[a] || {}).pos || 99) - ((cpts[b] || {}).pos || 99); });
    order.forEach(function(k){
      var t = state.teams[k], b = mk('button','tcard'); b.type = 'button';
      b.style.setProperty('--t1', t.c1); b.style.setProperty('--t2', t.c2); b.style.setProperty('--t3', t.c3 || t.c2);
      b.setAttribute('aria-pressed', String(state.team === k));
      var nm = mk('div','nm'); var nmL = mk('span'); nmL.appendChild(teamSwatch(k)); nmL.appendChild(document.createTextNode(' ' + t.en)); nm.appendChild(nmL); nm.appendChild(mk('small', null, t.name)); b.appendChild(nm);
      b.appendChild(mk('div','dr', t.drivers.join('・') + ' · PU ' + t.pu));
      var r2 = mk('div','row2');
      var l = mk('span'); l.appendChild(document.createTextNode(cpts[k] ? cpts[k].pos + '位 ' : '')); l.appendChild(mk('b', null, cpts[k] ? cpts[k].pts + '点' : '6位以下'));
      r2.appendChild(l); r2.appendChild(mk('span', null, '今週の記事 ' + (cnt[k] || 0) + '本'));
      b.appendChild(r2);
      b.addEventListener('click', function(){ state.team = state.team === k ? 'all' : k; renderAll(); goNews(); });
      g.appendChild(b);
    });
    // wins
    var s = state.season || {}, w = {}, teamOf = {};
    (s.drivers || []).forEach(function(d){ teamOf[d.name] = d.team; });
    (s.calendar || []).forEach(function(r){ if (r.winner) w[r.winner] = (w[r.winner] || 0) + 1; });
    var ws = Object.keys(w).sort(function(a, b){ return w[b] - w[a]; }), max = ws.length ? w[ws[0]] : 1, total = 0;
    var wb = el('wins'); wb.textContent = '';
    ws.forEach(function(n){
      total += w[n];
      var tm = state.teams[teamOf[n]] || {};
      var row = mk('div','wrow');
      var nm = mk('span'); var dt = mk('span','tdot'); dt.style.setProperty('--t1', tm.c1 || '#888'); dt.style.setProperty('--t2', tm.c2 || '#ccc'); dt.style.setProperty('--t3', tm.c3 || tm.c2 || '#ccc'); nm.appendChild(dt); nm.appendChild(document.createTextNode(' ' + n)); row.appendChild(nm);
      var bar = mk('span','bar'); var i = mk('i'); i.style.width = (w[n] / max * 100) + '%'; i.style.background = tm.c1 || 'var(--ink)'; bar.appendChild(i); row.appendChild(bar);
      row.appendChild(mk('b', null, String(w[n])));
      wb.appendChild(row);
    });
    el('wins-note').textContent = total + '戦終了 · ' + ws.length + '人が優勝';
    // topics
    var tg = {}, weekAgo = Date.now() - 7 * 864e5;
    all.forEach(function(a){ if (!a.topic || new Date(a.published).getTime() < weekAgo) return; (tg[a.topic] = tg[a.topic] || { src:{}, items:[] }); tg[a.topic].src[a.source] = 1; tg[a.topic].items.push(a); });
    var tk = Object.keys(tg).map(function(k){ return { k:k, n:Object.keys(tg[k].src).length, items:tg[k].items }; }).sort(function(a, b){ return b.n - a.n || b.items.length - a.items.length; }).slice(0, 6);
    var ol = el('topics'); ol.textContent = '';
    var infos = (state.data || {}).topics || {};
    tk.forEach(function(x){
      var li = mk('li');
      var dt = mk('details'); var sm = mk('summary');
      sm.appendChild(mk('b', null, (infos[x.k] && infos[x.k].title) || x.items[0].title));
      sm.appendChild(mk('span', null, x.n + '媒体 ▾'));
      dt.appendChild(sm);
      var ul = mk('ul','tlinks');
      x.items.slice().sort(function(a, b){ return new Date(b.published) - new Date(a.published); }).forEach(function(a){
        var it = mk('li'); it.setAttribute('data-c', colorOf(a.source));
        it.appendChild(badge(a.source));
        it.appendChild(artLink(a, a.title));
        ul.appendChild(it);
      });
      dt.appendChild(ul);
      li.appendChild(dt);
      ol.appendChild(li);
    });
    // sources
    var sc = {}, sl = {};
    all.forEach(function(a){ if (a.isNote) return; sc[a.source] = (sc[a.source] || 0) + 1; sl[a.source] = a.lang; }); /* media only: individual writers are not outlets (owner, 9 Oct 2026) */
    var sk = Object.keys(sc).sort(function(a, b){ return sc[b] - sc[a]; }), smax = sk.length ? sc[sk[0]] : 1;
    var sb = el('sources'); sb.textContent = '';
    sk.forEach(function(k){
      var row = mk('div','srow2'); row.setAttribute('data-c', colorOf(k));
      var n = mk('span'); n.appendChild(badge(k)); n.appendChild(mk('span','tl-lang', ' ' + langCode(sl[k]))); row.appendChild(n);
      var bar = mk('span','bar'); var i = mk('i'); i.style.width = (sc[k] / smax * 100) + '%'; bar.appendChild(i); row.appendChild(bar);
      row.appendChild(mk('b', null, String(sc[k])));
      if (state.src === k) row.classList.add('on');
      row.setAttribute('role','button'); row.tabIndex = 0; row.title = k + 'の記事だけを表示';
      var go = function(){ state.src = state.src === k ? 'all' : k; renderAll(); goNews(); };
      row.addEventListener('click', go); row.addEventListener('keydown', function(e){ if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); go(); } });
      sb.appendChild(row);
    });
    if (sk.length > 10) {
      if (window.__srcAll) sb.classList.add('all'); else sb.classList.remove('all');
      var mb = mk('button','src-more', window.__srcAll ? '閉じる' : 'すべての媒体を見る（' + sk.length + '）'); mb.type = 'button';
      mb.addEventListener('click', function(ev){ ev.stopPropagation(); window.__srcAll = !window.__srcAll; sb.classList.toggle('all', window.__srcAll); mb.textContent = window.__srcAll ? '閉じる' : 'すべての媒体を見る（' + sk.length + '）'; });
      sb.appendChild(mb);
    }
  }
  /* ---------- race week, standings, calendar ---------- */
  function fmtJST(iso, opts){
    try { return new Intl.DateTimeFormat('ja-JP', Object.assign({ timeZone:'Asia/Tokyo' }, opts)).format(new Date(iso)); } catch(e){ return ''; }
  }
  function dur(ms){
    var m = Math.max(0, Math.floor(ms / 60000)), d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), mm = m % 60;
    return { d:d, h:h, m:mm };
  }
  function countNode(ms){
    var x = dur(ms), n = mk('span','num');
    function part(v, u){ n.appendChild(document.createTextNode(String(v))); n.appendChild(mk('small', null, u)); }
    if (x.d) part(x.d, '日');
    part(x.h, '時間'); if (!x.d) part(x.m, '分');
    return n;
  }
  function renderTopRace(w){
    var box = el('top-race'); if (!box || !w || !w.sessions || !w.sessions.length) return; box.textContent = '';
    var now = Date.now(), race = w.sessions[w.sessions.length - 1], cur = null, next = null;
    w.sessions.forEach(function(x){ var a = new Date(x.start).getTime(), b = new Date(x.end).getTime(); if (a <= now && now < b) cur = x; if (!next && a > now) next = x; });
    box.appendChild(mk('b','tr-round','第' + w.round + '戦'));
    box.appendChild(mk('span','tr-gp', w.gp));
    var rs = new Date(race.start).getTime(), re = new Date(race.end).getTime();
    if (now < rs){ var d = dur(rs - now), c = mk('span','tr-count'); c.appendChild(document.createTextNode('決勝まで ')); c.appendChild(mk('b', null, (d.d ? d.d + '日' : '') + d.h + '時間' + (d.d ? '' : d.m + '分'))); box.appendChild(c); }
    else if (now < re) box.appendChild(mk('span','tr-count','決勝 開催中'));
    else box.appendChild(mk('span','tr-count','決勝終了'));
    var sx = cur || next;
    if (sx && sx !== race) box.appendChild(mk('span','tr-next', (cur ? '開催中 ' : '次 ') + sx.name + ' ' + fmtJST(sx.start, { month:'numeric', day:'numeric', weekday:'short', hour:'2-digit', minute:'2-digit', hour12:false })));
    box.hidden = false;
  }
  function renderWeekend(){
    var s = state.season; if (!s || !s.weekend) return;
    renderTopRace(s.weekend);
    var w = s.weekend, now = Date.now(), box = el('wk-main'); box.textContent = '';
    var c = state.circuits[w.circuit];
    var eb = mk('div','wk-eyebrow');
    eb.appendChild(mk('b', null, '第' + w.round + '戦'));
    if (c) eb.appendChild(mk('span', null, c.name));
    if (w.laps) eb.appendChild(mk('span', null, w.laps + '周' + (w.lengthKm ? ' · 1周 ' + w.lengthKm + 'km' : '')));
    box.appendChild(eb);
    var left = mk('div');
    left.appendChild(mk('h2','wk-title', w.gp));
    var race = w.sessions[w.sessions.length - 1];
    var cur = null, next = null;
    w.sessions.forEach(function(x){
      var a = new Date(x.start).getTime(), b = new Date(x.end).getTime();
      if (a <= now && now < b) cur = x;
      if (!next && a > now) next = x;
    });
    var cnt = mk('div','wk-count');
    var rs = new Date(race.start).getTime(), re = new Date(race.end).getTime();
    if (now < rs){ cnt.appendChild(mk('span','lbl','決勝まで')); cnt.appendChild(countNode(rs - now)); }
    else if (now < re){ cnt.appendChild(mk('span','num','決勝 開催中')); }
    else { cnt.appendChild(mk('span','lbl','決勝は終了しました。結果は次の更新でお届けします。')); }
    left.appendChild(cnt);
    left.appendChild(mk('p','wk-when', '決勝 ' + fmtJST(race.start, { month:'long', day:'numeric', weekday:'short', hour:'2-digit', minute:'2-digit', hour12:false }) + ' スタート（日本時間）'));
    if (w.note) left.appendChild(mk('p','wk-note', w.note));
    box.appendChild(left);
    var mp = mk('div','wk-map');
    if (c){ var sg = circuitSvg(c, true); sg.setAttribute('role','img'); sg.setAttribute('aria-label', c.name + 'のコース図'); mp.appendChild(sg); }
    box.appendChild(mp);
    var ul = mk('ul','sessions');
    w.sessions.forEach(function(x){
      var a = new Date(x.start).getTime(), b = new Date(x.end).getTime();
      var li = mk('li', b <= now ? 'done' : (x === cur ? 'now' : (x === next ? 'next' : '')));
      li.appendChild(mk('b', 'ln', x.name));
      li.appendChild(mk('b', 'sn', ({'フリー走行1':'FP1','フリー走行2':'FP2','フリー走行3':'FP3','スプリント予選':'SQ','スプリント':'SPR'})[x.name] || x.name));
      li.appendChild(mk('span','t', fmtJST(x.start, { month:'numeric', day:'numeric', weekday:'short', hour:'2-digit', minute:'2-digit', hour12:false })));
      var st = b <= now ? ('終了' + (x.result ? ' · ' + x.result : '')) : (x === cur ? 'いま開催中' : (function(){ var d = dur(a - now); return 'あと ' + (d.d ? d.d + '日' : '') + d.h + '時間' + (d.d ? '' : d.m + '分'); })());
      li.appendChild(mk('span','st', st));
      ul.appendChild(li);
    });
    box.appendChild(ul);
  }
  function renderStandings(){
    var s = state.season; if (!s) return;
    var box = el('standings'); box.textContent = '';
    box.appendChild(mk('h2', null, 'ランキング'));
    if (s.standingsAfter){ var sa = s.standingsAfter; box.appendChild(mk('div','sub', (typeof sa === 'string') ? sa + ' 終了時点' : '第' + sa.round + '戦 ' + sa.gp + ' 終了時点')); }
    var tabs = mk('div','stand-tabs'); tabs.setAttribute('role','group'); tabs.setAttribute('aria-label','ランキングの種類');
    [['d','ドライバー'],['c','チーム']].forEach(function(t){
      var b = mk('button', null, t[1]); b.type = 'button';
      b.setAttribute('aria-pressed', String(state.standTab === t[0]));
      b.addEventListener('click', function(){ state.standTab = t[0]; renderStandings(); });
      tabs.appendChild(b);
    });
    box.appendChild(tabs);
    var rows = state.standTab === 'c' ? (s.constructors || []) : (s.drivers || []);
    var max = rows.length ? rows[0].pts : 1;
    rows.forEach(function(r){
      var tm = state.teams[r.team] || {};
      var row = mk('div','srow' + (r.pos === 1 ? ' lead' : ''));
      row.style.setProperty('--t1', tm.c1 || 'var(--moss)'); row.style.setProperty('--t2', tm.c2 || 'var(--line)'); row.style.setProperty('--t3', tm.c3 || tm.c2 || 'var(--line)');
      row.appendChild(mk('span','p', String(r.pos)));
      row.appendChild(mk('span','tdot'));
      var n = mk('span','n', state.standTab === 'c' ? (tm.en || r.team) : r.name);
      if (state.standTab !== 'c' && tm.en) n.appendChild(mk('small', null, tm.en));
      row.appendChild(n);
      var bar = mk('span','b'); var fill = mk('i'); fill.style.width = Math.round(r.pts / max * 100) + '%'; bar.appendChild(fill); row.appendChild(bar);
      row.appendChild(mk('span','v', String(r.pts)));
      box.appendChild(row);
    });
    if (state.standTab === 'c' && rows.length < 11) box.appendChild(mk('div','sub', '上位' + rows.length + 'チームを表示しています。'));
  }
  function renderCalendar(){
    var s = state.season; if (!s || !s.calendar) return;
    var box = el('calendar'); box.textContent = '';
    var cur = s.weekend ? s.weekend.round : null, done = 0, left = 0;
    s.calendar.forEach(function(r){
      var isNow = r.round === cur && !r.winner;
      var d = mk('div','rd' + (r.cancelled ? ' off' : '') + (isNow ? ' now' : ''));
      d.appendChild(mk('span','rn', r.round ? 'Rd.' + r.round : '—'));
      var c = state.circuits[r.circuit];
      var mp = mk('div','mp'); if (c) mp.appendChild(circuitSvg(c, false)); d.appendChild(mp);
      d.appendChild(mk('span','g', r.gp));
      if (r.cancelled){ d.appendChild(mk('span','flag','中止')); }
      else {
        d.appendChild(mk('span','d', fmtJST(r.date + 'T12:00:00Z', { month:'numeric', day:'numeric', weekday:'short' })));
        if (r.winner){ var w = mk('span','w'); w.appendChild(document.createTextNode('優勝 ')); w.appendChild(mk('b', null, r.winner)); d.appendChild(w); done++; }
        else if (isNow){ d.appendChild(mk('span','flag','今週')); left++; }
        else { d.appendChild(mk('span','flag', r.tbc ? r.tbc : '予定')); left++; }
      }
      box.appendChild(d);
    });
    el('cal-note').textContent = done + '戦終了 · 残り' + left + '戦（中止2戦）';
    var nowEl = box.querySelector('.rd.now');
    if (nowEl){ box.scrollTop = Math.max(0, nowEl.offsetTop - box.offsetTop - 8); }
  }
  function renderSeason(){
    if (!state.season) return;
    el('raceweek').hidden = false;
    renderWeekend(); renderStandings(); renderCalendar(); renderNumbers();
  }
  setInterval(function(){ if (state.season) renderWeekend(); }, 30000);

  function renderTeamFilter(all){
    var box = el('teamfilter'); box.textContent = '';
    if (!state.teamOrder.length) return;
    var counts = {};
    all.forEach(function(a){ (a.teams || []).forEach(function(k){ counts[k] = (counts[k] || 0) + 1; }); });
    state.teamOrder.forEach(function(k){ var b = teamTag(k, counts[k] || 0); if (b) box.appendChild(b); });
  }

  var PANEL_OF = { '#standings':'standings', '#numbers':'numbers', '#calendar':'calendar', '#teams-band':'teams', '#sources':'teams' };
  var wide = window.matchMedia ? window.matchMedia('not all') : { matches:false };
  if (wide.addEventListener) wide.addEventListener('change', function(){ state.newsShown = 0; renderAll(); });
  function setPanel(k, on){
    document.body.classList.toggle('open-' + k, on);
    var b = document.querySelector('.databar [data-panel="' + k + '"]'); if (b) b.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  Array.prototype.forEach.call(document.querySelectorAll('.databar [data-panel]'), function(b){
    b.addEventListener('click', function(){
      var k = b.getAttribute('data-panel'), on = !document.body.classList.contains('open-' + k);
      setPanel(k, on);
      if (on && k === 'teams'){ var t = el('teams-band'); if (t) t.scrollIntoView({ behavior:'smooth', block:'start' }); }
    });
  });
  Array.prototype.forEach.call(document.querySelectorAll('.jump a'), function(a){
    var KJ = { '#tech':'tech', '#gossip':'rumor', '#notes':'analysis' }[a.getAttribute('href')];
    if (KJ){ a.addEventListener('click', function(e){ e.preventDefault(); state.kind = KJ; state.view = 'latest'; renderAll(); goNews(); }); return; }
    a.addEventListener('click', function(e){
      var h = a.getAttribute('href'), k = PANEL_OF[h]; if (k && wide.matches) setPanel(k, true);
      var alt = { '#tech':'#sec-tech', '#gossip':'#sec-rumor' }[h];
      if (alt && wide.matches){ var t = document.querySelector(alt); if (t && !t.classList.contains('empty')){ e.preventDefault(); t.scrollIntoView({ behavior:'smooth', block:'start' }); } }
    });
  });
  function getJSON(u){ return fetch(u, { cache:'no-store' }).then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); }); }
  Promise.all([
    getJSON('articles.json'),
    getJSON('circuits.json').catch(function(){ return { circuits:{} }; }),
    getJSON('teams.json').catch(function(){ return { teams:{}, order:[] }; }),
    getJSON('season.json').catch(function(){ return getJSON('assets/snapshot.json').then(function(s){ return s.season || null; }); })
  ]).catch(function(){
    /* the old fallback copy now sits in its own file, read only when the live data cannot be read (owner's OK, 20 Nov 2026) */
    return getJSON('assets/snapshot.json').then(function(s){
      state.fromSnapshot = true;
      return [s.articles, s.circuits, s.teams, s.season || null];
    });
  }).then(function(res){
    state.circuits = res[1].circuits || {};
    state.teams = res[2].teams || {};
    state.teamOrder = (res[2].order || Object.keys(state.teams)).filter(function(k){ return state.teams[k]; });
    state.season = res[3] || null;
    state.data = res[0];
    /* this site's own time for each article (sitePublished), the outlet's time kept as sourcePublished (owner's OK, 20 Nov 2026) */
    try { var stEl = document.getElementById('sitetimes'), stM = stEl ? JSON.parse(stEl.textContent) : {}; (state.data.articles || []).forEach(function(a){ if (stM[a.id]) { a.sourcePublished = a.published; a.published = stM[a.id]; } }); } catch (e) {}
    /* never show a time still to come: a date-only article is set to 12:00 outlet time (owner's OK, 20 Nov 2026) */
    try { var nowIso = new Date().toISOString(); (state.data.articles || []).forEach(function(a){ if (a.published && new Date(a.published) > new Date()) a.published = nowIso; }); } catch (e) {}
    renderAll();
    renderSeason();
    getJSON('notes.json').catch(function(){ return getJSON('assets/snapshot.json').then(function(sn){ return sn.notes || null; }); }).then(function(n){ state.notes = n; renderNotes(); renderAll(); }).catch(function(){});
  }).catch(function(){
    el('updated').textContent = '記事を読み込めませんでした';
    el('hero-title').textContent = '記事を読み込めませんでした。少し時間をおいて、ページを再読み込みしてください。';
  });
})();
