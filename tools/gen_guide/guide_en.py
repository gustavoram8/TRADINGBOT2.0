# -*- coding: utf-8 -*-
"""Contenido EN de la guía ampliada. Un dict por sección: lead, pasos y tip.

Los datos salen del código real (PLAN_LIMITS, PROJECT_LIMITS, los gates de
plan), no de lo que decía la guía vieja — que entre otras cosas seguía
diciendo que el foro era solo Premium.
"""

EN = {
 'analyze': {
  'd': ('Upload a screenshot of your chart and the AI walks through it the way an '
        'instructor would: what structure it can see, whether the timing and the '
        'confluences you claimed line up, and where the reasoning has holes. It '
        'never tells you to take the trade — it gives you things to check.'),
  's': [
   'Open the <b>Analyze</b> tab and set the context first: <b>instrument</b>, '
   '<b>direction</b>, <b>session</b>, and the <b>confluences</b> you believe are '
   'present. The AI reads a chart very differently depending on what you claim to '
   'be seeing, so this is not a formality.',
   'Pick the <b>methodology</b> you are trading. Each one has its own reading of '
   'the same candles — an order block matters under ICT and means nothing under '
   'Wyckoff — so choosing the wrong one produces an answer about a method you are '
   'not using.',
   'Upload a <b>screenshot</b>. Include enough chart to show where price came '
   'from: a zoomed-in image of the entry alone hides the context the analysis '
   'depends on. Marking your levels before the screenshot helps.',
   'Optionally write your <b>Trade Construction</b> — your reasoning in your own '
   'words, up to about 200 words. This is the part most people skip and it is the '
   'part that turns the answer from generic into specific to your idea.',
   'Press <b>Analyze</b>, then read it as a second opinion, not a verdict. The '
   'useful question is not "does it agree with me" but "did it see something I '
   'did not".',
   'Save the analysis to a <b>project</b> to keep a record. Reading three of your '
   'own old analyses side by side shows patterns in your mistakes that no single '
   'analysis can.',
  ],
  'tip': ('The counter on the right shows how many analyses you have left in the '
          'current window. It updates the moment an analysis finishes, so you '
          'never have to guess — and a failed upload does not consume one.'),
 },
 'preflight': {
  'd': ('A checklist you fill in <b>before</b> you enter, not after. Its whole '
        'purpose is to make you state your rules while you still have nothing at '
        'risk, because the moment money is on the line your reasoning changes '
        'without asking permission.'),
  's': [
   'Open <b>Pre-Flight</b> and create a checklist for the setup you are looking '
   'at. Do it before you click buy or sell — a checklist filled in after entry is '
   'a diary, not a filter.',
   'Work through each item honestly: <b>bias</b>, <b>session</b>, <b>risk</b> and '
   '<b>invalidation</b>. Invalidation is the one that matters most: if you cannot '
   'say what would prove you wrong, you do not have a trade, you have an opinion.',
   'Answer with what is actually on the chart, not with what you hope. The '
   'checklist only works if it can tell you no.',
   'If an item does not pass, that is a result, not a failure. A setup that fails '
   'your own rules is information you paid nothing for.',
   'Keep your checklists. Going back over the ones you overrode is the fastest '
   'way to find out which rule you keep breaking.',
  ],
  'tip': ('Pre-Flight is a Premium tool, and you can keep up to ten checklists — '
          'enough to cover the setups you actually trade rather than every idea '
          'you look at.'),
 },
 'quiz': {
  'd': ('A question bank across the methodologies the platform teaches, in rising '
        'levels of difficulty, plus one very hard question a day. It is designed '
        'to find the gaps you did not know you had — not to make you feel good '
        'about what you already know.'),
  's': [
   'Open the <b>Quiz</b> tab and pick a methodology and a topic — order blocks, '
   'market structure, accumulation, chart patterns and so on.',
   'Choose a level. <b>Beginner</b> checks definitions, <b>intermediate</b> '
   'checks whether you can apply them, and <b>advanced</b> puts two rules in '
   'conflict so you have to know which one wins.',
   'Answer, then read the explanation even when you got it right — a lucky guess '
   'and real knowledge look identical on the score.',
   'Try a <b>hardcore scenario</b> when a topic feels easy: full situations with '
   'several plausible readings and only one that survives scrutiny.',
   'Come back for the <b>Daily Challenge</b>: one hard question every day, and a '
   'streak that only grows if you keep showing up.',
  ],
  'tip': ('Your answers are checked on the server and the options are shuffled, '
          'so the answer key is never in the page and there is no pattern to '
          'exploit. Your daily question is also rotated per account — nobody can '
          'pass you the answer, because theirs is a different one.'),
 },
 'forum': {
  'd': ('A space to post setups, ask what you got wrong and follow traders whose '
        'reasoning you want to learn from. Available on <b>Standard and '
        'Premium</b>. Every post and image passes automatic moderation before it '
        'is published.'),
  's': [
   'Open <b>Forum</b> and read the general feed, or the <b>Following</b> tab to '
   'see only the traders you follow.',
   'Use <b>New post</b> to share a setup or a question. Posting the chart with '
   'your reasoning gets you far better answers than posting the chart alone.',
   'Join or create a <b>community</b> for a methodology or a market, and post '
   'there when the topic is narrow enough that the general feed would bury it.',
   'React and reply to other traders. Answering someone else forces you to put '
   'your own reasoning into words, which is where the gaps show up.',
   'Use <b>Saved</b> to keep posts worth rereading, and <b>Messages</b> for a '
   'private conversation with another trader.',
  ],
  'tip': ('Moderation runs before publishing, not after complaints, and it covers '
          'text and images. It is there so nobody has to scroll past insults or '
          'signal-selling to reach the useful discussion.'),
 },
 'chalk': {
  'd': ('A free drawing board for thinking with your hands: sketch the structure, '
        'mark the levels, write the plan next to it. Useful precisely because it '
        'is not a chart — nothing moves while you think.'),
  's': [
   'Open the <b>Chalkboard</b> tab and pick a tool from the toolbar.',
   'Sketch the <b>structure, zones and levels</b> you are watching, and write the '
   'reasoning next to the drawing instead of keeping it in your head.',
   'Use several boards to separate ideas — one per instrument, or one per '
   'session — rather than piling everything onto one.',
   '<b>Export the board</b> when it is worth keeping. That exported file is the '
   'real save.',
  ],
  'tip': ('Your boards live in <b>this browser</b>, not in your account. They '
          'survive closing the tab, but they do not travel to your phone and they '
          'disappear if you clear site data. If a board matters, export it — that '
          'is the only copy that is genuinely yours.'),
 },
 'synapse': {
  'd': ('An interactive map of every methodology the platform covers, built as a '
        '3D brain: each branch is a method, each node a concept, and each node '
        'opens a full dossier. It is for exploring how ideas connect, which a '
        'list of lessons cannot show you.'),
  's': [
   'Open <b>Synapse</b> and let the map load, then click a branch to open a '
   'methodology.',
   'Click a <b>node</b> to read its dossier: what the concept is, how it is '
   'identified, and how it relates to the concepts next to it.',
   'Follow the connections rather than reading in order. Seeing that two methods '
   'describe the same behaviour with different names is the point of the map.',
   'Everything is available in your language — the map, the names and the '
   'dossiers all follow the language you picked.',
   'Use the <b>Menu</b> arrow to return to the rest of the app whenever you want.',
  ],
  'tip': ('If you prefer to read away from the screen, the complete library is '
          'available as a PDF from the store. It is the same content, laid out '
          'for reading start to finish.'),
 },
 'timing': {
  'd': ('Live clocks for the sessions that actually move the instruments you '
        'trade, plus the economic calendar. Most avoidable losses are not bad '
        'analysis — they are good analysis at the wrong hour.'),
  's': [
   'On the Analyze tab, open the <b>Market Timing</b> panel to see which session '
   'is running right now.',
   'Hover any band to read its exact time in <b>New York time and your own local '
   'time</b>. The bands are the same for everyone; only the clock is yours.',
   'Learn the character of each window: the London and New York opens tend to '
   'expand, the lunch hours tend to chop, and the ranges built overnight are what '
   'the day session reaches for.',
   'Filter the <b>economic calendar</b> by your instrument so you only see the '
   'releases that can move it.',
   'Check what is scheduled <b>before</b> you plan an entry, not after price has '
   'already jumped.',
  ],
  'tip': ('A session clock tells you when participation usually shows up, not '
          'that something will happen. Holiday weeks keep the same clock with '
          'almost none of the volume behind it.'),
 },
 'plans': {
  'd': ('Your plan sets how often you can run an analysis, how many projects you '
        'can keep, and which tools are unlocked. Everything else — the guide, the '
        'map, your rank — is the same for everyone.'),
  's': [
   '<b>Free</b> — one analysis every 7 days and one saved project. Enough to see '
   'exactly what the tool does before paying anything.',
   '<b>Standard</b> — one analysis every 24 hours, five projects, and full access '
   'to the Forum.',
   '<b>Premium</b> — five analyses every 24 hours, ten projects, the Forum, '
   '<b>Pre-Flight</b>, and its own visual theme.',
   'Your remaining analyses are always shown in the right-hand panel, so you '
   'never have to count them yourself.',
  ],
  'tip': ('Open <b>Products → Plans</b> in the sidebar to compare them or change '
          'plan. A paid plan is paid period by period and never renews on its '
          'own: nothing is charged unless you decide to pay again.'),
 },
 'account': {
  'd': ('Your profile, your plan, your rank and how the platform looks and speaks '
        'to you. All of it changes instantly and none of it affects your saved '
        'work.'),
  's': [
   'Open the <b>account panel</b> at the top of the right rail to see your plan, '
   'your rank and your codes.',
   'Switch <b>language</b> at any time between English, Spanish, French and '
   'Portuguese — the whole platform follows, including the analyses.',
   'Switch between <b>light and dark</b> from the sidebar, and change your '
   '<b>theme</b> if you own one: themes restyle the platform without moving '
   'anything around.',
   'Watch your <b>rank</b> climb as you earn experience by analyzing, answering '
   'quizzes and taking part in the forum. Rank only ever goes up.',
   'Open <b>Products → Settings</b> for your account details, your password and '
   'your session.',
  ],
  'tip': ('Reaching a new rank issues a certificate with a public verification '
          'page, so it can be shared and checked by anyone. It certifies study on '
          'this platform — it is not a professional qualification or a licence.'),
 },
}
