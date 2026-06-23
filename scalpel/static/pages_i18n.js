/* ──────────────────────────────────────────────────────────────────────────
   Standalone pages — i18n (pricing, checkout, checkout_done, settings, camos,
   store_indicators). Same approach as improve_i18n.js: reads the shared
   `scalpel_lang` localStorage key so the language choice stays consistent
   across the site, and translates elements tagged with:
     [data-i18n]       → textContent
     [data-i18n-html]  → innerHTML (use when the string has inline markup)
     [data-i18n-ph]    → input placeholder
   Keys are namespaced per page (pricing.*, checkout.*, cdone.*, settings.*,
   camos.*, store.*) plus shared common.* / nav.*.

   Only EN + ES are filled. FR/PT are intentionally left as empty stubs: any
   missing key falls back to the element's English default, so a FR/PT visitor
   sees English until those languages are audited (Task #2).
   ────────────────────────────────────────────────────────────────────────── */
(function () {
  var T = {
    en: {
      // shared
      'nav.backApp': '← Back to app',
      'nav.backPlans': '← Back to plans',
      'common.soon': 'Coming soon',
      'common.annual': 'Annual',
      'common.monthly': 'Monthly',
      'plan.free': 'Free',

      // ── pricing.html ──
      'pricing.doctitle': 'Trader Accelerator — Plans & Pricing',
      'pricing.tagline': 'Trade Analysis Platform',
      'pricing.eyebrow': 'Plans & Pricing',
      'pricing.h1': 'Sharpen how you analyze every setup',
      'pricing.heroSub': 'Start free. Upgrade when you want deeper, daily educational analysis of your setups.',
      'pricing.save20': 'Save 20%',
      'pricing.subMonthly': 'Pay month to month, cancel anytime.',
      'pricing.subAnnual': 'Pay once a year and save 20% — that’s 2 months free on every paid plan.',
      'pricing.perMonth': '/ month',
      'pricing.fFullEngine': 'Full AI feedback engine',
      'pricing.currentPlan': '✓ Current Plan',
      // Free
      'pricing.freeTag': 'For traders just getting started with journaling.',
      'pricing.freeF1': '<strong>1</strong> screenshot analysis per week',
      'pricing.startFree': 'Start free',
      // Standard
      'pricing.stdTag': 'For active traders reviewing setups daily.',
      'pricing.stdBilled': '<s>$300</s> &nbsp;$240 billed yearly',
      'pricing.stdSave': '↓ 20% — you save $60/yr',
      'pricing.stdF1': '<strong>1</strong> screenshot analysis per day',
      'pricing.everythingFree': 'Everything in Free',
      'pricing.chooseStandard': 'Choose Standard',
      // Premium
      'pricing.mostPopular': 'Most Popular',
      'pricing.premTag': 'For serious traders who want deep daily review.',
      'pricing.premBilled': '<s>$600</s> &nbsp;$480 billed yearly',
      'pricing.premSave': '↓ 20% — you save $120/yr',
      'pricing.premF1': 'Up to <strong>5 screenshot analyses per day</strong>',
      'pricing.premForum': '<strong>Trading Forum</strong> — AI-moderated community to share setups &amp; ideas',
      'pricing.premScout': '<strong>Prop Firm Scout</strong> — filter &amp; compare 25+ prop firms with AI advisor chat',
      'pricing.everythingStandard': 'Everything in Standard',
      'pricing.premIndicators': 'Indicators library <span class="label-soon">soon</span>',
      'pricing.goPremium': 'Go Premium',
      // Compare table
      'pricing.compareTitle': 'Compare all features',
      'pricing.compareSub': 'Same feature, same row — see exactly what each plan includes.',
      'pricing.soon': 'soon',
      'pricing.val1week': '1 / week',
      'pricing.val1day': '1 / day',
      'pricing.val5day': '5 / day',
      'pricing.cmpAnalyses': 'Screenshot analyses',
      'pricing.cmpAnalysesNote': 'AI chart review',
      'pricing.cmpProjects': 'Saved analysis projects',
      'pricing.cmpProjectsNote': 'reusable setup presets',
      'pricing.cmpPreflight': 'Pre-Flight checklist',
      'pricing.cmpPreflightNote': 'discipline trainer & stats',
      'pricing.cmpForum': 'Trading Forum',
      'pricing.cmpForumNote': 'AI-moderated community',
      'pricing.cmpQuiz': 'Quiz Academy',
      'pricing.cmpQuizNote': 'every methodology + Hardcore',
      'pricing.cmpDaily': 'Daily Challenge & Roulette',
      'pricing.cmpChalkboard': 'Chalkboard',
      'pricing.cmpChalkboardNote': 'visual study whiteboards',
      'pricing.cmpSynapseNote': '3D study experience',
      'pricing.cmpIndicators': 'Indicators library',
      'pricing.cmpScout': 'Prop Firm Scout',
      'pricing.cmpScoutNote': 'compare 25+ firms + AI advisor',
      'pricing.cmpCamosNote': 'dashboard design themes',
      'pricing.footNote': 'Plans shown are introductory. Billing is not active yet — these tiers preview what Trader Accelerator will offer. For educational purposes only; not financial advice.',
      'pricing.footer': 'TRADER ACCELERATOR · Trade Analysis Platform · For educational purposes only · Not financial advice<br><span style="opacity:.65">&copy; 2026 Trader Accelerator. All rights reserved.</span>',

      // ── store_indicators.html ──
      'store.doctitle': 'Trader Accelerator — Indicators',
      'store.eyebrow': 'Store',
      'store.title': 'Indicators',
      'store.hero': 'A dedicated storefront for premium trading indicators — separate from the in-app Indicators section. Browse, preview and purchase indicators here.',
      'store.ph': '<strong>Indicators store — coming soon.</strong><br />This is a standalone page (distinct from the in-app Indicators tab) where the indicator catalog, pricing and checkout will live.',

      // ── camos.html ──
      'camos.doctitle': 'Trader Accelerator — Camos',
      'camos.eyebrow': 'Website Skins',
      'camos.title': 'Camos',
      'camos.hero': 'Custom visual themes for your Trader Accelerator workspace. Unlock a skin and restyle the entire website to match your style. More designs coming soon.',
      'camos.navyDesc': 'A disciplined, military-grade navy theme across the whole platform.',
      'camos.desertDesc': 'Warm tactical desert tones for a focused trading session.',
      'camos.forestDesc': 'Deep woodland green camo for a calm, grounded interface.',
      'camos.getSkin': 'Get this skin',

      // ── settings.html ──
      'settings.doctitle': 'Trader Accelerator — Settings',
      'settings.title': 'Settings',
      'settings.flashCancelled': "Plan cancellation scheduled — you'll keep access until your billing period ends.",
      'settings.flashReactivated': 'Plan reactivated — your subscription will continue normally.',
      'settings.secAccount': 'Account',
      'settings.email': 'Email',
      'settings.password': 'Password',
      'settings.passwordDesc': 'Change your password.',
      'settings.subscription': 'Subscription',
      'settings.cancelling': 'Cancelling',
      'settings.accessEnds': '⚠ Access ends',
      'settings.renews': 'Renews',
      'settings.upgrade': 'Upgrade →',
      'settings.reactivate': 'Reactivate',
      'settings.cancelPlan': 'Cancel plan',
      'settings.cancelConfirm': 'Cancel your plan? You keep access until {date}. No refund will be issued.',
      'settings.cancelConfirmNoDate': 'Cancel your plan? You keep access until the end of your period. No refund will be issued.',
      'settings.secPrefs': 'Preferences',
      'settings.language': 'Language',
      'settings.languageDesc': 'Interface language (EN / ES / FR / PT).',
      'settings.theme': 'Theme',
      'settings.themeDesc': 'Dark or light mode (toggle available in-app).',
      'settings.activeCamo': 'Active Camo',
      'settings.activeCamoDesc': 'Choose a purchased website skin.',
      'settings.browseCamos': 'Browse Camos →',
      'settings.secNotif': 'Notifications',
      'settings.emailNotif': 'Email notifications',
      'settings.emailNotifDesc': 'Analysis results and important updates.',
      'settings.secDanger': 'Danger zone',
      'settings.deleteAccount': 'Delete account',
      'settings.deleteAccountDesc': 'Permanently remove your account and all data.',

      // ── checkout.html ──
      'checkout.doctitle': 'Trader Accelerator — Checkout',
      'checkout.eyebrow': 'Checkout',
      'checkout.title': 'Review your order',
      'checkout.planBilledYearly': 'plan (billed yearly)',
      'checkout.planBilledMonthly': 'plan (billed monthly)',
      'checkout.discount': 'Discount',
      'checkout.total': 'Total',
      'checkout.perYear': '/ year',
      'checkout.perMonth': '/ month',
      'checkout.promoLabel': 'Have a discount or creator code?',
      'checkout.promoPlaceholder': 'Enter code',
      'checkout.promoApply': 'Apply',
      'checkout.promoApplied': 'Applied',
      'checkout.promoNote': 'Creator codes support the trader who referred you and may unlock a discount.',
      'checkout.continue': 'Continue to payment →',
      'checkout.infoLine': "You'll receive payment instructions on the next step. Your plan activates once payment is confirmed by our team.",
      'checkout.agreePre': 'By continuing you agree to our',
      'checkout.terms': 'Terms & Conditions',
      // promo JS feedback
      'checkout.discountLabel': 'Discount',
      'checkout.codeApplied': '✓ Code applied — you save ${saved}.',
      'checkout.err.not_found': 'That code does not exist.',
      'checkout.err.expired': 'That code has expired.',
      'checkout.err.maxed': 'That code has reached its usage limit.',
      'checkout.err.inactive': 'That code is no longer active.',
      'checkout.err.cycle': 'That code is not valid for this billing cycle.',
      'checkout.err.empty': 'Please enter a code.',
      'checkout.err.generic': 'That code could not be applied.',

      // ── checkout_done.html ──
      'cdone.doctitle': 'Trader Accelerator — Order received',
      'cdone.dup': 'You already have a pending order awaiting payment confirmation. Complete that one first — here are its details. If you think this is a mistake, <a href="/contact">contact support</a>.',
      'cdone.title': 'Order received',
      'cdone.sub': 'Your order is reserved. Complete payment to activate your plan.',
      'cdone.orderId': 'Order ID',
      'cdone.plan': 'Plan',
      'cdone.promoCode': 'Promo code',
      'cdone.amountDue': 'Amount due',
      'cdone.payTitle': '⏳ Payment instructions',
      'cdone.step1a': 'Send',
      'cdone.step1b': 'in USDT to our Binance account.',
      'cdone.step2a': 'Include your',
      'cdone.step2b': 'in the payment note.',
      'cdone.orderIdInline': 'Order ID',
      'cdone.step3a': 'Send the payment proof through our',
      'cdone.contactForm': 'contact form',
      'cdone.step3b': ', selecting "Billing".',
      'cdone.step4': 'Our team verifies and activates your plan — usually within a few hours.',
      'cdone.backApp': 'Back to app',
      'cdone.sendProof': 'Send payment proof →'
    },

    es: {
      // shared
      'nav.backApp': '← Volver a la app',
      'nav.backPlans': '← Volver a los planes',
      'common.soon': 'Muy pronto',
      'common.annual': 'Anual',
      'common.monthly': 'Mensual',
      'plan.free': 'Gratis',

      // ── pricing.html ──
      'pricing.doctitle': 'Trader Accelerator — Planes y precios',
      'pricing.tagline': 'Plataforma de análisis de trading',
      'pricing.eyebrow': 'Planes y precios',
      'pricing.h1': 'Afina cómo analizas cada setup',
      'pricing.heroSub': 'Empieza gratis. Mejora tu plan cuando quieras un análisis educativo más profundo y diario de tus setups.',
      'pricing.save20': 'Ahorra 20%',
      'pricing.subMonthly': 'Paga mes a mes, cancela cuando quieras.',
      'pricing.subAnnual': 'Paga una vez al año y ahorra 20% — son 2 meses gratis en cada plan de pago.',
      'pricing.perMonth': '/ mes',
      'pricing.fFullEngine': 'Motor completo de feedback con IA',
      'pricing.currentPlan': '✓ Plan actual',
      // Free
      'pricing.freeTag': 'Para traders que recién empiezan a llevar su diario.',
      'pricing.freeF1': '<strong>1</strong> análisis de captura por semana',
      'pricing.startFree': 'Empieza gratis',
      // Standard
      'pricing.stdTag': 'Para traders activos que revisan setups a diario.',
      'pricing.stdBilled': '<s>$300</s> &nbsp;$240 facturados al año',
      'pricing.stdSave': '↓ 20% — ahorras $60/año',
      'pricing.stdF1': '<strong>1</strong> análisis de captura por día',
      'pricing.everythingFree': 'Todo lo de Gratis',
      'pricing.chooseStandard': 'Elegir Standard',
      // Premium
      'pricing.mostPopular': 'Más popular',
      'pricing.premTag': 'Para traders serios que quieren una revisión diaria profunda.',
      'pricing.premBilled': '<s>$600</s> &nbsp;$480 facturados al año',
      'pricing.premSave': '↓ 20% — ahorras $120/año',
      'pricing.premF1': 'Hasta <strong>5 análisis de captura por día</strong>',
      'pricing.premForum': '<strong>Foro de Trading</strong> — comunidad moderada por IA para compartir setups e ideas',
      'pricing.premScout': '<strong>Prop Firm Scout</strong> — filtra y compara más de 25 prop firms con un chat asesor con IA',
      'pricing.everythingStandard': 'Todo lo de Standard',
      'pricing.premIndicators': 'Biblioteca de indicadores <span class="label-soon">pronto</span>',
      'pricing.goPremium': 'Pásate a Premium',
      // Compare table
      'pricing.compareTitle': 'Compara todas las funciones',
      'pricing.compareSub': 'Misma función, misma fila — mira exactamente qué incluye cada plan.',
      'pricing.soon': 'pronto',
      'pricing.val1week': '1 / semana',
      'pricing.val1day': '1 / día',
      'pricing.val5day': '5 / día',
      'pricing.cmpAnalyses': 'Análisis de capturas',
      'pricing.cmpAnalysesNote': 'revisión de gráficos con IA',
      'pricing.cmpProjects': 'Proyectos de análisis guardados',
      'pricing.cmpProjectsNote': 'presets de setup reutilizables',
      'pricing.cmpPreflight': 'Checklist Pre-Flight',
      'pricing.cmpPreflightNote': 'entrenador de disciplina y estadísticas',
      'pricing.cmpForum': 'Foro de Trading',
      'pricing.cmpForumNote': 'comunidad moderada por IA',
      'pricing.cmpQuiz': 'Quiz Academy',
      'pricing.cmpQuizNote': 'todas las metodologías + Hardcore',
      'pricing.cmpDaily': 'Reto diario y Ruleta',
      'pricing.cmpChalkboard': 'Pizarra',
      'pricing.cmpChalkboardNote': 'pizarras visuales de estudio',
      'pricing.cmpSynapseNote': 'experiencia de estudio en 3D',
      'pricing.cmpIndicators': 'Biblioteca de indicadores',
      'pricing.cmpScout': 'Prop Firm Scout',
      'pricing.cmpScoutNote': 'compara más de 25 firms + asesor con IA',
      'pricing.cmpCamosNote': 'temas de diseño del panel',
      'pricing.footNote': 'Los planes mostrados son introductorios. La facturación aún no está activa — estos niveles son una vista previa de lo que ofrecerá Trader Accelerator. Solo con fines educativos; no es asesoría financiera.',
      'pricing.footer': 'TRADER ACCELERATOR · Plataforma de análisis de trading · Solo con fines educativos · No es asesoría financiera<br><span style="opacity:.65">&copy; 2026 Trader Accelerator. Todos los derechos reservados.</span>',

      // ── store_indicators.html ──
      'store.doctitle': 'Trader Accelerator — Indicadores',
      'store.eyebrow': 'Tienda',
      'store.title': 'Indicadores',
      'store.hero': 'Una tienda dedicada a indicadores de trading premium, separada de la sección de Indicadores dentro de la app. Explora, previsualiza y adquiere indicadores aquí.',
      'store.ph': '<strong>Tienda de indicadores — muy pronto.</strong><br />Esta es una página independiente (distinta de la pestaña de Indicadores dentro de la app) donde estarán el catálogo de indicadores, los precios y el pago.',

      // ── camos.html ──
      'camos.doctitle': 'Trader Accelerator — Camos',
      'camos.eyebrow': 'Skins del sitio',
      'camos.title': 'Camos',
      'camos.hero': 'Temas visuales personalizados para tu espacio de Trader Accelerator. Desbloquea un skin y dale un nuevo estilo a todo el sitio a tu manera. Pronto habrá más diseños.',
      'camos.navyDesc': 'Un tema azul marino, disciplinado y de nivel militar, en toda la plataforma.',
      'camos.desertDesc': 'Tonos cálidos y tácticos del desierto para una sesión de trading enfocada.',
      'camos.forestDesc': 'Camuflaje verde bosque profundo para una interfaz tranquila y centrada.',
      'camos.getSkin': 'Obtener este skin',

      // ── settings.html ──
      'settings.doctitle': 'Trader Accelerator — Configuración',
      'settings.title': 'Configuración',
      'settings.flashCancelled': 'Cancelación del plan programada — conservarás el acceso hasta que termine tu período de facturación.',
      'settings.flashReactivated': 'Plan reactivado — tu suscripción continuará normalmente.',
      'settings.secAccount': 'Cuenta',
      'settings.email': 'Correo',
      'settings.password': 'Contraseña',
      'settings.passwordDesc': 'Cambia tu contraseña.',
      'settings.subscription': 'Suscripción',
      'settings.cancelling': 'Cancelando',
      'settings.accessEnds': '⚠ El acceso termina el',
      'settings.renews': 'Se renueva el',
      'settings.upgrade': 'Mejorar plan →',
      'settings.reactivate': 'Reactivar',
      'settings.cancelPlan': 'Cancelar plan',
      'settings.cancelConfirm': '¿Cancelar tu plan? Conservas el acceso hasta el {date}. No se hará ningún reembolso.',
      'settings.cancelConfirmNoDate': '¿Cancelar tu plan? Conservas el acceso hasta el final de tu período. No se hará ningún reembolso.',
      'settings.secPrefs': 'Preferencias',
      'settings.language': 'Idioma',
      'settings.languageDesc': 'Idioma de la interfaz (EN / ES / FR / PT).',
      'settings.theme': 'Tema',
      'settings.themeDesc': 'Modo claro u oscuro (el interruptor está dentro de la app).',
      'settings.activeCamo': 'Camo activo',
      'settings.activeCamoDesc': 'Elige un skin del sitio que hayas adquirido.',
      'settings.browseCamos': 'Ver Camos →',
      'settings.secNotif': 'Notificaciones',
      'settings.emailNotif': 'Notificaciones por correo',
      'settings.emailNotifDesc': 'Resultados de análisis y novedades importantes.',
      'settings.secDanger': 'Zona de peligro',
      'settings.deleteAccount': 'Eliminar cuenta',
      'settings.deleteAccountDesc': 'Elimina de forma permanente tu cuenta y todos tus datos.',

      // ── checkout.html ──
      'checkout.doctitle': 'Trader Accelerator — Pago',
      'checkout.eyebrow': 'Pago',
      'checkout.title': 'Revisa tu pedido',
      'checkout.planBilledYearly': 'plan (facturación anual)',
      'checkout.planBilledMonthly': 'plan (facturación mensual)',
      'checkout.discount': 'Descuento',
      'checkout.total': 'Total',
      'checkout.perYear': '/ año',
      'checkout.perMonth': '/ mes',
      'checkout.promoLabel': '¿Tienes un código de descuento o de creador?',
      'checkout.promoPlaceholder': 'Ingresa el código',
      'checkout.promoApply': 'Aplicar',
      'checkout.promoApplied': 'Aplicado',
      'checkout.promoNote': 'Los códigos de creador apoyan al trader que te recomendó y pueden desbloquear un descuento.',
      'checkout.continue': 'Continuar al pago →',
      'checkout.infoLine': 'Recibirás las instrucciones de pago en el siguiente paso. Tu plan se activa una vez que nuestro equipo confirme el pago.',
      'checkout.agreePre': 'Al continuar aceptas nuestros',
      'checkout.terms': 'Términos y Condiciones',
      // promo JS feedback
      'checkout.discountLabel': 'Descuento',
      'checkout.codeApplied': '✓ Código aplicado — ahorras ${saved}.',
      'checkout.err.not_found': 'Ese código no existe.',
      'checkout.err.expired': 'Ese código ya expiró.',
      'checkout.err.maxed': 'Ese código alcanzó su límite de usos.',
      'checkout.err.inactive': 'Ese código ya no está activo.',
      'checkout.err.cycle': 'Ese código no es válido para este ciclo de facturación.',
      'checkout.err.empty': 'Por favor ingresa un código.',
      'checkout.err.generic': 'No se pudo aplicar ese código.',

      // ── checkout_done.html ──
      'cdone.doctitle': 'Trader Accelerator — Pedido recibido',
      'cdone.dup': 'Ya tienes un pedido pendiente a la espera de confirmación de pago. Completa ese primero — aquí están sus detalles. Si crees que es un error, <a href="/contact">contacta a soporte</a>.',
      'cdone.title': 'Pedido recibido',
      'cdone.sub': 'Tu pedido está reservado. Completa el pago para activar tu plan.',
      'cdone.orderId': 'N.º de pedido',
      'cdone.plan': 'Plan',
      'cdone.promoCode': 'Código promocional',
      'cdone.amountDue': 'Monto a pagar',
      'cdone.payTitle': '⏳ Instrucciones de pago',
      'cdone.step1a': 'Envía',
      'cdone.step1b': 'en USDT a nuestra cuenta de Binance.',
      'cdone.step2a': 'Incluye tu',
      'cdone.step2b': 'en la nota del pago.',
      'cdone.orderIdInline': 'N.º de pedido',
      'cdone.step3a': 'Envía el comprobante de pago a través de nuestro',
      'cdone.contactForm': 'formulario de contacto',
      'cdone.step3b': ', seleccionando "Facturación".',
      'cdone.step4': 'Nuestro equipo verifica y activa tu plan — normalmente en pocas horas.',
      'cdone.backApp': 'Volver a la app',
      'cdone.sendProof': 'Enviar comprobante de pago →'
    },

    // ── Task #2: fill these by auditing every surface in French / Portuguese.
    //    Empty stubs → missing keys fall back to the English default text.
    fr: {},
    pt: {}
  };

  function getLang() {
    try { var s = localStorage.getItem('scalpel_lang'); if (s && T[s]) return s; } catch (e) {}
    return 'en';
  }

  // Resolve a key for the active lang, falling back to English so partially
  // translated languages (and the FR/PT stubs) never show a blank.
  function str(lang, key) {
    var d = T[lang] || {};
    if (d[key] != null) return d[key];
    return (T.en[key] != null) ? T.en[key] : null;
  }

  function apply(lang) {
    if (!T[lang]) lang = 'en';
    document.documentElement.setAttribute('lang', lang);

    var titleEl = document.querySelector('[data-i18n-title]');
    if (titleEl) {
      var tk = titleEl.getAttribute('data-i18n-title');
      var tv = str(lang, tk);
      if (tv != null) document.title = tv;
    }

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var v = str(lang, el.getAttribute('data-i18n'));
      if (v != null) el.textContent = v;
    });
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var v = str(lang, el.getAttribute('data-i18n-html'));
      if (v != null) el.innerHTML = v;
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(function (el) {
      var v = str(lang, el.getAttribute('data-i18n-ph'));
      if (v != null) el.setAttribute('placeholder', v);
    });
    document.querySelectorAll('.lang-switch [data-lang]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });

    try { localStorage.setItem('scalpel_lang', lang); } catch (e) {}
    try { document.cookie = 'scalpel_lang=' + lang + ';path=/;max-age=31536000;samesite=Lax'; } catch (e) {}
  }

  // Expose a tiny helper so inline page scripts (e.g. checkout promo feedback,
  // settings cancel-confirm) can reuse the same dictionary.
  window.PagesI18n = {
    lang: getLang,
    t: function (key, vars) {
      var s = str(getLang(), key);
      if (s == null) return key;
      if (vars) {
        Object.keys(vars).forEach(function (k) {
          s = s.replace('{' + k + '}', vars[k]);
        });
      }
      return s;
    }
  };

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
