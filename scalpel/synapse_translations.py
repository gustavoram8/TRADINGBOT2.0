# -*- coding: utf-8 -*-
"""
Synapse Library PDF — translations (chrome + legal + method/title labels).

The English content lives in static/synapse_export.json; per-language topic
content overrides live in static/synapse_content_{lang}.json. This module
holds everything else that the PDF builder needs translated: cover strings,
the full legal notice page, section labels, method names and topic titles.

SVG diagram internal labels (e.g. "neckline", "BOS", "FVG") deliberately stay
in English — trading terminology is native English even in non-English
trading communities, matching the design philosophy of synapse_library.js.
"""

SUPPORTED_LANGS = ('en', 'es', 'fr', 'pt')


# ── UI / chrome strings ──────────────────────────────────────────────────────
CHROME = {
    'en': {
        'cover_sub':       'Complete Trading Knowledge Base',
        'cover_licensed':  'Licensed exclusively to',
        'cover_issued':    'Issued',
        'cover_order':     'Order',
        'cover_confidential': 'CONFIDENTIAL — Unauthorized distribution is strictly prohibited and may result in legal action.',
        'toc_title':       'Table of Contents',
        'methodology':     'Methodology',
        'common_mistake':  'Common mistake',
        'setup_cond':      'Conditions',
        'setup_entry':     'Entry',
        'setup_stop':      'Stop',
        'setup_target':    'Target',
        'footer':          'CONFIDENTIAL — Licensed to: {name} · {email} · Order {order} · Unauthorized distribution is prohibited',
    },
    'es': {
        'cover_sub':       'Base de Conocimiento Completa de Trading',
        'cover_licensed':  'Con licencia exclusiva para',
        'cover_issued':    'Emitido',
        'cover_order':     'Orden',
        'cover_confidential': 'CONFIDENCIAL — Su distribución no autorizada está terminantemente prohibida y puede dar lugar a acciones legales.',
        'toc_title':       'Índice',
        'methodology':     'Metodología',
        'common_mistake':  'Error común',
        'setup_cond':      'Condiciones',
        'setup_entry':     'Entrada',
        'setup_stop':      'Stop',
        'setup_target':    'Objetivo',
        'footer':          'CONFIDENCIAL — Con licencia para: {name} · {email} · Orden {order} · Prohibida su distribución no autorizada',
    },
    'fr': {
        'cover_sub':       'Base Complète de Connaissances en Trading',
        'cover_licensed':  'Sous licence exclusive pour',
        'cover_issued':    'Émis le',
        'cover_order':     'Commande',
        'cover_confidential': 'CONFIDENTIEL — La distribution non autorisée est strictement interdite et peut entraîner des poursuites judiciaires.',
        'toc_title':       'Table des Matières',
        'methodology':     'Méthodologie',
        'common_mistake':  'Erreur fréquente',
        'setup_cond':      'Conditions',
        'setup_entry':     'Entrée',
        'setup_stop':      'Stop',
        'setup_target':    'Objectif',
        'footer':          'CONFIDENTIEL — Sous licence pour : {name} · {email} · Commande {order} · Distribution non autorisée interdite',
    },
    'pt': {
        'cover_sub':       'Base Completa de Conhecimento de Trading',
        'cover_licensed':  'Licenciado exclusivamente para',
        'cover_issued':    'Emitido em',
        'cover_order':     'Pedido',
        'cover_confidential': 'CONFIDENCIAL — A distribuição não autorizada é estritamente proibida e pode resultar em ações legais.',
        'toc_title':       'Sumário',
        'methodology':     'Metodologia',
        'common_mistake':  'Erro comum',
        'setup_cond':      'Condições',
        'setup_entry':     'Entrada',
        'setup_stop':      'Stop',
        'setup_target':    'Alvo',
        'footer':          'CONFIDENCIAL — Licenciado para: {name} · {email} · Pedido {order} · Distribuição não autorizada proibida',
    },
}


