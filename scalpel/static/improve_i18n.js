/* ──────────────────────────────────────────────────────────────────────────
   Mentorship funnel ("Find New Ways to Improve") — i18n for the standalone
   /improve pages. Reads the same localStorage key as the main app
   (`scalpel_lang`) so the language choice stays consistent across the site,
   and exposes a small EN/ES/FR/PT switcher in the page header.
   Strings with inline markup use [data-i18n-html]; everything else [data-i18n].
   ────────────────────────────────────────────────────────────────────────── */
(function () {
  var T = {
    en: {
      'doctitle': 'Find New Ways to Improve',
      'nav.backApp': '← Back to app',
      'nav.back': '← Back',
      'legal': 'Educational content only. Nothing here is financial advice, a recommendation, a signal, or a guarantee of results. Trading involves substantial risk of loss. Any progress depends entirely on your own effort, decisions and circumstances.',
      // Page 1 — intro
      'p1.eyebrowA': 'Beyond the tools',
      'p1.eyebrowB': 'A different path',
      'p1.title': 'Find new ways to <span class="accent">improve</span>.',
      'p1.sub': "Most traders hit a ceiling that more screen time won't break. When studying on your own stops moving the needle, there's another way to keep growing — quieter, closer, and built for the part nobody really teaches.",
      'p1.cta': 'Keep going',
      'p1.reassure': 'Takes two minutes. No pressure, no commitment.',
      // Page 2 — mindset
      'p2.eyebrow': 'The part nobody teaches',
      'p2.title': 'You can know everything — <span class="accent">and still freeze.</span>',
      'p2.lead': 'Trading is two skills wearing one name. The first — structure, levels, timing — you can study. The second can’t be taught from a slide.',
      'p2.p1': 'Patience while a trade breathes. Taking the loss without flinching. Not chasing, not revenging, not abandoning the plan the moment it gets uncomfortable. That second skill is the <strong>mind</strong> — and almost nobody teaches it, so most traders leave it to chance.',
      'p2.p2': 'Then they wonder why they know exactly what to do… and do the opposite when it’s live. The hardest part is that you usually can’t see your own blind spot. The one thing self-study can never give you is someone who already walked through it — and can see it for you.',
      'p2.cta': 'There’s more',
      // Page 3 — the gap
      'p3.eyebrow': 'The gap',
      'p3.title': 'The distance between <span class="accent">knowing and doing.</span>',
      'p3.lead': 'That gap is where most progress quietly dies.',
      'p3.p1': 'Not because you lack information — you’re drowning in it. Information was never the bottleneck. Turning it into calm, repeatable decisions is. And that translation is exactly what you can’t get from one more video, one more book, one more indicator.',
      'p3.p2': 'Closing that gap alone can cost you <strong>years</strong> of expensive trial and error. Or it can take far less — with someone who can see what you can’t, point at the one thing holding you back, and shorten the road to understanding.',
      'p3.p3': 'That’s the idea behind what comes next. A quieter way to learn — closer to how it actually clicks.',
      'p3.cta': 'Show me',
      // Page 4 — inside
      'p4.eyebrow': 'A different way to learn',
      'p4.title': 'Two ways to <span class="accent">go deeper.</span>',
      'p4.lead': 'No theory dumps. No noise. Just a closer look at how someone who lives in the markets actually thinks — and the option to bring your own thinking into the room.',
      'p4.way1label': 'On your own time',
      'p4.way1title': 'Recorded walkthroughs',
      'p4.way1body': 'A growing library that takes real analysis apart from start to finish — the read, the reasoning, the mistakes, the why. Watch, pause, and revisit whenever it clicks.',
      'p4.way2label': 'Up close',
      'p4.way2title': 'One-to-one time',
      'p4.way2body': 'Direct, private time with someone who’s in the markets every day. Bring your own charts, your own decisions, your own blind spots — and work through them together.',
      'p4.closing': 'No signals. No one telling you what to buy or sell. Just a guide — for your understanding, your discipline, and your craft.',
      'p4.cta': 'See if it’s for you'
    },
    es: {
      'doctitle': 'Encuentra nuevas formas de mejorar',
      'nav.backApp': '← Volver a la app',
      'nav.back': '← Atrás',
      'legal': 'Solo contenido educativo. Nada aquí es asesoría financiera, una recomendación, una señal ni una garantía de resultados. Operar implica un riesgo sustancial de pérdida. Cualquier progreso depende enteramente de tu propio esfuerzo, decisiones y circunstancias.',
      'p1.eyebrowA': 'Más allá de las herramientas',
      'p1.eyebrowB': 'Un camino distinto',
      'p1.title': 'Encuentra nuevas formas de <span class="accent">mejorar</span>.',
      'p1.sub': 'La mayoría de los traders llega a un techo que más horas de pantalla no rompen. Cuando estudiar por tu cuenta deja de marcar la diferencia, hay otra forma de seguir creciendo — más silenciosa, más cercana, y pensada para la parte que casi nadie enseña.',
      'p1.cta': 'Seguir',
      'p1.reassure': 'Toma dos minutos. Sin presión, sin compromiso.',
      'p2.eyebrow': 'La parte que nadie enseña',
      'p2.title': 'Puedes saberlo todo — <span class="accent">y aun así congelarte.</span>',
      'p2.lead': 'Operar son dos habilidades con un solo nombre. La primera — estructura, niveles, timing — se puede estudiar. La segunda no se enseña con una diapositiva.',
      'p2.p1': 'Paciencia mientras un trade respira. Tomar la pérdida sin titubear. No perseguir, no buscar revancha, no abandonar el plan apenas se pone incómodo. Esa segunda habilidad es la <strong>mente</strong> — y casi nadie la enseña, así que la mayoría la deja al azar.',
      'p2.p2': 'Y luego se preguntan por qué saben exactamente qué hacer… y hacen lo contrario en vivo. Lo más difícil es que casi nunca puedes ver tu propio punto ciego. Lo único que el autoestudio jamás te dará es alguien que ya pasó por ahí — y que puede verlo por ti.',
      'p2.cta': 'Hay más',
      'p3.eyebrow': 'La brecha',
      'p3.title': 'La distancia entre <span class="accent">saber y hacer.</span>',
      'p3.lead': 'Esa brecha es donde la mayoría del progreso muere en silencio.',
      'p3.p1': 'No porque te falte información — te estás ahogando en ella. La información nunca fue el cuello de botella. Convertirla en decisiones calmadas y repetibles, sí. Y esa traducción es justo lo que no consigues con un video más, un libro más, un indicador más.',
      'p3.p2': 'Cerrar esa brecha solo puede costarte <strong>años</strong> de ensayo y error costoso. O puede tomar mucho menos — con alguien que ve lo que tú no, que señala lo único que te frena, y que acorta el camino al entendimiento.',
      'p3.p3': 'Esa es la idea detrás de lo que viene. Una forma más silenciosa de aprender — más cerca de cómo realmente hace clic.',
      'p3.cta': 'Muéstrame',
      'p4.eyebrow': 'Una forma distinta de aprender',
      'p4.title': 'Dos formas de <span class="accent">ir más profundo.</span>',
      'p4.lead': 'Sin atiborrarte de teoría. Sin ruido. Solo una mirada más cercana a cómo piensa de verdad alguien que vive en los mercados — y la opción de traer tu propio criterio a la mesa.',
      'p4.way1label': 'A tu propio ritmo',
      'p4.way1title': 'Análisis grabados',
      'p4.way1body': 'Una biblioteca en crecimiento que desarma el análisis real de principio a fin — la lectura, el razonamiento, los errores, el porqué. Mira, pausa y vuelve cuando haga clic.',
      'p4.way2label': 'De cerca',
      'p4.way2title': 'Tiempo uno a uno',
      'p4.way2body': 'Tiempo directo y privado con alguien que está en los mercados todos los días. Trae tus propios gráficos, tus propias decisiones, tus propios puntos ciegos — y trabájenlos juntos.',
      'p4.closing': 'Sin señales. Nadie diciéndote qué comprar o vender. Solo una guía — para tu entendimiento, tu disciplina y tu oficio.',
      'p4.cta': 'Ve si es para ti'
    },
    fr: {
      'doctitle': 'Trouve de nouvelles façons de progresser',
      'nav.backApp': '← Retour à l’app',
      'nav.back': '← Retour',
      'legal': 'Contenu éducatif uniquement. Rien ici n’est un conseil financier, une recommandation, un signal ou une garantie de résultats. Le trading comporte un risque substantiel de perte. Tout progrès dépend entièrement de vos propres efforts, décisions et circonstances.',
      'p1.eyebrowA': 'Au-delà des outils',
      'p1.eyebrowB': 'Une autre voie',
      'p1.title': 'Trouve de nouvelles façons de <span class="accent">progresser</span>.',
      'p1.sub': 'La plupart des traders atteignent un plafond que plus de temps d’écran ne brisera pas. Quand étudier seul ne fait plus la différence, il existe une autre façon de continuer à progresser — plus discrète, plus proche, et conçue pour la partie que presque personne n’enseigne.',
      'p1.cta': 'Continuer',
      'p1.reassure': 'Ça prend deux minutes. Sans pression, sans engagement.',
      'p2.eyebrow': 'La partie que personne n’enseigne',
      'p2.title': 'Tu peux tout savoir — <span class="accent">et figer quand même.</span>',
      'p2.lead': 'Le trading, ce sont deux compétences sous un seul nom. La première — structure, niveaux, timing — s’étudie. La seconde ne s’enseigne pas sur une diapositive.',
      'p2.p1': 'La patience pendant qu’un trade respire. Encaisser la perte sans broncher. Ne pas courir après, ne pas chercher la revanche, ne pas abandonner le plan dès que ça devient inconfortable. Cette seconde compétence, c’est le <strong>mental</strong> — et presque personne ne l’enseigne, alors la plupart le laissent au hasard.',
      'p2.p2': 'Puis ils se demandent pourquoi ils savent exactement quoi faire… et font l’inverse en direct. Le plus dur, c’est qu’on ne voit presque jamais son propre angle mort. La seule chose que l’auto-apprentissage ne donnera jamais, c’est quelqu’un qui est déjà passé par là — et qui peut le voir pour toi.',
      'p2.cta': 'Il y a plus',
      'p3.eyebrow': 'L’écart',
      'p3.title': 'La distance entre <span class="accent">savoir et faire.</span>',
      'p3.lead': 'C’est dans cet écart que la plupart des progrès meurent en silence.',
      'p3.p1': 'Pas par manque d’information — tu t’y noies. L’information n’a jamais été le goulot d’étranglement. La transformer en décisions calmes et reproductibles, si. Et cette traduction, c’est exactement ce qu’une vidéo de plus, un livre de plus, un indicateur de plus ne te donneront pas.',
      'p3.p2': 'Combler cet écart seul peut te coûter <strong>des années</strong> d’essais et d’erreurs coûteux. Ou cela peut prendre bien moins — avec quelqu’un qui voit ce que tu ne vois pas, qui pointe la seule chose qui te freine, et qui raccourcit le chemin vers la compréhension.',
      'p3.p3': 'C’est l’idée derrière ce qui suit. Une façon plus discrète d’apprendre — plus proche de la manière dont ça fait vraiment tilt.',
      'p3.cta': 'Montre-moi',
      'p4.eyebrow': 'Une autre façon d’apprendre',
      'p4.title': 'Deux façons d’<span class="accent">aller plus loin.</span>',
      'p4.lead': 'Pas de déversement de théorie. Pas de bruit. Juste un regard plus proche sur la façon dont pense vraiment quelqu’un qui vit dans les marchés — et la possibilité d’amener ta propre réflexion dans la pièce.',
      'p4.way1label': 'À ton rythme',
      'p4.way1title': 'Analyses enregistrées',
      'p4.way1body': 'Une bibliothèque qui s’étoffe et décortique de vraies analyses du début à la fin — la lecture, le raisonnement, les erreurs, le pourquoi. Regarde, mets en pause, et reviens quand ça fait tilt.',
      'p4.way2label': 'De près',
      'p4.way2title': 'Du temps en tête-à-tête',
      'p4.way2body': 'Du temps direct et privé avec quelqu’un qui est sur les marchés chaque jour. Apporte tes propres graphiques, tes propres décisions, tes propres angles morts — et travaillez-les ensemble.',
      'p4.closing': 'Pas de signaux. Personne pour te dire quoi acheter ou vendre. Juste un guide — pour ta compréhension, ta discipline et ton art.',
      'p4.cta': 'Vois si c’est pour toi'
    },
    pt: {
      'doctitle': 'Encontre novas formas de evoluir',
      'nav.backApp': '← Voltar ao app',
      'nav.back': '← Voltar',
      'legal': 'Apenas conteúdo educativo. Nada aqui é aconselhamento financeiro, uma recomendação, um sinal ou uma garantia de resultados. Operar envolve risco substancial de perda. Qualquer progresso depende inteiramente do seu próprio esforço, decisões e circunstâncias.',
      'p1.eyebrowA': 'Além das ferramentas',
      'p1.eyebrowB': 'Um caminho diferente',
      'p1.title': 'Encontre novas formas de <span class="accent">evoluir</span>.',
      'p1.sub': 'A maioria dos traders atinge um teto que mais tempo de tela não quebra. Quando estudar por conta própria deixa de fazer diferença, existe outra forma de continuar crescendo — mais silenciosa, mais próxima, e feita para a parte que quase ninguém ensina.',
      'p1.cta': 'Continuar',
      'p1.reassure': 'Leva dois minutos. Sem pressão, sem compromisso.',
      'p2.eyebrow': 'A parte que ninguém ensina',
      'p2.title': 'Você pode saber tudo — <span class="accent">e ainda assim travar.</span>',
      'p2.lead': 'Operar são duas habilidades com um só nome. A primeira — estrutura, níveis, timing — dá para estudar. A segunda não se ensina num slide.',
      'p2.p1': 'Paciência enquanto um trade respira. Aceitar a perda sem vacilar. Não correr atrás, não buscar revanche, não abandonar o plano assim que fica desconfortável. Essa segunda habilidade é a <strong>mente</strong> — e quase ninguém a ensina, então a maioria deixa ao acaso.',
      'p2.p2': 'Aí se perguntam por que sabem exatamente o que fazer… e fazem o oposto ao vivo. O mais difícil é que quase nunca dá para ver o próprio ponto cego. A única coisa que o autoestudo nunca vai te dar é alguém que já passou por isso — e que consegue vê-lo por você.',
      'p2.cta': 'Tem mais',
      'p3.eyebrow': 'A lacuna',
      'p3.title': 'A distância entre <span class="accent">saber e fazer.</span>',
      'p3.lead': 'É nessa lacuna que a maior parte do progresso morre em silêncio.',
      'p3.p1': 'Não por falta de informação — você está se afogando nela. A informação nunca foi o gargalo. Transformá-la em decisões calmas e repetíveis, sim. E essa tradução é justamente o que mais um vídeo, mais um livro, mais um indicador não te dão.',
      'p3.p2': 'Fechar essa lacuna sozinho pode te custar <strong>anos</strong> de tentativa e erro caros. Ou pode levar muito menos — com alguém que vê o que você não vê, que aponta a única coisa que te trava, e que encurta o caminho até o entendimento.',
      'p3.p3': 'Essa é a ideia por trás do que vem a seguir. Uma forma mais silenciosa de aprender — mais perto de como a ficha realmente cai.',
      'p3.cta': 'Mostre-me',
      'p4.eyebrow': 'Uma forma diferente de aprender',
      'p4.title': 'Duas formas de <span class="accent">ir mais fundo.</span>',
      'p4.lead': 'Sem despejos de teoria. Sem ruído. Apenas um olhar mais próximo de como realmente pensa alguém que vive nos mercados — e a opção de trazer o seu próprio pensamento para a sala.',
      'p4.way1label': 'No seu próprio ritmo',
      'p4.way1title': 'Análises gravadas',
      'p4.way1body': 'Uma biblioteca em crescimento que desmonta análises reais do início ao fim — a leitura, o raciocínio, os erros, o porquê. Assista, pause e revise quando a ficha cair.',
      'p4.way2label': 'De perto',
      'p4.way2title': 'Tempo um a um',
      'p4.way2body': 'Tempo direto e privado com alguém que está nos mercados todos os dias. Traga seus próprios gráficos, suas próprias decisões, seus próprios pontos cegos — e resolvam juntos.',
      'p4.closing': 'Sem sinais. Ninguém te dizendo o que comprar ou vender. Apenas um guia — para o seu entendimento, a sua disciplina e o seu ofício.',
      'p4.cta': 'Veja se é para você'
    }
  };

  function getLang() {
    try { var s = localStorage.getItem('scalpel_lang'); if (s && T[s]) return s; } catch (e) {}
    return 'en';
  }

  function apply(lang) {
    if (!T[lang]) lang = 'en';
    var d = T[lang];
    document.documentElement.setAttribute('lang', lang);
    if (d['doctitle']) document.title = d['doctitle'];
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var k = el.getAttribute('data-i18n');
      if (d[k] != null) el.textContent = d[k];
    });
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var k = el.getAttribute('data-i18n-html');
      if (d[k] != null) el.innerHTML = d[k];
    });
    document.querySelectorAll('.lang-switch [data-lang]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });
    try { localStorage.setItem('scalpel_lang', lang); } catch (e) {}
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
