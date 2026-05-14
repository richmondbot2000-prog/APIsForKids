/* Mobile sub-page accordion for the top nav.
   On a narrow viewport (drawer open), a top-level link that carries a
   data-sub attribute (JSON array of {href, label}) expands its sub-pages
   inline on the first tap; the second tap navigates.

   Desktop (>960px) is untouched — the .qb-subnav row beneath the topbar
   handles sub-page navigation there. */
(function () {
  const links = document.querySelectorAll('.qb-nav-link[data-sub]');
  if (!links.length) return;

  links.forEach(a => {
    a.addEventListener('click', function (ev) {
      // Desktop: no interception — let the browser navigate normally.
      if (window.innerWidth > 960) return;
      // Second tap (already expanded): navigate.
      if (a.classList.contains('qb-nav-link--expanded')) return;

      let subs;
      try { subs = JSON.parse(a.dataset.sub); } catch (e) { return; }
      if (!Array.isArray(subs) || !subs.length) return;

      ev.preventDefault();

      // Collapse any other expanded sibling first.
      a.parentNode.querySelectorAll('.qb-nav-link--expanded').forEach(other => {
        if (other === a) return;
        other.classList.remove('qb-nav-link--expanded');
        const list = other.nextElementSibling;
        if (list && list.classList.contains('qb-nav-sublist')) list.remove();
      });

      a.classList.add('qb-nav-link--expanded');
      const list = document.createElement('div');
      list.className = 'qb-nav-sublist';
      const currentHref = location.pathname.split('/').pop();
      subs.forEach(s => {
        const sa = document.createElement('a');
        sa.className = 'qb-nav-sublink';
        if (s.href === currentHref) sa.classList.add('is-active');
        sa.href = s.href;
        sa.textContent = s.label;
        list.appendChild(sa);
      });
      a.parentNode.insertBefore(list, a.nextSibling);
    });
  });
})();
