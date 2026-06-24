/* ──────────────────────────────────────────────────────────────────────────
   Legal pages — i18n (terms.html, privacy.html).
   COURTESY TRANSLATIONS ONLY. The English version is the single authoritative,
   legally-binding text and is what the page serves by default; this script
   swaps in a Spanish / French / Brazilian-Portuguese rendering for readability
   when the visitor's chosen language (localStorage `scalpel_lang`) is es/fr/pt.
   A "controlling language" notice on every translated view states that, in case
   of any discrepancy, the English version prevails.

   Mechanism: elements carry [data-i18n] (textContent) or [data-i18n-html]
   (innerHTML). On first run each element's ORIGINAL English content is cached,
   so only es/fr/pt strings live here — English is never duplicated, and
   switching back to English restores the authoritative source exactly. Any key
   without a translation falls back to that cached English (safe default).
   ────────────────────────────────────────────────────────────────────────── */
(function () {
  var T = {
    es: {
      // ── terms.html — header / banner / TOC / section titles ──
      'terms.doctitle': 'Trader Accelerator — Términos y Condiciones',
      'terms.eyebrow': 'Legal',
      'terms.h1': 'Términos y Condiciones',
      'terms.updated': 'Última actualización: 13 de junio de 2026',
      'terms.intro': 'Lee estos Términos y Condiciones con atención antes de usar Trader Accelerator. Al crear una cuenta o acceder a cualquier parte del Servicio, aceptas quedar obligado por estos Términos. Si no estás de acuerdo, no uses el Servicio.',
      'terms.controlling': '<strong>Idioma rector:</strong> El idioma rector de estos Términos es el <strong>inglés</strong>. Cualquier traducción se ofrece únicamente por conveniencia y carece de efecto legal. En caso de conflicto o discrepancia entre la versión en inglés y cualquier traducción, prevalecerá la versión en inglés.',
      'terms.tocTitle': 'Índice',
      'terms.toc1': 'Aceptación de los Términos',
      'terms.toc2': 'Descripción del Servicio — Aviso educativo',
      'terms.toc3': 'Elegibilidad',
      'terms.toc4': 'Cuentas de usuario',
      'terms.toc5': 'Planes, pagos y facturación',
      'terms.toc6': 'Recompensas promocionales, gamificación y códigos promocionales',
      'terms.toc7': 'Política de reembolsos',
      'terms.toc8': 'Propiedad intelectual y licencia de contenido',
      'terms.toc9': 'Conducta prohibida',
      'terms.toc10': 'Terminación y suspensión',
      'terms.toc11': 'Avisos legales (Disclaimers)',
      'terms.toc12': 'Limitación de responsabilidad',
      'terms.toc13': 'Indemnización',
      'terms.toc14': 'Resolución de disputas — Arbitraje vinculante',
      'terms.toc15': 'Ley aplicable',
      'terms.toc16': 'Modificaciones',
      'terms.toc17': 'Disposiciones generales',
      'terms.toc18': 'Contacto',
      'terms.t1': '<span class="sec-num">1.</span> Aceptación de los Términos',
      'terms.t2': '<span class="sec-num">2.</span> Descripción del Servicio — Aviso educativo',
      'terms.t3': '<span class="sec-num">3.</span> Elegibilidad',
      'terms.t4': '<span class="sec-num">4.</span> Cuentas de usuario',
      'terms.t5': '<span class="sec-num">5.</span> Planes, pagos y facturación',
      'terms.t6': '<span class="sec-num">6.</span> Recompensas promocionales, gamificación y códigos promocionales',
      'terms.t7': '<span class="sec-num">7.</span> Política de reembolsos',
      'terms.t8': '<span class="sec-num">8.</span> Propiedad intelectual y licencia de contenido',
      'terms.t9': '<span class="sec-num">9.</span> Conducta prohibida',
      'terms.t10': '<span class="sec-num">10.</span> Terminación y suspensión',
      'terms.t11': '<span class="sec-num">11.</span> Avisos legales (Disclaimers)',
      'terms.t12': '<span class="sec-num">12.</span> Limitación de responsabilidad',
      'terms.t13': '<span class="sec-num">13.</span> Indemnización',
      'terms.t14': '<span class="sec-num">14.</span> Resolución de disputas — Arbitraje vinculante',
      'terms.t15': '<span class="sec-num">15.</span> Ley aplicable',
      'terms.t16': '<span class="sec-num">16.</span> Modificaciones a estos Términos',
      'terms.t17': '<span class="sec-num">17.</span> Disposiciones generales',
      'terms.t18': '<span class="sec-num">18.</span> Contacto'
    },

    fr: {
      'terms.doctitle': 'Trader Accelerator — Conditions Générales',
      'terms.eyebrow': 'Légal',
      'terms.h1': 'Conditions Générales',
      'terms.updated': 'Dernière mise à jour : 13 juin 2026',
      'terms.intro': "Veuillez lire attentivement ces Conditions Générales avant d'utiliser Trader Accelerator. En créant un compte ou en accédant à toute partie du Service, vous acceptez d'être lié par ces Conditions. Si vous n'êtes pas d'accord, n'utilisez pas le Service.",
      'terms.controlling': "<strong>Langue faisant foi :</strong> La langue faisant foi de ces Conditions est l'<strong>anglais</strong>. Toute traduction est fournie à titre de commodité uniquement et n'a aucune valeur juridique. En cas de conflit ou de divergence entre la version anglaise et une traduction, la version anglaise prévaut.",
      'terms.tocTitle': 'Table des matières',
      'terms.toc1': 'Acceptation des Conditions',
      'terms.toc2': 'Description du Service — Avertissement éducatif',
      'terms.toc3': 'Éligibilité',
      'terms.toc4': 'Comptes utilisateur',
      'terms.toc5': 'Offres, paiements et facturation',
      'terms.toc6': 'Récompenses promotionnelles, gamification et codes promotionnels',
      'terms.toc7': 'Politique de remboursement',
      'terms.toc8': 'Propriété intellectuelle et licence de contenu',
      'terms.toc9': 'Conduite interdite',
      'terms.toc10': 'Résiliation et suspension',
      'terms.toc11': 'Avertissements (Disclaimers)',
      'terms.toc12': 'Limitation de responsabilité',
      'terms.toc13': 'Indemnisation',
      'terms.toc14': 'Résolution des litiges — Arbitrage exécutoire',
      'terms.toc15': 'Droit applicable',
      'terms.toc16': 'Modifications',
      'terms.toc17': 'Dispositions générales',
      'terms.toc18': 'Contact',
      'terms.t1': '<span class="sec-num">1.</span> Acceptation des Conditions',
      'terms.t2': '<span class="sec-num">2.</span> Description du Service — Avertissement éducatif',
      'terms.t3': '<span class="sec-num">3.</span> Éligibilité',
      'terms.t4': '<span class="sec-num">4.</span> Comptes utilisateur',
      'terms.t5': '<span class="sec-num">5.</span> Offres, paiements et facturation',
      'terms.t6': '<span class="sec-num">6.</span> Récompenses promotionnelles, gamification et codes promotionnels',
      'terms.t7': '<span class="sec-num">7.</span> Politique de remboursement',
      'terms.t8': '<span class="sec-num">8.</span> Propriété intellectuelle et licence de contenu',
      'terms.t9': '<span class="sec-num">9.</span> Conduite interdite',
      'terms.t10': '<span class="sec-num">10.</span> Résiliation et suspension',
      'terms.t11': '<span class="sec-num">11.</span> Avertissements (Disclaimers)',
      'terms.t12': '<span class="sec-num">12.</span> Limitation de responsabilité',
      'terms.t13': '<span class="sec-num">13.</span> Indemnisation',
      'terms.t14': '<span class="sec-num">14.</span> Résolution des litiges — Arbitrage exécutoire',
      'terms.t15': '<span class="sec-num">15.</span> Droit applicable',
      'terms.t16': '<span class="sec-num">16.</span> Modifications de ces Conditions',
      'terms.t17': '<span class="sec-num">17.</span> Dispositions générales',
      'terms.t18': '<span class="sec-num">18.</span> Contact'
    },

    pt: {
      'terms.doctitle': 'Trader Accelerator — Termos e Condições',
      'terms.eyebrow': 'Legal',
      'terms.h1': 'Termos e Condições',
      'terms.updated': 'Última atualização: 13 de junho de 2026',
      'terms.intro': 'Leia estes Termos e Condições com atenção antes de usar o Trader Accelerator. Ao criar uma conta ou acessar qualquer parte do Serviço, você concorda em se vincular a estes Termos. Se você não concordar, não use o Serviço.',
      'terms.controlling': '<strong>Idioma prevalecente:</strong> O idioma prevalecente destes Termos é o <strong>inglês</strong>. Qualquer tradução é fornecida apenas por conveniência e não tem efeito legal. Em caso de conflito ou divergência entre a versão em inglês e qualquer tradução, prevalecerá a versão em inglês.',
      'terms.tocTitle': 'Índice',
      'terms.toc1': 'Aceitação dos Termos',
      'terms.toc2': 'Descrição do Serviço — Aviso educativo',
      'terms.toc3': 'Elegibilidade',
      'terms.toc4': 'Contas de usuário',
      'terms.toc5': 'Planos, pagamentos e cobrança',
      'terms.toc6': 'Recompensas promocionais, gamificação e códigos promocionais',
      'terms.toc7': 'Política de reembolso',
      'terms.toc8': 'Propriedade intelectual e licença de conteúdo',
      'terms.toc9': 'Conduta proibida',
      'terms.toc10': 'Rescisão e suspensão',
      'terms.toc11': 'Avisos legais (Disclaimers)',
      'terms.toc12': 'Limitação de responsabilidade',
      'terms.toc13': 'Indenização',
      'terms.toc14': 'Resolução de disputas — Arbitragem vinculante',
      'terms.toc15': 'Lei aplicável',
      'terms.toc16': 'Modificações',
      'terms.toc17': 'Disposições gerais',
      'terms.toc18': 'Contato',
      'terms.t1': '<span class="sec-num">1.</span> Aceitação dos Termos',
      'terms.t2': '<span class="sec-num">2.</span> Descrição do Serviço — Aviso educativo',
      'terms.t3': '<span class="sec-num">3.</span> Elegibilidade',
      'terms.t4': '<span class="sec-num">4.</span> Contas de usuário',
      'terms.t5': '<span class="sec-num">5.</span> Planos, pagamentos e cobrança',
      'terms.t6': '<span class="sec-num">6.</span> Recompensas promocionais, gamificação e códigos promocionais',
      'terms.t7': '<span class="sec-num">7.</span> Política de reembolso',
      'terms.t8': '<span class="sec-num">8.</span> Propriedade intelectual e licença de conteúdo',
      'terms.t9': '<span class="sec-num">9.</span> Conduta proibida',
      'terms.t10': '<span class="sec-num">10.</span> Rescisão e suspensão',
      'terms.t11': '<span class="sec-num">11.</span> Avisos legais (Disclaimers)',
      'terms.t12': '<span class="sec-num">12.</span> Limitação de responsabilidade',
      'terms.t13': '<span class="sec-num">13.</span> Indenização',
      'terms.t14': '<span class="sec-num">14.</span> Resolução de disputas — Arbitragem vinculante',
      'terms.t15': '<span class="sec-num">15.</span> Lei aplicável',
      'terms.t16': '<span class="sec-num">16.</span> Modificações destes Termos',
      'terms.t17': '<span class="sec-num">17.</span> Disposições gerais',
      'terms.t18': '<span class="sec-num">18.</span> Contato'
    }
  };

  function getLang() {
    try { var s = localStorage.getItem('scalpel_lang'); if (s) return s; } catch (e) {}
    return 'en';
  }

  function apply(lang) {
    if (lang !== 'es' && lang !== 'fr' && lang !== 'pt') lang = 'en';
    document.documentElement.setAttribute('lang', lang);
    var dict = T[lang] || {};

    var titleEl = document.querySelector('[data-i18n-title]');
    if (titleEl) {
      var tk = titleEl.getAttribute('data-i18n-title');
      if (!titleEl.__enTitle) titleEl.__enTitle = document.title;
      document.title = (lang !== 'en' && dict[tk] != null) ? dict[tk] : titleEl.__enTitle;
    }

    function swap(attr, isHtml) {
      document.querySelectorAll('[' + attr + ']').forEach(function (el) {
        var key = el.getAttribute(attr);
        if (el.__en == null) el.__en = isHtml ? el.innerHTML : el.textContent;
        var v = (lang !== 'en' && dict[key] != null) ? dict[key] : el.__en;
        if (isHtml) el.innerHTML = v; else el.textContent = v;
      });
    }
    swap('data-i18n', false);
    swap('data-i18n-html', true);

    document.querySelectorAll('.lang-switch [data-lang]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });

    try { localStorage.setItem('scalpel_lang', lang); } catch (e) {}
    try { document.cookie = 'scalpel_lang=' + lang + ';path=/;max-age=31536000;samesite=Lax'; } catch (e) {}
  }

  function init() {
    apply(getLang());
    document.querySelectorAll('.lang-switch [data-lang]').forEach(function (b) {
      b.addEventListener('click', function () { apply(b.getAttribute('data-lang')); });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
