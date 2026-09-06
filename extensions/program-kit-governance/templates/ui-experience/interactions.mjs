// Native dialog owns modal semantics and Escape; keep Tab at the content edges and restore focus.
export function wireDialogs(root = document) {
  const cleanups = [];
  for (const opener of root.querySelectorAll('[data-pk-dialog]')) {
    const dialog = root.getElementById(opener.dataset.pkDialog);
    if (!(dialog instanceof HTMLDialogElement)) throw new Error('Missing native dialog');
    const open = () => dialog.showModal();
    const close = () => opener.focus();
    const wrap = event => {
      if (event.key !== 'Tab') return;
      const targets = [...dialog.querySelectorAll('a[href],button,input,select,textarea,[tabindex],[contenteditable="true"]')]
        .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length);
      const first = targets[0], last = targets.at(-1);
      if (!first) { event.preventDefault(); dialog.focus(); return; }
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    opener.addEventListener('click', open);
    dialog.addEventListener('close', close);
    dialog.addEventListener('keydown', wrap);
    cleanups.push(() => { opener.removeEventListener('click', open); dialog.removeEventListener('close', close); dialog.removeEventListener('keydown', wrap); });
  }
  return () => cleanups.forEach(cleanup => cleanup());
}
if (typeof document !== 'undefined') wireDialogs();
