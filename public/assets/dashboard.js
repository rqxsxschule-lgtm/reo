// Load config.json and populate page elements
async function loadConfig() {
  try {
    const res = await fetch('/config.json');
    const cfg = await res.json();
    document.title = cfg.BOT_NAME + ' – Dashboard';
    const brand = document.querySelectorAll('[data-cfg="brand"]');
    brand.forEach(el => el.textContent = cfg.BOT_NAME);
    const desc = document.querySelectorAll('[data-cfg="desc"]');
    desc.forEach(el => el.textContent = cfg.BOT_DESCRIPTION || '');
    // populate links
    const map = {
      invite: cfg.INVITE,
      dashboard: cfg.DASHBOARD || cfg.WEBSITE,
      support: cfg.SUPPORT_SERVER,
      vote: cfg.VOTE,
      privacy: cfg.PRIVACY_POLICY,
      tos: cfg.TERMS_OF_SERVICE
    };
    Object.entries(map).forEach(([k,v]) => {
      const els = document.querySelectorAll('[data-link="'+k+'"]');
      els.forEach(a => a.href = v || '#');
    });

    if (cfg.DASHBOARD) {
      const dashboardButton = document.querySelector('[data-link="dashboard"]');
      if (!dashboardButton) {
        const buttons = document.querySelector('.buttons');
        if (buttons) {
          const button = document.createElement('a');
          button.className = 'ghost-btn';
          button.href = cfg.DASHBOARD;
          button.textContent = 'Dashboard';
          button.style.minWidth = '180px';
          buttons.appendChild(button);
        }
      }
    }
  } catch (e) {
    console.warn('Failed to load config.json', e);
  }
}

document.addEventListener('DOMContentLoaded', loadConfig);

// Mark current language button active and add small load animations
document.addEventListener('DOMContentLoaded', () => {
  try {
    const path = window.location.pathname || '/';
    const en = document.getElementById('lang-en');
    const de = document.getElementById('lang-de');
    if (en) en.classList.toggle('active', path.startsWith('/en'));
    if (de) de.classList.toggle('active', path.startsWith('/de'));

    // Slight staggered animation for panels
    const panels = Array.from(document.querySelectorAll('.panel'));
    panels.forEach((p, i) => {
      p.style.animationDelay = (i * 40) + 'ms';
    });
    // Load and apply locale for static pages
    try {
      const lang = path.startsWith('/de') ? 'de' : 'en';
      fetch(`/locales/${lang}.json`).then(r => r.ok ? r.json() : {}).then(loc => {
        if (!loc) return;
        // replace data-i18n text
        Object.entries(loc).forEach(([key, val]) => {
          const els = document.querySelectorAll(`[data-i18n="${key}"]`);
          els.forEach(el => {
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
              el.value = val;
            } else {
              el.textContent = val;
            }
          });
        });
        // also translate links with data-page or data-link if needed
      }).catch(()=>{});
    } catch (e) {}
  } catch (e) {
    // silent
  }
});