# ── Method names (keyed by canonical English name) ───────────────────────────
METHODS = {
    'en': {
        'Price Action': 'Price Action',
        'Technical Analysis': 'Technical Analysis',
        'SMC / ICT': 'SMC / ICT',
        'Fundamental Analysis': 'Fundamental Analysis',
        'Quantitative': 'Quantitative',
    },
    'es': {
        'Price Action': 'Acción del Precio',
        'Technical Analysis': 'Análisis Técnico',
        'SMC / ICT': 'SMC / ICT',
        'Fundamental Analysis': 'Análisis Fundamental',
        'Quantitative': 'Cuantitativo',
    },
    'fr': {
        'Price Action': 'Action des Prix',
        'Technical Analysis': 'Analyse Technique',
        'SMC / ICT': 'SMC / ICT',
        'Fundamental Analysis': 'Analyse Fondamentale',
        'Quantitative': 'Quantitatif',
    },
    'pt': {
        'Price Action': 'Ação do Preço',
        'Technical Analysis': 'Análise Técnica',
        'SMC / ICT': 'SMC / ICT',
        'Fundamental Analysis': 'Análise Fundamental',
        'Quantitative': 'Quantitativo',
    },
}


# ── Topic titles (keyed by slug) ─────────────────────────────────────────────
TITLES = {
    'es': {
        'price.support-resistance': 'Soporte y Resistencia',
        'price.trend-structure': 'Tendencia y Estructura',
        'price.candles': 'Lectura de Velas',
        'price.chart-patterns': 'Patrones Gráficos',
        'price.supply-demand': 'Oferta y Demanda',
        'price.pin-bar': 'Rechazo en Pin Bar',
        'price.engulfing': 'Confirmación por Envolvente',
        'price.breakout-retest': 'Retest de Ruptura',
        'price.harmonic': 'Patrones Armónicos',
        'technical.moving-averages': 'Medias Móviles',
        'technical.rsi': 'RSI',
        'technical.rsi-divergence': 'Divergencia de RSI',
        'technical.macd': 'MACD',
        'technical.macd-cross': 'Cruce de MACD',
        'technical.bollinger': 'Bandas de Bollinger',
        'technical.volume': 'Análisis de Volumen',
        'technical.ma-cross': 'Cruce de Medias',
        'technical.squeeze-break': 'Ruptura de Compresión',
        'smc.order-blocks': 'Order Blocks',
        'smc.ob-retest': 'Retest de Order Block',
        'smc.fair-value-gaps': 'Fair Value Gaps',
        'smc.fvg-fill': 'Relleno de FVG',
        'smc.market-structure': 'Estructura de Mercado (BOS/ChoCH)',
        'smc.liquidity': 'Liquidez',
        'smc.liquidity-sweep': 'Barrido de Liquidez',
        'smc.kill-zones': 'Kill Zones',
        'smc.pd-arrays': 'Premium / Descuento',
        'smc.ote': 'Entrada Óptima (OTE)',
        'smc.wyckoff-roots': 'Raíces de Wyckoff',
        'fundamental.interest-rates': 'Tasas de Interés',
        'fundamental.macro-drivers': 'Motores Macroeconómicos',
        'fundamental.news-data': 'Noticias de Alto Impacto',
        'fundamental.news-fade': 'Reversión tras la Noticia',
        'fundamental.data-continuation': 'Continuación tras el Dato',
        'fundamental.intermarket': 'Análisis Intermercado',
        'quant.probability': 'Probabilidad y Ventaja',
        'quant.risk-of-ruin': 'Riesgo de Ruina',
        'quant.backtesting': 'Backtesting',
        'quant.mean-reversion': 'Reversión a la Media',
        'quant.momentum': 'Momentum',
        'quant.algo-systems': 'Sistemas Algorítmicos',
    },
    'fr': {
        'price.support-resistance': 'Support et Résistance',
        'price.trend-structure': 'Tendance et Structure',
        'price.candles': 'Lecture des Chandeliers',
        'price.chart-patterns': 'Figures Chartistes',
        'price.supply-demand': 'Offre et Demande',
        'price.pin-bar': 'Rejet en Pin Bar',
        'price.engulfing': "Confirmation par Avalement",
        'price.breakout-retest': 'Retest de Cassure',
        'price.harmonic': 'Figures Harmoniques',
        'technical.moving-averages': 'Moyennes Mobiles',
        'technical.rsi': 'RSI',
        'technical.rsi-divergence': 'Divergence du RSI',
        'technical.macd': 'MACD',
        'technical.macd-cross': 'Croisement du MACD',
        'technical.bollinger': 'Bandes de Bollinger',
        'technical.volume': 'Analyse du Volume',
        'technical.ma-cross': 'Croisement de Moyennes',
        'technical.squeeze-break': 'Cassure de Compression',
        'smc.order-blocks': 'Order Blocks',
        'smc.ob-retest': "Retest d'Order Block",
        'smc.fair-value-gaps': 'Fair Value Gaps',
        'smc.fvg-fill': 'Comblement de FVG',
        'smc.market-structure': 'Structure de Marché (BOS/ChoCH)',
        'smc.liquidity': 'Liquidité',
        'smc.liquidity-sweep': 'Balayage de Liquidité',
        'smc.kill-zones': 'Kill Zones',
        'smc.pd-arrays': 'Premium / Discount',
        'smc.ote': 'Entrée Optimale (OTE)',
        'smc.wyckoff-roots': 'Racines de Wyckoff',
        'fundamental.interest-rates': "Taux d'Intérêt",
        'fundamental.macro-drivers': 'Moteurs Macroéconomiques',
        'fundamental.news-data': 'Nouvelles à Fort Impact',
        'fundamental.news-fade': 'Estompage des Nouvelles',
        'fundamental.data-continuation': 'Continuation après la Donnée',
        'fundamental.intermarket': 'Analyse Intermarchés',
        'quant.probability': 'Probabilité et Avantage',
        'quant.risk-of-ruin': 'Risque de Ruine',
        'quant.backtesting': 'Backtesting',
        'quant.mean-reversion': 'Retour à la Moyenne',
        'quant.momentum': 'Momentum',
        'quant.algo-systems': 'Systèmes Algorithmiques',
    },
    'pt': {
        'price.support-resistance': 'Suporte e Resistência',
        'price.trend-structure': 'Tendência e Estrutura',
        'price.candles': 'Leitura de Velas',
        'price.chart-patterns': 'Padrões Gráficos',
        'price.supply-demand': 'Oferta e Demanda',
        'price.pin-bar': 'Rejeição em Pin Bar',
        'price.engulfing': 'Confirmação por Engolfo',
        'price.breakout-retest': 'Reteste de Rompimento',
        'price.harmonic': 'Padrões Harmônicos',
        'technical.moving-averages': 'Médias Móveis',
        'technical.rsi': 'RSI',
        'technical.rsi-divergence': 'Divergência de RSI',
        'technical.macd': 'MACD',
        'technical.macd-cross': 'Cruzamento de MACD',
        'technical.bollinger': 'Bandas de Bollinger',
        'technical.volume': 'Análise de Volume',
        'technical.ma-cross': 'Cruzamento de Médias',
        'technical.squeeze-break': 'Rompimento de Compressão',
        'smc.order-blocks': 'Order Blocks',
        'smc.ob-retest': 'Reteste de Order Block',
        'smc.fair-value-gaps': 'Fair Value Gaps',
        'smc.fvg-fill': 'Preenchimento de FVG',
        'smc.market-structure': 'Estrutura de Mercado (BOS/ChoCH)',
        'smc.liquidity': 'Liquidez',
        'smc.liquidity-sweep': 'Varredura de Liquidez',
        'smc.kill-zones': 'Kill Zones',
        'smc.pd-arrays': 'Premium / Desconto',
        'smc.ote': 'Entrada Ótima (OTE)',
        'smc.wyckoff-roots': 'Raízes de Wyckoff',
        'fundamental.interest-rates': 'Taxas de Juros',
        'fundamental.macro-drivers': 'Fatores Macroeconômicos',
        'fundamental.news-data': 'Notícias de Alto Impacto',
        'fundamental.news-fade': 'Desvanecimento de Notícias',
        'fundamental.data-continuation': 'Continuação após o Dado',
        'fundamental.intermarket': 'Análise Intermercados',
        'quant.probability': 'Probabilidade e Vantagem',
        'quant.risk-of-ruin': 'Risco de Ruína',
        'quant.backtesting': 'Backtesting',
        'quant.mean-reversion': 'Reversão à Média',
        'quant.momentum': 'Momentum',
        'quant.algo-systems': 'Sistemas Algorítmicos',
    },
}


