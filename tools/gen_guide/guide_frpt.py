# -*- coding: utf-8 -*-
"""Contenido FR y PT. Convención de siempre: FR en «vous», PT brasileño «você»."""

FR = {
 'analyze': {
  'd': ('Vous téléversez la capture de votre graphique et l’IA la parcourt comme '
        'le ferait un instructeur : quelle structure elle distingue, si l’horaire '
        'et les confluences que vous avez déclarés concordent, et où votre '
        'raisonnement a des trous. Elle ne vous dit jamais d’entrer — elle vous '
        'donne des choses à vérifier.'),
  's': [
   'Ouvrez l’onglet <b>Analyser</b> et commencez par le contexte : '
   '<b>instrument</b>, <b>direction</b>, <b>session</b> et les <b>confluences</b> '
   'que vous pensez présentes. L’IA lit un même graphique très différemment selon '
   'ce que vous dites y voir : ce n’est pas une formalité.',
   'Choisissez la <b>méthodologie</b> que vous tradez. Chacune lit les mêmes '
   'bougies à sa manière — un order block compte en ICT et ne signifie rien en '
   'Wyckoff — donc vous tromper ici vous renvoie une réponse sur une méthode que '
   'vous n’utilisez pas.',
   'Téléversez la <b>capture</b>. Montrez d’où vient le prix : une image collée à '
   'l’entrée cache justement le contexte dont dépend l’analyse. Marquer vos '
   'niveaux avant la capture aide beaucoup.',
   'Si vous le souhaitez, rédigez votre <b>Construction du trade</b> : votre '
   'raisonnement avec vos mots, jusqu’à environ 200. C’est la partie que presque '
   'tout le monde saute, et c’est celle qui transforme une réponse générique en '
   'une réponse sur votre idée.',
   'Appuyez sur <b>Analyser</b> et lisez-la comme un second avis, pas comme un '
   'verdict. La bonne question n’est pas « est-ce qu’elle me donne raison ? » '
   'mais « a-t-elle vu quelque chose que je n’ai pas vu ? ».',
   'Enregistrez l’analyse dans un <b>projet</b>. Mettre trois de vos analyses '
   'côte à côte révèle dans vos erreurs des schémas qu’aucune ne montre seule.',
  ],
  'tip': ('Le compteur de droite indique combien d’analyses il vous reste dans la '
          'fenêtre en cours. Il se met à jour dès qu’une analyse se termine, vous '
          'n’avez donc rien à compter — et un envoi échoué n’en consomme aucune.'),
 },
 'preflight': {
  'd': ('Une check-list que vous remplissez <b>avant</b> d’entrer, pas après. Son '
        'but est de vous faire écrire vos règles pendant que vous n’avez encore '
        'rien en risque, car dès qu’il y a de l’argent en jeu votre raisonnement '
        'change sans vous demander la permission.'),
  's': [
   'Ouvrez <b>Pre-Flight</b> et créez une check-list pour le setup que vous '
   'regardez. Faites-le avant de cliquer sur acheter ou vendre : une check-list '
   'remplie après l’entrée est un journal, pas un filtre.',
   'Traitez chaque point honnêtement : <b>biais</b>, <b>session</b>, <b>risque</b> '
   'et <b>invalidation</b>. L’invalidation est la plus importante : si vous ne '
   'savez pas dire ce qui vous donnerait tort, vous n’avez pas un trade, vous avez '
   'un avis.',
   'Répondez avec ce qui est réellement sur le graphique, pas avec ce que vous '
   'espérez. La liste ne sert que si elle peut vous dire non.',
   'Qu’un point ne passe pas est un résultat, pas un échec. Un setup qui ne '
   'respecte pas vos propres règles est une information qui ne vous a rien coûté.',
   'Conservez vos check-lists. Revoir celles que vous avez outrepassées est le '
   'moyen le plus rapide de découvrir quelle règle vous enfreignez toujours.',
  ],
  'tip': ('Pre-Flight est un outil Premium et vous pouvez conserver jusqu’à dix '
          'check-lists — de quoi couvrir les setups que vous tradez vraiment, pas '
          'chaque idée qui passe.'),
 },
 'quiz': {
  'd': ('Une banque de questions sur toutes les méthodologies enseignées par la '
        'plateforme, avec une difficulté croissante, plus une question très dure '
        'chaque jour. Elle est conçue pour trouver les lacunes que vous ne vous '
        'connaissiez pas, pas pour vous rassurer sur ce que vous savez déjà.'),
  's': [
   'Ouvrez l’onglet <b>Quiz</b> et choisissez une méthodologie et un thème : order '
   'blocks, structure de marché, accumulation, figures graphiques, etc.',
   'Choisissez le niveau. <b>Débutant</b> vérifie les définitions, '
   '<b>intermédiaire</b> vérifie si vous savez les appliquer, et <b>avancé</b> met '
   'deux règles en conflit pour que vous sachiez laquelle l’emporte.',
   'Répondez, puis lisez l’explication même quand vous avez juste : au score, une '
   'intuition heureuse et une vraie connaissance se ressemblent exactement.',
   'Essayez un <b>scénario hardcore</b> quand un thème vous paraît facile : des '
   'situations complètes avec plusieurs lectures crédibles et une seule qui tient.',
   'Revenez pour le <b>Défi quotidien</b> : une question difficile par jour, et '
   'une série qui ne grandit que si vous êtes là.',
  ],
  'tip': ('Vos réponses sont vérifiées sur le serveur et les options sont '
          'mélangées : la bonne réponse ne circule jamais dans la page et il n’y a '
          'aucun schéma à exploiter. Le défi quotidien tourne aussi par compte — '
          'personne ne peut vous souffler la réponse, la sienne est une autre '
          'question.'),
 },
 'forum': {
  'd': ('Un espace pour publier des setups, demander où vous vous êtes trompé et '
        'suivre les traders dont vous voulez apprendre le raisonnement. Disponible '
        'en <b>Standard et Premium</b>. Chaque publication et chaque image passe '
        'par une modération automatique avant d’être visible.'),
  's': [
   'Ouvrez <b>Forum Trading</b> et lisez le fil général, ou l’onglet <b>Abonnements</b> '
   'pour ne voir que les traders que vous suivez.',
   'Utilisez <b>Nouvelle publication</b> pour partager un setup ou une question. '
   'Publier le graphique avec votre raisonnement vous vaut de bien meilleures '
   'réponses que le graphique seul.',
   'Rejoignez ou créez une <b>communauté</b> pour une méthodologie ou un marché, '
   'et publiez-y quand le sujet est trop précis pour le fil général.',
   'Réagissez et répondez aux autres. Répondre à quelqu’un vous oblige à mettre '
   'votre propre raisonnement en mots, et c’est là que les trous apparaissent.',
   'Utilisez <b>Enregistrés</b> pour ce qui mérite d’être relu, et <b>Messages</b> '
   'pour échanger en privé avec un autre trader.',
  ],
  'tip': ('La modération intervient avant publication, pas après une plainte, et '
          'elle couvre le texte et les images. Elle est là pour que personne n’ait '
          'à passer par-dessus des insultes ou de la vente de signaux pour '
          'atteindre la discussion utile.'),
 },
 'chalk': {
  'd': ('Un tableau libre pour penser avec les mains : dessinez la structure, '
        'marquez les niveaux, écrivez le plan à côté. Il est utile précisément '
        'parce que ce n’est pas un graphique — ici rien ne bouge pendant que vous '
        'réfléchissez.'),
  's': [
   'Ouvrez l’onglet <b>Chalkboard</b> et choisissez un outil dans la barre. '
   '(L’onglet porte ce nom dans toutes les langues.)',
   'Dessinez la <b>structure, les zones et les niveaux</b> que vous surveillez, et '
   'écrivez le raisonnement à côté du dessin plutôt que de le garder en tête.',
   'Utilisez plusieurs tableaux pour séparer les idées — un par instrument, ou un '
   'par session — au lieu de tout empiler sur un seul.',
   '<b>Exportez le tableau</b> quand il mérite d’être conservé. Ce fichier exporté '
   'est la vraie sauvegarde.',
  ],
  'tip': ('Vos tableaux vivent dans <b>ce navigateur</b>, pas dans votre compte. '
          'Ils survivent à la fermeture de l’onglet, mais ils ne voyagent pas '
          'jusqu’à votre téléphone et disparaissent si vous effacez les données du '
          'site. Si un tableau compte, exportez-le : c’est la seule copie qui vous '
          'appartient vraiment.'),
 },
 'synapse': {
  'd': ('Une carte interactive de toutes les méthodologies, construite comme un '
        'cerveau en 3D : chaque branche est une méthode, chaque nœud un concept, '
        'et chaque nœud ouvre un dossier complet. Elle sert à explorer comment les '
        'idées se relient, ce qu’une liste de leçons ne peut pas montrer.'),
  's': [
   'Ouvrez <b>Synapse</b>, laissez la carte se charger, puis cliquez sur une '
   'branche pour entrer dans une méthodologie.',
   'Cliquez sur un <b>nœud</b> pour lire son dossier : ce qu’est le concept, '
   'comment on l’identifie et comment il se relie à ceux qui l’entourent.',
   'Suivez les connexions plutôt que de lire dans l’ordre. Voir que deux méthodes '
   'décrivent le même comportement sous des noms différents, c’est tout l’intérêt '
   'de la carte.',
   'Tout est dans votre langue : la carte, les noms et les dossiers suivent la '
   'langue que vous avez choisie.',
   'Utilisez la flèche <b>Menu</b> pour revenir au reste de l’application quand '
   'vous voulez.',
  ],
  'tip': ('Si vous préférez lire loin de l’écran, la bibliothèque complète est '
          'disponible en PDF dans la boutique. C’est le même contenu, mis en page '
          'pour être lu du début à la fin.'),
 },
 'timing': {
  'd': ('Des horloges en direct pour les sessions qui font réellement bouger vos '
        'instruments, plus le calendrier économique. La plupart des pertes '
        'évitables ne sont pas de mauvaises analyses : ce sont de bonnes analyses '
        'à la mauvaise heure.'),
  's': [
   'Dans l’onglet Analyser, ouvrez le panneau <b>Market Timing</b> pour voir '
   'quelle session est en cours.',
   'Survolez une bande pour lire son horaire exact à l’<b>heure de New York et à '
   'la vôtre</b>. Les bandes sont les mêmes pour tout le monde ; seule l’horloge '
   'est la vôtre.',
   'Apprenez le caractère de chaque fenêtre : les ouvertures de Londres et de New '
   'York tendent à étendre, les heures du déjeuner à hacher, et les ranges '
   'construits la nuit sont ce que la session du jour va chercher.',
   'Filtrez le <b>calendrier économique</b> par votre instrument pour ne voir que '
   'les publications capables de le déplacer.',
   'Regardez ce qui est prévu <b>avant</b> de planifier une entrée, pas après que '
   'le prix a déjà sauté.',
  ],
  'tip': ('Une horloge de session vous dit quand la participation arrive '
          'habituellement, pas qu’il va se passer quelque chose. Une semaine de '
          'jours fériés garde le même horaire avec presque aucun volume derrière.'),
 },
 'plans': {
  'd': ('Votre offre détermine à quelle fréquence vous pouvez analyser, combien de '
        'projets vous conservez et quels outils sont débloqués. Tout le reste — le '
        'guide, la carte, votre rang — est identique pour tout le monde.'),
  's': [
   '<b>Free</b> — une analyse tous les 7 jours et un projet enregistré. De quoi '
   'voir exactement ce que fait l’outil avant de payer quoi que ce soit.',
   '<b>Standard</b> — une analyse toutes les 24 heures, cinq projets et un accès '
   'complet au Forum.',
   '<b>Premium</b> — cinq analyses toutes les 24 heures, dix projets, le Forum, '
   '<b>Pre-Flight</b> et son propre thème visuel.',
   'Les analyses qu’il vous reste s’affichent toujours dans le panneau de droite, '
   'vous n’avez donc rien à compter.',
  ],
  'tip': ('Ouvrez <b>Products → Offres</b> dans la barre latérale pour les '
          'comparer ou changer. Une offre payante se règle période par période et '
          'ne se renouvelle jamais toute seule : rien ne vous est prélevé si vous '
          'ne décidez pas de payer à nouveau.'),
 },
 'account': {
  'd': ('Votre profil, votre offre, votre rang et la façon dont la plateforme vous '
        'apparaît et vous parle. Tout change instantanément et rien de tout cela '
        'ne touche au travail que vous avez enregistré.'),
  's': [
   'Ouvrez le <b>panneau de compte</b> en haut de la colonne de droite pour voir '
   'votre offre, votre rang et vos codes.',
   'Changez de <b>langue</b> quand vous voulez entre français, anglais, espagnol '
   'et portugais — toute la plateforme suit, analyses comprises.',
   'Basculez entre <b>clair et sombre</b> depuis la barre latérale, et changez de '
   '<b>thème</b> si vous en possédez un : les thèmes restylent la plateforme sans '
   'rien déplacer.',
   'Regardez votre <b>rang</b> monter à mesure que vous gagnez de l’expérience en '
   'analysant, en répondant aux quiz et en participant au forum. Le rang ne fait '
   'que monter.',
   'Ouvrez <b>Products → Settings</b> pour les données de votre compte, votre mot '
   'de passe et votre session.',
  ],
  'tip': ('Atteindre un nouveau rang délivre un certificat avec une page de '
          'vérification publique : il peut donc être partagé et vérifié par '
          'n’importe qui. Il atteste d’une étude sur cette plateforme — ce n’est '
          'ni un diplôme professionnel ni une licence.'),
 },
}

