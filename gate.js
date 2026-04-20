(function(){
  var KEY = 'cc_gate_v1';
  var PASS = 'cine';
  if(sessionStorage.getItem(KEY) === 'ok' || localStorage.getItem(KEY) === 'ok') return;

  var style = document.createElement('style');
  style.textContent =
    '#cc-gate-host{position:fixed;inset:0;z-index:2147483647;display:flex;align-items:center;justify-content:center;background:rgba(8,10,18,0.72);backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);font-family:Inter,system-ui,sans-serif;color:#e5e9f0}' +
    'html.cc-locked,html.cc-locked body{overflow:hidden!important;height:100%}' +
    '#cc-gate-card{position:relative;padding:40px 44px 36px;border-radius:18px;background:linear-gradient(180deg,rgba(21,29,46,0.92),rgba(13,18,32,0.92));border:1px solid rgba(212,160,82,0.35);box-shadow:0 40px 80px -20px rgba(0,0,0,0.65),0 0 120px -30px rgba(212,160,82,0.35);min-width:320px;text-align:center}' +
    '#cc-gate-card::before{content:"";position:absolute;inset:-1px;border-radius:18px;padding:1px;background:linear-gradient(135deg,rgba(212,160,82,0.55),transparent 60%);-webkit-mask:linear-gradient(#000,#000) content-box,linear-gradient(#000,#000);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}' +
    '#cc-gate-mark{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10px;letter-spacing:4px;color:#d4a052;text-transform:uppercase;font-weight:700;margin-bottom:14px;opacity:0.9}' +
    '#cc-gate-title{font-family:"Space Grotesk",Inter,sans-serif;font-size:22px;font-weight:700;letter-spacing:-0.01em;margin-bottom:6px;line-height:1.2}' +
    '#cc-gate-sub{font-size:12px;color:#94a3b8;margin-bottom:22px;font-family:"JetBrains Mono",monospace;letter-spacing:1px}' +
    '#cc-gate-input{width:240px;padding:14px 18px;text-align:center;font-family:"JetBrains Mono",monospace;font-size:20px;letter-spacing:10px;text-transform:lowercase;background:rgba(10,14,23,0.7);border:1px solid rgba(212,160,82,0.3);border-radius:10px;color:#e5e9f0;outline:none;caret-color:#d4a052;transition:border-color 0.2s,box-shadow 0.2s}' +
    '#cc-gate-input:focus{border-color:#d4a052;box-shadow:0 0 0 3px rgba(212,160,82,0.15)}' +
    '#cc-gate-input.shake{animation:ccGateShake 0.45s cubic-bezier(.36,.07,.19,.97)}' +
    '#cc-gate-input.shake{border-color:#f87171;box-shadow:0 0 0 3px rgba(248,113,113,0.18)}' +
    '@keyframes ccGateShake{10%,90%{transform:translateX(-2px)}20%,80%{transform:translateX(3px)}30%,50%,70%{transform:translateX(-6px)}40%,60%{transform:translateX(6px)}}' +
    '#cc-gate-hint{font-size:10px;color:#64748b;margin-top:14px;font-family:"JetBrains Mono",monospace;letter-spacing:1.5px;text-transform:uppercase}' +
    '#cc-gate-dots{display:flex;gap:8px;justify-content:center;margin-top:16px}' +
    '#cc-gate-dots span{width:8px;height:8px;border-radius:50%;background:rgba(212,160,82,0.18);transition:background 0.2s}' +
    '#cc-gate-dots span.on{background:#d4a052;box-shadow:0 0 8px rgba(212,160,82,0.5)}';
  document.head.appendChild(style);

  function mount(){
    document.documentElement.classList.add('cc-locked');
    var host = document.createElement('div');
    host.id = 'cc-gate-host';
    host.innerHTML =
      '<div id="cc-gate-card" role="dialog" aria-modal="true" aria-labelledby="cc-gate-title">' +
        '<div id="cc-gate-mark">CHAOSCONSOLE · PRIVATE</div>' +
        '<div id="cc-gate-title">Enter the 4-letter key</div>' +
        '<div id="cc-gate-sub">a word, not a number</div>' +
        '<input id="cc-gate-input" maxlength="4" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" inputmode="text" aria-label="Password" />' +
        '<div id="cc-gate-dots"><span></span><span></span><span></span><span></span></div>' +
        '<div id="cc-gate-hint">Press enter to unlock</div>' +
      '</div>';
    document.body.appendChild(host);

    var input = document.getElementById('cc-gate-input');
    var dots = document.querySelectorAll('#cc-gate-dots span');
    input.focus();

    function tryUnlock(){
      var v = (input.value || '').trim().toLowerCase();
      if(v === PASS){
        localStorage.setItem(KEY, 'ok');
        sessionStorage.setItem(KEY, 'ok');
        document.documentElement.classList.remove('cc-locked');
        host.style.transition = 'opacity 0.35s ease';
        host.style.opacity = '0';
        setTimeout(function(){ host.remove(); }, 360);
      } else {
        input.classList.remove('shake');
        // force reflow
        void input.offsetWidth;
        input.classList.add('shake');
        setTimeout(function(){ input.value = ''; dots.forEach(function(d){ d.classList.remove('on'); }); input.focus(); }, 500);
      }
    }

    input.addEventListener('input', function(){
      var n = (input.value || '').length;
      dots.forEach(function(d, i){ d.classList.toggle('on', i < n); });
      if(n === 4) tryUnlock();
    });
    input.addEventListener('keydown', function(e){
      if(e.key === 'Enter') tryUnlock();
    });
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
