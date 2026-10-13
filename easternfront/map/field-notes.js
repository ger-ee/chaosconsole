// Native two-axis scrolling keeps touch momentum and vertical card reading intact.
// Add grab-to-pan for mouse users without replacing iPad's native touch handling.
let drag;
document.addEventListener('pointerdown', e => {
  const track = e.target.closest('#track');
  if (!track || e.pointerType !== 'mouse' || e.button !== 0) return;
  drag = {track, x:e.clientX, left:track.scrollLeft, moved:false};
});
document.addEventListener('pointermove', e => {
  if (!drag) return;
  const dx=e.clientX-drag.x;
  if (Math.abs(dx)>6) drag.moved=true;
  if (drag.moved) {drag.track.scrollLeft=drag.left-dx;e.preventDefault();}
});
document.addEventListener('click', e => {
  if (drag?.moved) {e.preventDefault();e.stopImmediatePropagation();drag=null;}
},true);
document.addEventListener('pointerup', () => {if(drag) setTimeout(()=>{drag=null;},0);});
document.addEventListener('pointercancel', () => {drag=null;});
// Keep keyboard focus inside the reading panel, and restore the originating card.
let previousFocus, openPanel;
new MutationObserver(() => {
  const panel=document.querySelector('aside[role="dialog"]');
  if(panel && panel!==openPanel){previousFocus=document.activeElement;openPanel=panel;panel.focus();}
  else if(!panel && openPanel){openPanel=null;if(previousFocus?.isConnected)previousFocus.focus();}
}).observe(document.body,{childList:true,subtree:true});
document.addEventListener('keydown', e => {
  if(e.key!=='Tab'||!openPanel)return;
  const nodes=[...openPanel.querySelectorAll('button,a[href],input,[tabindex="0"]')];
  const first=nodes[0],last=nodes.at(-1);
  if(e.shiftKey&&(document.activeElement===first||document.activeElement===openPanel)){e.preventDefault();last?.focus();}
  else if(!e.shiftKey&&(document.activeElement===last||document.activeElement===openPanel)){e.preventDefault();first?.focus();}
});
