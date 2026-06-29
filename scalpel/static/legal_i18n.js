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
      'terms.t18': '<span class="sec-num">18.</span> Contacto',
      'terms.b1': '<p>Estos Términos y Condiciones ("Términos") constituyen un acuerdo legalmente vinculante entre tú ("Usuario", "tú" o "tu") y Trader Accelerator ("la Empresa", "nosotros" o "nuestro"), que rige tu acceso y uso del sitio web, la plataforma, las herramientas, el contenido digital y cualquier servicio relacionado (en conjunto, el "Servicio").</p><p>Al registrar una cuenta, hacer clic en "Acepto", realizar un pago, o acceder o usar de cualquier otra forma cualquier parte del Servicio, reconoces que has leído, entendido y aceptas quedar obligado por estos Términos en su totalidad, así como por cualquier política adicional aquí referenciada.</p><p>Si usas el Servicio en nombre de un tercero u organización, declaras que tienes autoridad para obligar a esa parte a estos Términos.</p><p style="font-size:13px; color:var(--muted);">A la fecha de estos Términos, Trader Accelerator es un negocio y nombre comercial operado de forma independiente. Una sociedad de responsabilidad limitada (que se prevé denominar "Trader Accelerator LLC") está en proceso de constitución. Hasta que dicha entidad se constituya y asuma expresamente estos Términos, estos Términos se celebran con el negocio independiente que opera bajo el nombre Trader Accelerator. Una vez constituida, Trader Accelerator LLC podrá asumir estos Términos mediante notificación escrita o electrónica a los usuarios, y desde la fecha de dicha notificación será la parte contratante bajo estos Términos; esta sección se actualizará entonces para indicar el nombre y el domicilio registrado de esa entidad. Las referencias en estos Términos a "Trader Accelerator", "la Empresa", "nosotros" o "nuestro" se refieren a ese negocio y, una vez constituida y tras dicha asunción, a Trader Accelerator LLC. Para cualquier notificación, consulta o contacto legal relativo a estos Términos o al Servicio, puedes escribirnos a <a href="mailto:support@traderaccelerator.com">support@traderaccelerator.com</a> (ver Sección 18).</p>',
      'terms.b2': '<p>Trader Accelerator es una plataforma educativa digital diseñada para ofrecer contenido educativo general sobre los mercados financieros, conceptos de trading, metodologías de análisis técnico y temas relacionados. El Servicio incluye, entre otros, herramientas y funciones interactivas y asistidas por IA, tales como análisis de capturas/gráficos generado por IA, cuestionarios educativos y desafíos de conocimiento (incluido un Reto Diario cronometrado), checklists de preparación de trades y herramientas de autorregistro ("Pre-Flight"), un foro de comunidad, funciones de visualización de datos, PDFs educativos descargables y elementos de gamificación (puntos de experiencia, rangos, insignias y certificados). Las funciones específicas disponibles dependen de tu plan y pueden añadirse, modificarse o eliminarse a nuestra entera discreción.</p><div class="callout info"><p><strong>Datos y herramientas autorregistrados:</strong> Cualquier detalle de trade, nota, checklist, estadística u otra información que ingreses en Pre-Flight o en cualquier otra herramienta es informada por ti, no es verificada por nosotros y no está conectada a ningún bróker, exchange ni cuenta de trading en vivo. Dichas herramientas son únicamente ayudas organizativas y educativas — no colocan, gestionan ni ejecutan operaciones, y nada de lo que muestran constituye asesoría financiera ni un historial de rendimiento certificado por Trader Accelerator.</p></div><div class="callout warn"><p><strong>Importante — No es asesoría financiera:</strong> Todo el contenido proporcionado a través del Servicio, incluidos, entre otros, artículos, tutoriales, documentos PDF, análisis generados por IA, revisiones de gráficos, discusiones del foro y cualquier otro material, se proporciona estrictamente con <strong>fines educativos e informativos únicamente</strong>. Nada en esta plataforma constituye, ni debe interpretarse como, asesoría financiera, asesoría de inversión, recomendaciones de trading o solicitud de compra o venta de cualquier instrumento o activo financiero de cualquier tipo.</p></div><div class="callout warn"><p><strong>Análisis generado por IA — ilustrativo, no asesoría personalizada:</strong> La función de análisis de capturas/gráficos asistida por IA produce una revisión educativa automatizada, general e ilustrativa de un trade que <strong>ya realizaste</strong>. No es asesoría financiera, de inversión ni de trading, no es una recomendación, señal o solicitud personalizada, y no es una recomendación de comprar, vender, mantener, entrar o salir de ningún instrumento o posición financiera específica. El análisis es generado por sistemas automatizados, puede ser incompleto o inexacto, y refleja una interpretación posible entre muchas — no debe utilizarse como base para ninguna decisión de trading o inversión. Eres el único responsable de evaluarlo según tus propias reglas, criterio y tolerancia al riesgo, y cualquier decisión que tomes sigue siendo enteramente tuya.</p></div><p>No estamos registrados como asesores de inversión, agentes de bolsa, planificadores financieros ni ningún profesional financiero regulado en ninguna jurisdicción. Operar e invertir en los mercados financieros implica un riesgo sustancial de pérdida, incluida la posible pérdida de todo el capital invertido. Los ejemplos educativos pasados o los escenarios históricos de mercado descritos dentro del Servicio no garantizan ni predicen resultados futuros.</p><p>Reconoces que cualquier decisión de trading o inversión que tomes es de tu exclusiva responsabilidad. Trader Accelerator no será responsable de ninguna pérdida financiera, daño o consecuencia derivada de tu interpretación o aplicación de cualquier contenido proporcionado a través del Servicio.</p>',
      'terms.b3': '<p>Para acceder o usar el Servicio, debes cumplir todos los siguientes requisitos:</p><ul><li>Debes tener al menos <strong>18 años de edad</strong>.</li><li>Debes tener la capacidad legal para celebrar un contrato vinculante conforme a las leyes de tu jurisdicción.</li><li>No debes ser residente de, ni estar sujeto a la jurisdicción de, ningún país o territorio sujeto a sanciones integrales por parte de la Oficina de Control de Activos Extranjeros de los Estados Unidos (OFAC), el Consejo de Seguridad de las Naciones Unidas, la Unión Europea o cualquier otra autoridad de sanciones aplicable que prohibiría tu acceso o uso del Servicio.</li><li>No debes haber sido suspendido previamente ni vetado de forma permanente del Servicio por Trader Accelerator.</li></ul><p>Al crear una cuenta, declaras y garantizas que cumples todos los requisitos de elegibilidad anteriores. Si no cumples estos requisitos, no debes acceder ni usar el Servicio. Nos reservamos el derecho de suspender o terminar cualquier cuenta que se determine haber sido creada en violación de estos criterios de elegibilidad, sin previo aviso y sin reembolso.</p>',
      'terms.b4': '<p>Para acceder a la mayoría de las funciones del Servicio, debes registrar y mantener una cuenta de usuario personal. Aceptas proporcionar información precisa, actual y completa durante el registro y actualizar dicha información según sea necesario.</p><p>Eres el único responsable de mantener la confidencialidad de las credenciales de tu cuenta, incluida tu contraseña. Eres plenamente responsable de todas las actividades que ocurran bajo tu cuenta, independientemente de si dichas actividades están autorizadas por ti. Aceptas notificarnos de inmediato sobre cualquier acceso no autorizado o sospecha de violación de seguridad.</p><p>Compartir la cuenta está estrictamente prohibido. Cada cuenta es personal e intransferible. No puedes crear, usar ni mantener más de una cuenta. Las cuentas que se determine que se comparten, transfieren, venden o duplican podrán ser suspendidas o terminadas de forma permanente, sin previo aviso y sin reembolso.</p><p>Trader Accelerator se reserva el derecho de rechazar registros, cancelar cuentas, o eliminar o editar contenido a su entera discreción.</p>'
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
      'terms.t18': '<span class="sec-num">18.</span> Contact',
      'terms.b1': '<p>Les présentes Conditions Générales (« Conditions ») constituent un accord juridiquement contraignant entre vous (« Utilisateur », « vous » ou « votre ») et Trader Accelerator (« la Société », « nous » ou « notre »), régissant votre accès et votre utilisation du site web, de la plateforme, des outils, du contenu numérique et de tout service connexe (collectivement, le « Service »).</p><p>En créant un compte, en cliquant sur « J’accepte », en effectuant un paiement, ou en accédant ou en utilisant de toute autre manière une partie quelconque du Service, vous reconnaissez avoir lu, compris et accepté d’être lié par les présentes Conditions dans leur intégralité, ainsi que par toute politique supplémentaire qui y est référencée.</p><p>Si vous utilisez le Service pour le compte d’un tiers ou d’une organisation, vous déclarez disposer de l’autorité nécessaire pour lier cette partie aux présentes Conditions.</p><p style="font-size:13px; color:var(--muted);">À la date des présentes Conditions, Trader Accelerator est une entreprise et un nom commercial exploités de manière indépendante. Une société à responsabilité limitée (qu’il est prévu de nommer « Trader Accelerator LLC ») est en cours de constitution. Jusqu’à ce que cette entité soit constituée et assume expressément les présentes Conditions, celles-ci sont conclues avec l’entreprise indépendante exploitée sous le nom Trader Accelerator. Une fois constituée, Trader Accelerator LLC pourra assumer les présentes Conditions par notification écrite ou électronique aux utilisateurs, et à compter de la date de cette notification, elle sera la partie contractante au titre des présentes Conditions ; la présente section sera alors mise à jour pour indiquer le nom et l’adresse enregistrée de cette entité. Les références dans les présentes Conditions à « Trader Accelerator », « la Société », « nous » ou « notre » désignent cette entreprise et, une fois constituée et après cette reprise, Trader Accelerator LLC. Pour toute notification, question ou contact juridique concernant les présentes Conditions ou le Service, vous pouvez nous écrire à <a href="mailto:support@traderaccelerator.com">support@traderaccelerator.com</a> (voir Section 18).</p>',
      'terms.b2': '<p>Trader Accelerator est une plateforme éducative numérique conçue pour fournir du contenu éducatif général sur les marchés financiers, les concepts de trading, les méthodologies d’analyse technique et les sujets connexes. Le Service comprend, sans s’y limiter, des outils et fonctionnalités interactifs et assistés par IA, tels que l’analyse de captures/graphiques générée par IA, des quiz éducatifs et des défis de connaissances (y compris un Défi Quotidien chronométré), des checklists de préparation de trades et des outils d’auto-enregistrement (« Pre-Flight »), un forum communautaire, des fonctions de visualisation de données, des PDF éducatifs téléchargeables et des éléments de gamification (points d’expérience, rangs, badges et certificats). Les fonctionnalités spécifiques disponibles dépendent de votre offre et peuvent être ajoutées, modifiées ou supprimées à notre entière discrétion.</p><div class="callout info"><p><strong>Données et outils auto-enregistrés :</strong> Tout détail de trade, note, checklist, statistique ou autre information que vous saisissez dans Pre-Flight ou tout autre outil est déclaré par vous, n’est pas vérifié par nous et n’est connecté à aucun courtier, bourse ou compte de trading réel. Ces outils sont uniquement des aides organisationnelles et éducatives — ils ne placent, ne gèrent ni n’exécutent aucune opération, et rien de ce qu’ils affichent ne constitue un conseil financier ni un historique de performance certifié par Trader Accelerator.</p></div><div class="callout warn"><p><strong>Important — Pas un conseil financier :</strong> Tout le contenu fourni via le Service, y compris, sans s’y limiter, les articles, tutoriels, documents PDF, analyses générées par IA, revues de graphiques, discussions de forum et tout autre matériel, est fourni strictement à des <strong>fins éducatives et informatives uniquement</strong>. Rien sur cette plateforme ne constitue, et ne doit être interprété comme, un conseil financier, un conseil en investissement, des recommandations de trading ou une sollicitation d’achat ou de vente de tout instrument ou actif financier de quelque nature que ce soit.</p></div><div class="callout warn"><p><strong>Analyse générée par IA — illustrative, pas un conseil personnalisé :</strong> La fonction d’analyse de captures/graphiques assistée par IA produit une revue éducative automatisée, générale et illustrative d’un trade que vous avez <strong>déjà réalisé</strong>. Ce n’est pas un conseil financier, en investissement ou en trading, ce n’est pas une recommandation, un signal ou une sollicitation personnalisée, et ce n’est pas une recommandation d’acheter, de vendre, de conserver, d’entrer ou de sortir d’un instrument ou d’une position financière spécifique. L’analyse est générée par des systèmes automatisés, peut être incomplète ou inexacte, et reflète une interprétation possible parmi d’autres — elle ne doit pas servir de base à une quelconque décision de trading ou d’investissement. Vous êtes seul responsable de l’évaluer au regard de vos propres règles, de votre jugement et de votre tolérance au risque, et toute décision que vous prenez reste entièrement la vôtre.</p></div><p>Nous ne sommes pas enregistrés en tant que conseillers en investissement, courtiers, planificateurs financiers ou tout autre professionnel financier réglementé dans une quelconque juridiction. Le trading et l’investissement sur les marchés financiers comportent un risque substantiel de perte, y compris la perte possible de la totalité du capital investi. Les exemples éducatifs passés ou les scénarios de marché historiques décrits dans le Service ne garantissent ni ne prédisent les résultats futurs.</p><p>Vous reconnaissez que toute décision de trading ou d’investissement que vous prenez relève de votre seule responsabilité. Trader Accelerator ne saurait être tenu responsable de toute perte financière, dommage ou conséquence résultant de votre interprétation ou de votre application de tout contenu fourni via le Service.</p>',
      'terms.b3': '<p>Pour accéder au Service ou l’utiliser, vous devez remplir toutes les conditions suivantes :</p><ul><li>Vous devez être âgé d’au moins <strong>18 ans</strong>.</li><li>Vous devez avoir la capacité juridique de conclure un contrat contraignant selon les lois de votre juridiction.</li><li>Vous ne devez pas être résident de, ni soumis à la juridiction de, tout pays ou territoire faisant l’objet de sanctions globales de la part de l’Office of Foreign Assets Control des États-Unis (OFAC), du Conseil de sécurité des Nations Unies, de l’Union européenne ou de toute autre autorité de sanctions applicable qui interdirait votre accès au Service ou son utilisation.</li><li>Vous ne devez pas avoir été précédemment suspendu ou banni de manière permanente du Service par Trader Accelerator.</li></ul><p>En créant un compte, vous déclarez et garantissez que vous remplissez toutes les conditions d’éligibilité ci-dessus. Si vous ne remplissez pas ces conditions, vous ne devez pas accéder au Service ni l’utiliser. Nous nous réservons le droit de suspendre ou de résilier tout compte dont il s’avère qu’il a été créé en violation de ces critères d’éligibilité, sans préavis et sans remboursement.</p>',
      'terms.b4': '<p>Pour accéder à la plupart des fonctionnalités du Service, vous devez créer et maintenir un compte utilisateur personnel. Vous acceptez de fournir des informations exactes, à jour et complètes lors de l’inscription et de mettre à jour ces informations si nécessaire.</p><p>Vous êtes seul responsable du maintien de la confidentialité des identifiants de votre compte, y compris votre mot de passe. Vous êtes pleinement responsable de toutes les activités effectuées sous votre compte, qu’elles soient ou non autorisées par vous. Vous acceptez de nous informer immédiatement de tout accès non autorisé ou de toute violation de sécurité présumée.</p><p>Le partage de compte est strictement interdit. Chaque compte est personnel et non transférable. Vous ne pouvez pas créer, utiliser ou maintenir plus d’un compte. Les comptes dont il s’avère qu’ils sont partagés, transférés, vendus ou dupliqués peuvent être suspendus ou résiliés de manière permanente, sans préavis et sans remboursement.</p><p>Trader Accelerator se réserve le droit de refuser une inscription, d’annuler des comptes, ou de supprimer ou de modifier du contenu à son entière discrétion.</p>'
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
      'terms.t18': '<span class="sec-num">18.</span> Contato',
      'terms.b1': '<p>Estes Termos e Condições ("Termos") constituem um acordo juridicamente vinculante entre você ("Usuário", "você" ou "seu") e a Trader Accelerator ("a Empresa", "nós" ou "nosso"), que rege seu acesso e uso do site, da plataforma, das ferramentas, do conteúdo digital e de quaisquer serviços relacionados (em conjunto, o "Serviço").</p><p>Ao registrar uma conta, clicar em "Concordo", efetuar um pagamento, ou de qualquer outra forma acessar ou usar qualquer parte do Serviço, você reconhece que leu, entendeu e concorda em se vincular a estes Termos na sua totalidade, bem como a quaisquer políticas adicionais aqui referenciadas.</p><p>Se você usar o Serviço em nome de um terceiro ou organização, você declara ter autoridade para vincular essa parte a estes Termos.</p><p style="font-size:13px; color:var(--muted);">Na data destes Termos, a Trader Accelerator é um negócio e nome comercial operado de forma independente. Uma sociedade de responsabilidade limitada (que se pretende nomear "Trader Accelerator LLC") está em processo de constituição. Até que essa entidade seja constituída e assuma expressamente estes Termos, estes Termos são celebrados com o negócio independente que opera sob o nome Trader Accelerator. Uma vez constituída, a Trader Accelerator LLC poderá assumir estes Termos mediante notificação escrita ou eletrônica aos usuários e, a partir da data dessa notificação, será a parte contratante sob estes Termos; esta seção será então atualizada para indicar o nome e o endereço registrado dessa entidade. As referências nestes Termos a "Trader Accelerator", "a Empresa", "nós" ou "nosso" referem-se a esse negócio e, uma vez constituída e após tal assunção, à Trader Accelerator LLC. Para qualquer notificação, dúvida ou contato jurídico relativo a estes Termos ou ao Serviço, você pode nos escrever em <a href="mailto:support@traderaccelerator.com">support@traderaccelerator.com</a> (ver Seção 18).</p>',
      'terms.b2': '<p>A Trader Accelerator é uma plataforma educativa digital projetada para fornecer conteúdo educativo geral sobre os mercados financeiros, conceitos de trading, metodologias de análise técnica e tópicos relacionados. O Serviço inclui, entre outros, ferramentas e recursos interativos e assistidos por IA, tais como análise de capturas/gráficos gerada por IA, quizzes educativos e desafios de conhecimento (incluindo um Desafio Diário cronometrado), checklists de preparação de trades e ferramentas de autorregistro ("Pre-Flight"), um fórum da comunidade, recursos de visualização de dados, PDFs educativos para download e elementos de gamificação (pontos de experiência, ranks, medalhas e certificados). Os recursos específicos disponíveis dependem do seu plano e podem ser adicionados, modificados ou removidos a nosso exclusivo critério.</p><div class="callout info"><p><strong>Dados e ferramentas autorregistrados:</strong> Quaisquer detalhes de trade, notas, checklists, estatísticas ou outras informações que você insira no Pre-Flight ou em qualquer outra ferramenta são informados por você, não são verificados por nós e não estão conectados a nenhuma corretora, exchange ou conta de trading ao vivo. Tais ferramentas são apenas auxílios organizacionais e educativos — elas não colocam, gerenciam nem executam operações, e nada do que exibem constitui aconselhamento financeiro ou um histórico de desempenho certificado pela Trader Accelerator.</p></div><div class="callout warn"><p><strong>Importante — Não é aconselhamento financeiro:</strong> Todo o conteúdo fornecido através do Serviço, incluindo, entre outros, artigos, tutoriais, documentos PDF, análises geradas por IA, revisões de gráficos, discussões do fórum e qualquer outro material, é fornecido estritamente para <strong>fins educativos e informativos apenas</strong>. Nada nesta plataforma constitui, nem deve ser interpretado como, aconselhamento financeiro, aconselhamento de investimento, recomendações de trading ou solicitação de compra ou venda de qualquer instrumento ou ativo financeiro de qualquer tipo.</p></div><div class="callout warn"><p><strong>Análise gerada por IA — ilustrativa, não aconselhamento personalizado:</strong> O recurso de análise de capturas/gráficos assistido por IA produz uma revisão educativa automatizada, geral e ilustrativa de um trade que você <strong>já realizou</strong>. Não é aconselhamento financeiro, de investimento ou de trading, não é uma recomendação, sinal ou solicitação personalizada, e não é uma recomendação de comprar, vender, manter, entrar ou sair de qualquer instrumento ou posição financeira específica. A análise é gerada por sistemas automatizados, pode ser incompleta ou imprecisa, e reflete uma interpretação possível entre muitas — não deve ser usada como base para qualquer decisão de trading ou investimento. Você é o único responsável por avaliá-la de acordo com suas próprias regras, julgamento e tolerância ao risco, e qualquer decisão que você tomar permanece inteiramente sua.</p></div><p>Não somos registrados como consultores de investimento, corretoras, planejadores financeiros ou qualquer profissional financeiro regulamentado em qualquer jurisdição. Operar e investir nos mercados financeiros envolve risco substancial de perda, incluindo a possível perda de todo o capital investido. Exemplos educativos passados ou cenários históricos de mercado descritos dentro do Serviço não garantem nem preveem resultados futuros.</p><p>Você reconhece que quaisquer decisões de trading ou investimento que você tomar são de sua exclusiva responsabilidade. A Trader Accelerator não será responsável por quaisquer perdas financeiras, danos ou consequências decorrentes da sua interpretação ou aplicação de qualquer conteúdo fornecido através do Serviço.</p>',
      'terms.b3': '<p>Para acessar ou usar o Serviço, você deve atender a todos os seguintes requisitos:</p><ul><li>Você deve ter pelo menos <strong>18 anos de idade</strong>.</li><li>Você deve ter capacidade legal para celebrar um contrato vinculante de acordo com as leis da sua jurisdição.</li><li>Você não deve ser residente de, nem estar sujeito à jurisdição de, qualquer país ou território sujeito a sanções abrangentes pelo Office of Foreign Assets Control dos Estados Unidos (OFAC), pelo Conselho de Segurança das Nações Unidas, pela União Europeia ou por qualquer outra autoridade de sanções aplicável que proibiria seu acesso ou uso do Serviço.</li><li>Você não deve ter sido previamente suspenso ou banido permanentemente do Serviço pela Trader Accelerator.</li></ul><p>Ao criar uma conta, você declara e garante que atende a todos os requisitos de elegibilidade acima. Se você não atender a esses requisitos, não deve acessar nem usar o Serviço. Reservamo-nos o direito de suspender ou encerrar qualquer conta que se verifique ter sido criada em violação destes critérios de elegibilidade, sem aviso prévio e sem reembolso.</p>',
      'terms.b4': '<p>Para acessar a maioria dos recursos do Serviço, você deve registrar e manter uma conta de usuário pessoal. Você concorda em fornecer informações precisas, atuais e completas durante o registro e em atualizar tais informações conforme necessário.</p><p>Você é o único responsável por manter a confidencialidade das credenciais da sua conta, incluindo sua senha. Você é totalmente responsável por todas as atividades que ocorram sob sua conta, independentemente de tais atividades serem autorizadas por você. Você concorda em nos notificar imediatamente sobre qualquer acesso não autorizado ou suspeita de violação de segurança.</p><p>O compartilhamento de conta é estritamente proibido. Cada conta é pessoal e intransferível. Você não pode criar, usar ou manter mais de uma conta. Contas que se verifique serem compartilhadas, transferidas, vendidas ou duplicadas podem ser suspensas ou encerradas permanentemente, sem aviso prévio e sem reembolso.</p><p>A Trader Accelerator reserva-se o direito de recusar registro, cancelar contas, ou remover ou editar conteúdo a seu exclusivo critério.</p>'
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
