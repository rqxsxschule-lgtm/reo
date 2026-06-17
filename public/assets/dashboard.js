// Load config.json and populate page elements
async function loadConfig() {
  try {
    const res = await fetch('config.json');
    const cfg = await res.json();
    document.title = cfg.BOT_NAME + ' – Dashboard';
    const brand = document.querySelectorAll('[data-cfg="brand"]');
    brand.forEach(el => el.textContent = cfg.BOT_NAME);
    const desc = document.querySelectorAll('[data-cfg="desc"]');
    desc.forEach(el => el.textContent = cfg.BOT_DESCRIPTION || '');
    // populate links
    const map = {
      invite: cfg.INVITE,
      support: cfg.SUPPORT_SERVER,
      vote: cfg.VOTE,
      privacy: cfg.PRIVACY_POLICY,
      tos: cfg.TERMS_OF_SERVICE
    };
    Object.entries(map).forEach(([k,v]) => {
      const els = document.querySelectorAll('[data-link="'+k+'"]');
      els.forEach(a => a.href = v || '#');
    });
  } catch (e) {
    console.warn('Failed to load config.json', e);
  }
}

document.addEventListener('DOMContentLoaded', loadConfig);
