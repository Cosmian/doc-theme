// Inject a promotional banner on every documentation page.
// Background image matches the Eviden Trustway DataProtect hero.
// CTA is product-aware: only KMS has a live demo link.
(function () {
  var path = window.location.pathname;

  // Product detection from URL path
  var product = 'generic';
  if (path.indexOf('/key_management_system/') !== -1 || path.endsWith('/key_management_system')) product = 'kms';
  else if (path.indexOf('/eviden_vm/') !== -1 || path.endsWith('/eviden_vm')) product = 'vm';
  else if (path.indexOf('/eviden_ai/') !== -1 || path.endsWith('/eviden_ai')) product = 'ai';
  else if (path.indexOf('/eviden_enclave/') !== -1 || path.endsWith('/eviden_enclave')) product = 'enclave';
  else if (path.indexOf('/findex/') !== -1 || path.endsWith('/findex')) product = 'findex';
  else if (path.indexOf('/authentication_verifier/') !== -1 || path.endsWith('/authentication_verifier')) product = 'auth';

  var config = {
    kms:   { title: 'Eviden KMS: Next-generation data protection',       cta: 'Launch the live demo',   href: 'https://demo-kms.cosmian.dev/' },
    vm:    { title: 'Eviden VM: Confidential computing made easy',        cta: null,                     href: null },
    ai:    { title: 'Eviden AI: Secure & sovereign AI',                   cta: null,                     href: null },
    enclave: { title: 'Eviden Enclave: Hardware-based security',          cta: null,                     href: null },
    findex: { title: 'Findex: Searchable encryption',                     cta: null,                     href: null },
    auth:  { title: 'Authentication Verifier: Zero-trust access control', cta: null,                     href: null },
    generic: { title: 'Sovereign, high-performance data protection',      cta: null,                     href: null }
  };

  var c = config[product] || config.generic;
  var ctaHtml = '';
  if (c.cta && c.href) {
    ctaHtml =
      '<a class="kms-demo-banner__cta" href="' + c.href + '" target="_blank" rel="noopener">' +
        c.cta +
        '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
      '</a>';
  }

  var tagHtml = product === 'kms'
    ? '<span class="kms-demo-banner__tag">🚀 Try it for free</span>'
    : '';

  var banner = document.createElement('div');
  banner.className = 'kms-demo-banner';
  banner.innerHTML =
    '<div class="kms-demo-banner__bg"></div>' +
    '<div class="kms-demo-banner__content">' +
      tagHtml +
      '<h2 class="kms-demo-banner__title">' + c.title + '</h2>' +
      ctaHtml +
    '</div>';

  var content = document.querySelector('.content');
  if (content) content.insertBefore(banner, content.firstChild);
})();