def method_name(method_en, lang):
    return METHODS.get(lang, METHODS['en']).get(method_en, method_en)


def topic_title(slug, title_en, lang):
    if lang == 'en':
        return title_en
    return TITLES.get(lang, {}).get(slug, title_en)


def chrome(lang):
    return CHROME.get(lang, CHROME['en'])


# ── Legal notice page (full HTML, per language) ──────────────────────────────
def legal_page_html(lang, wm_name, wm_email, wm_order, wm_date):
    """Return the full inner HTML for the legal/confidentiality page."""
    year = wm_date[:4]
    L = _LEGAL.get(lang, _LEGAL['en'])
    prohibited_items = ''.join(f'<li>{x}</li>' for x in L['prohibited'])
    consequence_items = ''.join(f'<li>{x}</li>' for x in L['consequences'])
    edu_paras = ''.join(f'<p>{x}</p>' for x in L['edu_body'])
    return f"""
<div class="legal-page">

  <div class="legal-id-box">
    <strong>{L['id_title']}</strong><br/>
    {L['id_licensed']}: <strong>{wm_name}</strong> &nbsp;·&nbsp; {wm_email}<br/>
    {L['id_order']}: <strong>{wm_order}</strong> &nbsp;·&nbsp; {L['id_date']}: {wm_date}<br/>
    {L['id_publisher']}: <strong>Tradeable</strong> &nbsp;·&nbsp; {L['id_product']}: Synapse Library ({L['id_edition']})
  </div>

  <div class="legal-warn">
    <div class="legal-warn-title">⚠ {L['warn_title']}</div>
    <p>{L['warn_intro1']}</p>
    <p>{L['warn_intro2']}</p>
    <ul style="padding-left:14pt;margin:6pt 0 6pt;">
      {prohibited_items}
    </ul>
    <p>{L['warn_trace']}</p>
  </div>

  <div class="legal-section">
    <div class="legal-section-title">{L['conseq_title']}</div>
    <p>{L['conseq_intro']}</p>
    <ul>
      {consequence_items}
    </ul>
    <p>{L['conseq_monitor']}</p>
  </div>

  <div class="legal-edu">
    <div class="legal-edu-title">{L['edu_title']}</div>
    {edu_paras}
    <p style="margin-top:8pt;font-style:italic;opacity:.85;">{L['lang_note']}</p>
  </div>

  <div class="legal-footer-note">
    © {year} Tradeable. {L['footer_note']}
  </div>

</div>"""