PT = {
 'analyze': {
  'd': ('Você envia o print do seu gráfico e a IA percorre ele como faria um '
        'instrutor: que estrutura consegue ver, se o horário e as confluências que '
        'você declarou combinam, e onde o seu raciocínio tem buracos. Ela nunca '
        'manda você entrar — ela te dá coisas para conferir.'),
  's': [
   'Abra a aba <b>Analisar</b> e comece pelo contexto: <b>instrumento</b>, '
   '<b>direção</b>, <b>sessão</b> e as <b>confluências</b> que você acredita '
   'estarem presentes. A IA lê o mesmo gráfico de um jeito bem diferente conforme '
   'o que você diz estar vendo, então isso não é burocracia.',
   'Escolha a <b>metodologia</b> que você está operando. Cada uma lê os mesmos '
   'candles do seu jeito — um order block importa no ICT e não significa nada em '
   'Wyckoff —, então errar aqui devolve uma resposta sobre um método que você não '
   'usa.',
   'Envie o <b>print</b>. Mostre de onde o preço veio: uma imagem colada na '
   'entrada esconde justamente o contexto de que a análise depende. Marcar seus '
   'níveis antes de printar ajuda bastante.',
   'Se quiser, escreva a sua <b>Construção do trade</b>: o seu raciocínio com as '
   'suas palavras, até umas 200. É a parte que quase todo mundo pula e é a que '
   'transforma uma resposta genérica em uma resposta sobre a sua ideia.',
   'Aperte <b>Analisar</b> e leia como uma segunda opinião, não como um veredito. '
   'A pergunta útil não é “ela concorda comigo?” e sim “ela viu algo que eu não '
   'vi?”.',
   'Salve a análise em um <b>projeto</b>. Colocar três análises suas lado a lado '
   'mostra padrões nos seus erros que nenhuma delas mostra sozinha.',
  ],
  'tip': ('O contador da direita mostra quantas análises sobraram na janela atual. '
          'Ele atualiza assim que uma análise termina, então você não precisa '
          'contar — e um envio que falhou não gasta nenhuma.'),
 },
 'preflight': {
  'd': ('Uma checklist que você preenche <b>antes</b> de entrar, não depois. O '
        'objetivo é fazer você deixar as suas regras por escrito enquanto ainda '
        'não tem nada em risco, porque no instante em que há dinheiro em jogo o '
        'seu raciocínio muda sem pedir licença.'),
  's': [
   'Abra o <b>Pre-Flight</b> e crie uma checklist para o setup que você está '
   'olhando. Faça isso antes de clicar em comprar ou vender: uma checklist '
   'preenchida depois da entrada é um diário, não um filtro.',
   'Responda cada item com honestidade: <b>viés</b>, <b>sessão</b>, <b>risco</b> e '
   '<b>invalidação</b>. A invalidação é a que mais pesa: se você não sabe dizer o '
   'que provaria que está errado, você não tem um trade, tem uma opinião.',
   'Responda com o que está no gráfico, não com o que você gostaria. A checklist '
   'só serve se puder dizer não.',
   'Um item não passar é um resultado, não um fracasso. Um setup que não cumpre as '
   'suas próprias regras é informação que saiu de graça.',
   'Guarde as suas checklists. Revisar as que você ignorou é o jeito mais rápido '
   'de descobrir qual regra você quebra sempre.',
  ],
  'tip': ('O Pre-Flight é uma ferramenta Premium e você pode manter até dez '
          'checklists — o suficiente para cobrir os setups que você realmente '
          'opera, não toda ideia que aparece.'),
 },
 'quiz': {
  'd': ('Um banco de questões de todas as metodologias que a plataforma ensina, '
        'com dificuldade crescente, mais uma questão bem difícil por dia. Foi '
        'feito para achar as lacunas que você não sabia que tinha, não para você '
        'se sentir bem com o que já sabe.'),
  's': [
   'Abra a aba <b>Quiz</b> e escolha metodologia e tema: order blocks, estrutura '
   'de mercado, acumulação, padrões gráficos e por aí vai.',
   'Escolha o nível. <b>Iniciante</b> checa definições, <b>intermediário</b> checa '
   'se você sabe aplicá-las, e <b>avançado</b> coloca duas regras em conflito para '
   'você ter que saber qual manda.',
   'Responda e leia a explicação mesmo quando acertar: no placar, um palpite '
   'certeiro e conhecimento de verdade são idênticos.',
   'Tente um <b>cenário hardcore</b> quando um tema ficar fácil: situações '
   'completas com várias leituras plausíveis e só uma que se sustenta.',
   'Volte para o <b>Desafio diário</b>: uma questão difícil por dia e uma '
   'sequência que só cresce se você aparecer.',
  ],
  'tip': ('Suas respostas são verificadas no servidor e as alternativas são '
          'embaralhadas, então o gabarito nunca viaja na página e não há padrão '
          'para explorar. O desafio diário também gira por conta: ninguém pode te '
          'passar a resposta, porque a dele é outra questão.'),
 },
 'forum': {
  'd': ('Um espaço para publicar setups, perguntar onde você errou e seguir '
        'traders cujo raciocínio você quer aprender. Disponível no <b>Standard e '
        'no Premium</b>. Cada publicação e imagem passa por moderação automática '
        'antes de aparecer.'),
  's': [
   'Abra <b>Fórum Trading</b> e leia o feed geral, ou a aba <b>Seguindo</b> para ver só '
   'os traders que você segue.',
   'Use <b>Nova publicação</b> para compartilhar um setup ou uma dúvida. Publicar '
   'o gráfico junto com o seu raciocínio rende respostas muito melhores do que '
   'publicar só o gráfico.',
   'Entre ou crie uma <b>comunidade</b> para uma metodologia ou um mercado, e '
   'publique lá quando o tema for específico demais para o feed geral.',
   'Reaja e responda aos outros. Responder alguém obriga você a colocar o seu '
   'próprio raciocínio em palavras, que é onde as lacunas aparecem.',
   'Use <b>Salvos</b> para o que vale reler, e <b>Mensagens</b> para conversar em '
   'particular com outro trader.',
  ],
  'tip': ('A moderação age antes de publicar, não depois que alguém reclama, e '
          'cobre texto e imagens. Ela existe para que ninguém precise passar por '
          'cima de ofensas ou de gente vendendo sinais para chegar à conversa que '
          'presta.'),
 },
 'chalk': {
  'd': ('Uma lousa livre para pensar com as mãos: desenhe a estrutura, marque os '
        'níveis, escreva o plano ao lado. Serve justamente porque não é um '
        'gráfico — aqui nada se mexe enquanto você pensa.'),
  's': [
   'Abra a aba <b>Chalkboard</b> e escolha uma ferramenta na barra. '
   '(A aba tem esse nome em todos os idiomas.)',
   'Desenhe a <b>estrutura, as zonas e os níveis</b> que você está acompanhando, e '
   'escreva o raciocínio ao lado do desenho em vez de deixar na cabeça.',
   'Use várias lousas para separar ideias — uma por instrumento, ou uma por '
   'sessão — em vez de empilhar tudo em uma só.',
   '<b>Exporte a lousa</b> quando ela valer a pena. Esse arquivo exportado é o '
   'salvamento de verdade.',
  ],
  'tip': ('Suas lousas ficam <b>neste navegador</b>, não na sua conta. Elas '
          'sobrevivem a fechar a aba, mas não viajam para o seu celular e somem se '
          'você limpar os dados do site. Se uma lousa importa, exporte: essa é a '
          'única cópia realmente sua.'),
 },
 'synapse': {
  'd': ('Um mapa interativo de todas as metodologias, montado como um cérebro em '
        '3D: cada ramo é um método, cada nó um conceito, e cada nó abre um dossiê '
        'completo. Serve para explorar como as ideias se conectam, que é o que uma '
        'lista de aulas não consegue mostrar.'),
  's': [
   'Abra o <b>Synapse</b>, espere o mapa carregar e clique em um ramo para entrar '
   'em uma metodologia.',
   'Clique em um <b>nó</b> para ler o dossiê: o que é o conceito, como se '
   'identifica e como ele se relaciona com os vizinhos.',
   'Siga as conexões em vez de ler em ordem. Ver que dois métodos descrevem o '
   'mesmo comportamento com nomes diferentes é o sentido do mapa.',
   'Está tudo no seu idioma: o mapa, os nomes e os dossiês seguem o idioma que '
   'você escolheu.',
   'Use a seta <b>Menu</b> para voltar ao resto do aplicativo quando quiser.',
  ],
  'tip': ('Se você prefere ler longe da tela, a biblioteca completa está '
          'disponível em PDF na loja. É o mesmo conteúdo, diagramado para ser lido '
          'do começo ao fim.'),
 },
 'timing': {
  'd': ('Relógios ao vivo das sessões que de fato movem os instrumentos que você '
        'opera, mais o calendário econômico. A maior parte das perdas evitáveis '
        'não é análise ruim: é análise boa na hora errada.'),
  's': [
   'Na aba Analisar, abra o painel <b>Market Timing</b> para ver qual sessão está '
   'rodando agora.',
   'Passe o cursor por qualquer faixa para ver o horário exato no <b>horário de '
   'Nova York e no seu</b>. As faixas são iguais para todo mundo; só o relógio é '
   'seu.',
   'Aprenda o caráter de cada janela: as aberturas de Londres e Nova York tendem a '
   'expandir, os horários de almoço a lateralizar, e as máximas e mínimas da '
   'madrugada são o que a sessão do dia vai buscar.',
   'Filtre o <b>calendário econômico</b> pelo seu instrumento para ver só o que '
   'pode mexer com ele.',
   'Veja o que está agendado <b>antes</b> de planejar uma entrada, não depois que '
   'o preço já pulou.',
  ],
  'tip': ('Um relógio de sessão diz quando a participação costuma aparecer, não '
          'que algo vai acontecer. Uma semana de feriados mantém o mesmo horário '
          'com quase nenhum volume atrás.'),
 },
 'plans': {
  'd': ('O seu plano define de quanto em quanto tempo você pode analisar, quantos '
        'projetos guarda e quais ferramentas estão liberadas. Todo o resto — o '
        'guia, o mapa, o seu rank — é igual para todo mundo.'),
  's': [
   '<b>Free</b> — uma análise a cada 7 dias e um projeto salvo. O suficiente para '
   'ver exatamente o que a ferramenta faz antes de pagar qualquer coisa.',
   '<b>Standard</b> — uma análise a cada 24 horas, cinco projetos e acesso '
   'completo ao Fórum.',
   '<b>Premium</b> — cinco análises a cada 24 horas, dez projetos, o Fórum, o '
   '<b>Pre-Flight</b> e um tema visual próprio.',
   'As análises que sobraram aparecem sempre no painel da direita, então você não '
   'precisa contar.',
  ],
  'tip': ('Abra <b>Products → Planos</b> na barra lateral para comparar ou mudar '
          'de plano. Um plano pago é pago período a período e nunca se renova '
          'sozinho: nada é cobrado se você não decidir pagar de novo.'),
 },
 'account': {
  'd': ('Seu perfil, seu plano, seu rank e como a plataforma aparece e fala com '
        'você. Tudo muda na hora e nada disso mexe no trabalho que você já '
        'salvou.'),
  's': [
   'Abra o <b>painel da conta</b> no topo da coluna da direita para ver seu plano, '
   'seu rank e seus códigos.',
   'Troque de <b>idioma</b> quando quiser entre português, inglês, espanhol e '
   'francês — a plataforma inteira acompanha, análises incluídas.',
   'Alterne entre <b>claro e escuro</b> pela barra lateral, e troque de '
   '<b>tema</b> se você tiver algum: os temas mudam o visual da plataforma sem '
   'mover nada de lugar.',
   'Veja seu <b>rank</b> subir conforme ganha experiência analisando, respondendo '
   'quizzes e participando do fórum. O rank só sobe, nunca desce.',
   'Abra <b>Products → Settings</b> para os dados da sua conta, sua senha e sua '
   'sessão.',
  ],
  'tip': ('Chegar a um rank novo emite um certificado com página pública de '
          'verificação, então dá para compartilhar e qualquer um pode conferir. '
          'Ele atesta estudo nesta plataforma — não é um título profissional nem '
          'uma licença.'),
 },
}