_LEGAL = {
    'en': {
        'id_title': 'Document identification',
        'id_licensed': 'Licensed to',
        'id_order': 'Order reference',
        'id_date': 'Issue date',
        'id_publisher': 'Publisher',
        'id_product': 'Product',
        'id_edition': 'Digital Edition',
        'warn_title': 'CONFIDENTIAL DOCUMENT — RESTRICTED LICENSE',
        'warn_intro1': 'This document is the exclusive and confidential property of Tradeable. '
                       'It is licensed solely and personally to the individual identified above for their own '
                       'private study. This license grants no other rights whatsoever.',
        'warn_intro2': 'The following actions are <strong>strictly prohibited</strong> under the terms and conditions '
                       'accepted at the time of purchase, and may constitute a violation of applicable intellectual '
                       'property and copyright law:',
        'prohibited': [
            'Reproducing, copying, or duplicating this document, in whole or in part, by any means.',
            'Sharing, distributing, or transmitting this document to any third party, whether free of charge or for '
            'commercial gain, through any medium (email, messaging platforms, file-sharing services, social networks, '
            'or otherwise).',
            'Reselling, sublicensing, or commercializing this document or any portion of its content.',
            'Removing, obscuring, or altering any watermark, copyright notice, or identification data embedded in this document.',
            'Publishing or uploading this document, or any derivative thereof, to any public or private online platform.',
        ],
        'warn_trace': 'Every copy of this document contains unique digital identification data tied to the licensed '
                      "user's account. Any unauthorized copy that surfaces publicly can be traced back to its origin.",
        'conseq_title': 'Consequences of unauthorized distribution',
        'conseq_intro': 'Tradeable reserves the right to take any or all of the following actions against any '
                        'individual found to have violated the terms of this license:',
        'consequences': [
            '<strong>Immediate and permanent suspension</strong> of the user\'s account on the Tradeable '
            'platform, without refund of any fees paid.',
            '<strong>Civil legal action</strong> for copyright infringement and breach of contract, including claims '
            'for compensatory damages, loss of revenue, and, where applicable under applicable law, statutory damages '
            'and legal costs.',
            '<strong>Criminal referral</strong> where the unauthorized distribution constitutes an offence under '
            'applicable national or international intellectual property legislation.',
            'Notification to relevant professional bodies, brokers, or prop firms where the infringer\'s identity is '
            'known and such disclosure is lawfully permitted.',
        ],
        'conseq_monitor': 'Tradeable actively monitors public and private channels for unauthorized copies of '
                          'its proprietary materials. We take intellectual property violations seriously and will pursue '
                          'all available legal remedies without prior warning.',
        'edu_title': 'Educational use only — Not financial advice',
        'edu_body': [
            'All content in this document is provided exclusively for educational and informational purposes. Nothing '
            'contained herein constitutes financial advice, investment advice, trading recommendations, or any other '
            'form of regulated advice.',
            'Trading financial instruments, including but not limited to forex, futures, indices, and commodities, '
            'involves a substantial risk of loss and is not suitable for every investor. Past performance, simulated '
            'results, and hypothetical scenarios are not indicative of future results. You are solely responsible for '
            'all trading decisions you make.',
            'Tradeable, its founders, employees, and affiliates shall not be held liable for any financial '
            'losses incurred as a result of applying, directly or indirectly, any concept, strategy, or information '
            'presented in this document.',
        ],
        'footer_note': 'All rights reserved. Unauthorized reproduction or distribution of this document, or any portion '
                       'of it, may result in severe civil and criminal penalties, and will be prosecuted to the maximum '
                       'extent permitted by law.',
        'lang_note': 'This notice is provided in English, the controlling language of this document. Any translation is '
                     'offered for convenience only and has no legal effect; in case of any discrepancy, the English '
                     'version prevails.',
    },
    'es': {
        'id_title': 'Identificación del documento',
        'id_licensed': 'Con licencia para',
        'id_order': 'Referencia de orden',
        'id_date': 'Fecha de emisión',
        'id_publisher': 'Editor',
        'id_product': 'Producto',
        'id_edition': 'Edición Digital',
        'warn_title': 'DOCUMENTO CONFIDENCIAL — LICENCIA RESTRINGIDA',
        'warn_intro1': 'Este documento es propiedad exclusiva y confidencial de Tradeable. Se concede en licencia, '
                       'de forma única y personal, a la persona identificada anteriormente para su estudio privado. Esta '
                       'licencia no otorga ningún otro derecho.',
        'warn_intro2': 'Las siguientes acciones quedan <strong>estrictamente prohibidas</strong> conforme a los términos '
                       'y condiciones aceptados en el momento de la compra, y pueden constituir una infracción de la '
                       'legislación aplicable en materia de propiedad intelectual y derechos de autor:',
        'prohibited': [
            'Reproducir, copiar o duplicar este documento, total o parcialmente, por cualquier medio.',
            'Compartir, distribuir o transmitir este documento a terceros, ya sea de forma gratuita o con '
            'fines comerciales, por cualquier medio (correo electrónico, plataformas de mensajería, servicios '
            'de intercambio de archivos, redes sociales u otros).',
            'Revender, sublicenciar o comercializar este documento o cualquier parte de su contenido.',
            'Eliminar, ocultar o alterar cualquier marca de agua, aviso de derechos de autor o dato de identificación '
            'incorporado en este documento.',
            'Publicar o subir este documento, o cualquier obra derivada del mismo, a plataformas en línea públicas o privadas.',
        ],
        'warn_trace': 'Cada copia de este documento contiene datos de identificación digital únicos, vinculados a la '
                      'cuenta del usuario con licencia. Cualquier copia no autorizada que aparezca públicamente puede '
                      'rastrearse hasta su origen.',
        'conseq_title': 'Consecuencias de la distribución no autorizada',
        'conseq_intro': 'Tradeable se reserva el derecho de emprender cualquiera de las siguientes acciones, o '
                        'todas ellas, contra cualquier persona que infrinja los términos de esta licencia:',
        'consequences': [
            '<strong>Suspensión inmediata y permanente</strong> de la cuenta del usuario en la plataforma Trader '
            'Accelerator, sin reembolso de las sumas pagadas.',
            '<strong>Acciones legales por la vía civil</strong> por infracción de derechos de autor e incumplimiento de '
            'contrato, incluidas reclamaciones por daños y perjuicios, lucro cesante y, cuando proceda según la ley '
            'aplicable, indemnizaciones legales y costas judiciales.',
            '<strong>Denuncia penal</strong> cuando la distribución no autorizada constituya un delito conforme a la '
            'legislación nacional o internacional aplicable en materia de propiedad intelectual.',
            'Notificación a los organismos profesionales, brokers o prop firms que corresponda cuando se conozca la '
            'identidad del infractor y dicha divulgación esté legalmente permitida.',
        ],
        'conseq_monitor': 'Tradeable supervisa activamente canales públicos y privados en busca de copias no '
                          'autorizadas de sus materiales protegidos. Nos tomamos muy en serio las infracciones de '
                          'propiedad intelectual y emprenderemos todas las acciones legales a nuestro alcance sin previo aviso.',
        'edu_title': 'Uso exclusivamente educativo — No es asesoría financiera',
        'edu_body': [
            'Todo el contenido de este documento se ofrece únicamente con fines educativos e informativos. '
            'Nada de lo aquí expuesto constituye asesoría financiera, asesoría de inversión, recomendaciones '
            'de trading ni ninguna otra forma de asesoría regulada.',
            'Operar con instrumentos financieros —incluidos, entre otros, forex, futuros, índices y materias primas— '
            'conlleva un riesgo sustancial de pérdida y no resulta adecuado para todos los inversores. Los resultados '
            'pasados, los resultados simulados y los escenarios hipotéticos no garantizan resultados futuros. Tú eres el '
            'único responsable de todas las decisiones de trading que tomes.',
            'Tradeable, sus fundadores, empleados y afiliados no se responsabilizan de ninguna pérdida '
            'financiera derivada de la aplicación, directa o indirecta, de cualquier concepto, estrategia o información '
            'contenidos en este documento.',
        ],
        'footer_note': 'Todos los derechos reservados. La reproducción o distribución no autorizada de este documento, '
                       'o de cualquier parte del mismo, puede acarrear graves sanciones civiles y penales, y se '
                       'perseguirá en la máxima medida que permita la ley.',
        'lang_note': 'La versión en inglés de este aviso es la única con valor legal. Cualquier traducción se ofrece '
                     'únicamente por cortesía y, en caso de discrepancia, prevalece la versión en inglés.',
    },
    'fr': {
        'id_title': 'Identification du document',
        'id_licensed': 'Sous licence pour',
        'id_order': 'Référence de commande',
        'id_date': "Date d'émission",
        'id_publisher': 'Éditeur',
        'id_product': 'Produit',
        'id_edition': 'Édition Numérique',
        'warn_title': 'DOCUMENT CONFIDENTIEL — LICENCE RESTREINTE',
        'warn_intro1': 'Ce document est la propriété exclusive et confidentielle de Tradeable. Il est concédé '
                       'sous licence uniquement et personnellement à la personne identifiée ci-dessus pour son propre '
                       "usage privé. Cette licence n'accorde aucun autre droit.",
        'warn_intro2': 'Les actions suivantes sont <strong>strictement interdites</strong> en vertu des conditions '
                       "générales acceptées au moment de l'achat, et peuvent constituer une violation de la législation "
                       "applicable en matière de propriété intellectuelle et de droit d'auteur :",
        'prohibited': [
            'Reproduire, copier ou dupliquer ce document, en tout ou en partie, par quelque moyen que ce soit.',
            'Partager, distribuer ou transmettre ce document à un tiers, que ce soit gratuitement ou à des fins '
            'commerciales, par quelque moyen que ce soit (e-mail, plateformes de messagerie, services de partage de '
            'fichiers, réseaux sociaux ou autres).',
            'Revendre, sous-licencier ou commercialiser ce document ou toute partie de son contenu.',
            "Supprimer, masquer ou modifier tout filigrane, avis de droit d'auteur ou donnée d'identification intégrée "
            'à ce document.',
            'Publier ou téléverser ce document, ou tout dérivé de celui-ci, sur toute plateforme en ligne publique ou privée.',
        ],
        'warn_trace': "Chaque copie de ce document contient des données d'identification numérique uniques liées au "
                      "compte de l'utilisateur licencié. Toute copie non autorisée qui apparaîtrait publiquement peut "
                      'être retracée jusqu\'à son origine.',
        'conseq_title': 'Conséquences de la distribution non autorisée',
        'conseq_intro': "Tradeable se réserve le droit d'engager tout ou partie des actions suivantes contre "
                        'toute personne reconnue avoir enfreint les conditions de cette licence :',
        'consequences': [
            "<strong>Suspension immédiate et permanente</strong> du compte de l'utilisateur sur la plateforme Trader "
            'Accelerator, sans remboursement des frais payés.',
            "<strong>Action en justice civile</strong> pour violation du droit d'auteur et rupture de contrat, y "
            'compris des demandes de dommages-intérêts compensatoires, de perte de revenus et, le cas échéant en vertu '
            'de la loi applicable, de dommages-intérêts légaux et de frais de justice.',
            '<strong>Signalement pénal</strong> lorsque la distribution non autorisée constitue une infraction au '
            'regard de la législation nationale ou internationale applicable en matière de propriété intellectuelle.',
            "Notification aux organismes professionnels, courtiers ou prop firms concernés lorsque l'identité du "
            'contrevenant est connue et que cette divulgation est légalement autorisée.',
        ],
        'conseq_monitor': 'Tradeable surveille activement les canaux publics et privés à la recherche de copies '
                          'non autorisées de ses documents propriétaires. Nous prenons les violations de la propriété '
                          'intellectuelle au sérieux et exercerons tous les recours juridiques disponibles sans préavis.',
        'edu_title': 'Usage éducatif uniquement — Pas un conseil financier',
        'edu_body': [
            "L'ensemble du contenu de ce document est fourni exclusivement à des fins éducatives et informatives. Rien "
            'de ce qui y est contenu ne constitue un conseil financier, un conseil en investissement, des '
            'recommandations de trading ou toute autre forme de conseil réglementé.',
            "Le trading d'instruments financiers, y compris mais sans s'y limiter le forex, les futures, les indices et "
            'les matières premières, comporte un risque substantiel de perte et ne convient pas à tous les '
            'investisseurs. Les performances passées, les résultats simulés et les scénarios hypothétiques ne préjugent '
            'pas des résultats futurs. Vous êtes seul responsable de toutes les décisions de trading que vous prenez.',
            "Tradeable, ses fondateurs, employés et affiliés ne sauraient être tenus responsables des pertes "
            "financières subies à la suite de l'application, directe ou indirecte, de tout concept, stratégie ou "
            'information présenté dans ce document.',
        ],
        'footer_note': 'Tous droits réservés. La reproduction ou la distribution non autorisée de ce document, ou de '
                       'toute partie de celui-ci, peut entraîner de lourdes sanctions civiles et pénales, et sera '
                       'poursuivie dans toute la mesure permise par la loi.',
        'lang_note': "Seule la version anglaise de cet avis a valeur juridique. Toute traduction est fournie à titre "
                     "indicatif uniquement et, en cas de divergence, la version anglaise prévaut.",
    },
    'pt': {
        'id_title': 'Identificação do documento',
        'id_licensed': 'Licenciado para',
        'id_order': 'Referência do pedido',
        'id_date': 'Data de emissão',
        'id_publisher': 'Editora',
        'id_product': 'Produto',
        'id_edition': 'Edição Digital',
        'warn_title': 'DOCUMENTO CONFIDENCIAL — LICENÇA RESTRITA',
        'warn_intro1': 'Este documento é propriedade exclusiva e confidencial da Tradeable. É licenciado única e '
                       'pessoalmente à pessoa identificada acima para o seu próprio estudo privado. Esta licença não '
                       'concede quaisquer outros direitos.',
        'warn_intro2': 'As seguintes ações são <strong>estritamente proibidas</strong> nos termos e condições aceitos no '
                       'momento da compra, e podem constituir uma violação da legislação aplicável em matéria de '
                       'propriedade intelectual e direitos autorais:',
        'prohibited': [
            'Reproduzir, copiar ou duplicar este documento, no todo ou em parte, por qualquer meio.',
            'Compartilhar, distribuir ou transmitir este documento a qualquer terceiro, seja gratuitamente ou para fins '
            'comerciais, através de qualquer meio (e-mail, plataformas de mensagens, serviços de compartilhamento de arquivos, '
            'redes sociais ou outros).',
            'Revender, sublicenciar ou comercializar este documento ou qualquer parte do seu conteúdo.',
            'Remover, ocultar ou alterar qualquer marca de água, aviso de direitos autorais ou dado de identificação '
            'incorporado neste documento.',
            'Publicar ou carregar este documento, ou qualquer derivado do mesmo, em qualquer plataforma online pública ou privada.',
        ],
        'warn_trace': 'Cada cópia deste documento contém dados únicos de identificação digital associados à conta do '
                      'usuário licenciado. Qualquer cópia não autorizada que surja publicamente pode ser rastreada '
                      'até a sua origem.',
        'conseq_title': 'Consequências da distribuição não autorizada',
        'conseq_intro': 'A Tradeable reserva-se o direito de tomar qualquer uma das seguintes ações, ou todas '
                        'elas, contra qualquer pessoa que se verifique ter violado os termos desta licença:',
        'consequences': [
            '<strong>Suspensão imediata e permanente</strong> da conta do usuário na plataforma Tradeable, '
            'sem reembolso de quaisquer taxas pagas.',
            '<strong>Ação legal civil</strong> por violação de direitos autorais e quebra de contrato, incluindo '
            'pedidos de indenização por danos, perda de receitas e, quando aplicável nos termos da lei, indenizações '
            'legais e custas judiciais.',
            '<strong>Participação criminal</strong> quando a distribuição não autorizada constitua um crime nos termos '
            'da legislação nacional ou internacional aplicável em matéria de propriedade intelectual.',
            'Notificação aos organismos profissionais, corretoras ou prop firms relevantes quando a identidade do '
            'infrator for conhecida e tal divulgação for legalmente permitida.',
        ],
        'conseq_monitor': 'A Tradeable monitora ativamente canais públicos e privados em busca de cópias não '
                          'autorizadas dos seus materiais proprietários. Levamos as violações de propriedade '
                          'intelectual a sério e exerceremos todos os recursos legais disponíveis sem aviso prévio.',
        'edu_title': 'Uso exclusivamente educativo — Não é aconselhamento financeiro',
        'edu_body': [
            'Todo o conteúdo deste documento é fornecido exclusivamente para fins educativos e informativos. Nada do '
            'aqui contido constitui aconselhamento financeiro, aconselhamento de investimento, recomendações de trading '
            'ou qualquer outra forma de aconselhamento regulado.',
            'Negociar instrumentos financeiros, incluindo, entre outros, forex, futuros, índices e matérias-primas, '
            'envolve um risco substancial de perda e não é adequado para todos os investidores. O desempenho passado, '
            'os resultados simulados e os cenários hipotéticos não são indicativos de resultados futuros. O usuário é '
            'o único responsável por todas as decisões de trading que tomar.',
            'A Tradeable, os seus fundadores, funcionários e afiliados não serão responsabilizados por '
            'quaisquer perdas financeiras incorridas em resultado da aplicação, direta ou indireta, de qualquer '
            'conceito, estratégia ou informação apresentada neste documento.',
        ],
        'footer_note': 'Todos os direitos reservados. A reprodução ou distribuição não autorizada deste documento, ou '
                       'de qualquer parte do mesmo, pode resultar em severas sanções civis e criminais, e será '
                       'processada na máxima extensão permitida por lei.',
        'lang_note': 'A versão em inglês deste aviso é a única com valor legal. Qualquer tradução é fornecida apenas '
                     'por cortesia e, em caso de divergência, prevalece a versão em inglês.',
    },
}
