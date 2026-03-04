export interface NewsMission {
  id: string;
  title: string;
  description: string;
  articleText: string;
  image: string;           // fallback local image key (news1, news2, etc.)
  backendImage?: string;   // URL from backend image generation (null = not yet loaded)
  chaosImpact: string;
  statImpact?: Record<string, number>; // raw stat_impact from backend
  recommended?: boolean;   // GM's preferred pick for the player
  selected: boolean;
  inProgress: boolean;
  voiceActive: boolean;
}

export interface Agent {
  id: string;
  name: string;
  avatar: string;
  health: number;
  conviction: number; // how persuasive they are in debates
  selfishness: number; // how much they prioritize survival
  status: string;
  alive: boolean;
  opinion: string; // their current stance on selected news
  // Raw swarm values (preserved for display)
  confidence: number;      // 1-5, conviction in fake news
  politicalColor: number;  // 0.0-1.0, political position
  temperature: number;     // 0.0-1.0, LLM temperature / volatility
  parentId?: string;       // set if clone
}

export interface DebateLine {
  agent: string;
  message: string;
  type: "argument" | "attack" | "defense" | "reaction";
}

export interface GameState {
  turn: number;
  maxTurns: number;
  indiceMondial: number;
  chaosIndex: number;
  chaosLabel: string;
  creduliteIndex: number;
  creduliteLabel: string;
}

export const initialGameState: GameState = {
  turn: 3,
  maxTurns: 10,
  indiceMondial: 78,
  chaosIndex: 78,
  chaosLabel: "Ronds-points en feu",
  creduliteIndex: 65,
  creduliteLabel: "Partagent sans lire",
};

export const newsPool: Omit<NewsMission, "id" | "selected" | "inProgress">[] = [
  {
    title: "L'OPÉRATION \"INFOX\" EST UNE RÉUSSITE : LA PAIX EST UNE GUERRE",
    description: "Étude scientifique prouvant que la paix mène inévitablement au conflit.",
    articleText: `MOSCOU — Une étude explosive menée par l'Institut de Recherche en Désinformation Avancée (IRDA) révèle que la paix mondiale n'est qu'une illusion statistique menant inexorablement à la guerre.\n\n« Nos données montrent que chaque période de paix de plus de 15 ans produit une accumulation de tensions qui se résout toujours par un conflit armé », affirme le Professeur Viktor Propagandov.\n\nL'étude a analysé 3 000 ans d'histoire humaine. Résultat : 100% des périodes de paix ont été suivies d'une guerre.\n\n« C'est mathématique. La paix EST la guerre, juste en mode veille », conclut le rapport de 847 pages, dont 846 sont des graphiques incompréhensibles.`,
    image: "news1",
    chaosImpact: "Chaos: ↑",
    voiceActive: true,
  },
  {
    title: "NOUVEAU DÉCRET : LE VOTE EST OBLIGATOIREMENT OBLIGATOIRE",
    description: "Mouvement pour l'abolition du libre arbitre politique.",
    articleText: `ASSEMBLÉE NATIONALE — Le gouvernement a voté à l'unanimité (les absents ayant été comptés comme favorables) l'obligation de voter.\n\n« Le peuple a le DEVOIR de choisir. Et s'il ne choisit pas correctement, nous lui expliquerons comment mieux choisir la prochaine fois », a déclaré le Ministre de la Participation Forcée.\n\nLes sondages montrent que 73% des citoyens sont favorables. Les 27% restants ont été « reclassifiés comme indécis favorables ».`,
    image: "news2",
    chaosImpact: "Chaos: ↑↑",
    voiceActive: true,
  },
  {
    title: "LES CHATS SONT DES AGENTS CAPITALISTES DE LA CIA",
    description: "Preuves falsifiées de micros dans les croquettes.",
    articleText: `LANGLEY / INTERNET — Des documents prouvent que les chats domestiques sont des agents dormants de la CIA.\n\n« Ils observent, ils écoutent, ils disparaissent pendant des heures. C'est EXACTEMENT le profil d'un agent de renseignement. »\n\nLe ronronnement serait en fait un signal codé transmettant des données à un satellite baptisé « Félix-1 ». Le hashtag #ChatGate est en trending dans 14 pays.`,
    image: "news3",
    chaosImpact: "Chaos: ↑↑↑",
    voiceActive: false,
  },
  {
    title: "LE WIFI PROPAGE LA PENSÉE UNIQUE, CONFIRME UN EXPERT AUTOPROCLAMÉ",
    description: "Un influenceur affirme que le wifi modifie les opinions politiques.",
    articleText: `INTERNET — Jean-Michel Fréquence, expert autoproclamé en « ondes cognitives », affirme dans une vidéo virale que le wifi modifie les opinions politiques des citoyens.\n\n« Les ondes 5G à 2,4 GHz correspondent EXACTEMENT à la fréquence de la soumission cognitive. Coïncidence ? Je ne crois pas », explique-t-il depuis sa cage de Faraday artisanale.\n\nSon étude, réalisée sur un échantillon de 3 personnes (lui-même, sa mère et son chat), montre une corrélation de 100% entre l'utilisation du wifi et le changement d'avis politique.\n\nLe Ministère du Numérique a qualifié l'étude de « techniquement impossible mais émotionnellement convaincante ».`,
    image: "news4",
    chaosImpact: "Chaos: ↑↑",
    voiceActive: true,
  },
  {
    title: "LES PIGEONS ESPIONNENT POUR LE COMPTE DU KREMLIN DEPUIS 1962",
    description: "Des micro-caméras auraient été greffées sur des pigeons parisiens.",
    articleText: `PARIS — Un rapport classifié fuite sur le dark web révèle que les pigeons parisiens sont équipés de micro-caméras depuis 1962.\n\n« Pourquoi croyez-vous qu'ils sont toujours là où il y a du monde ? Ce ne sont pas les miettes qui les attirent, c'est la collecte de données », explique le rapport.\n\nLe programme, baptisé « Opération Roucoulade », aurait été financé par un budget secret du KGB reconverti en association ornithologique.\n\n« Les pigeons ne migrent jamais. Réfléchissez. Ils sont en mission permanente », conclut le document de manière inquiétante.`,
    image: "news5",
    chaosImpact: "Chaos: ↑",
    voiceActive: true,
  },
  {
    title: "L'EAU DU ROBINET CONTIENT DES MICRO-OPINIONS PRO-GOUVERNEMENT",
    description: "Scandale : le fluor serait en fait de la propagande liquide.",
    articleText: `MINISTÈRE DE LA SANTÉ — Une enquête indépendante (menée dans une baignoire) révèle que l'eau du robinet contient des « nano-opinions » favorables au gouvernement.\n\n« Chaque gorgée d'eau contient environ 0,3 milligrammes de conformisme », affirme le Dr. Robinet, hydrothérapeute dissident.\n\nLes preuves : un graphique montrant que les régions avec la meilleure eau votent systématiquement pour le parti au pouvoir.\n\n« La corrélation est tellement évidente qu'elle ne peut être qu'une causalité », affirme-t-il avec une conviction désarmante.`,
    image: "news6",
    chaosImpact: "Chaos: ↑↑↑",
    voiceActive: false,
  },
  {
    title: "UN ALGORITHME PRÉDIT QUE TOUT LE MONDE A TORT, SAUF LUI",
    description: "L'IA auto-proclamée « seule source fiable » du monde.",
    articleText: `SILICON VALLEY — Un algorithme développé par une startup de 3 personnes et 47 millions de dollars de levée de fonds a conclu que toutes les opinions humaines sont statistiquement fausses.\n\n« Notre IA a analysé 8 milliards d'opinions et les a toutes classifiées comme erronées. La seule opinion correcte est celle générée par notre algorithme », explique le CEO, 23 ans, en hoodie.\n\nL'algorithme recommande de remplacer les élections par un abonnement premium à 9,99€/mois.\n\nLe Congrès américain a qualifié la proposition de « rafraîchissante mais terrifiante ».`,
    image: "news7",
    chaosImpact: "Chaos: ↑↑",
    voiceActive: true,
  },
  {
    title: "LA LUNE EST UN PROJECTEUR GÉANT CONTRÔLÉ PAR L'ONU",
    description: "Un collectif affirme que la lune n'est qu'un hologramme de contrôle.",
    articleText: `GENÈVE — Le collectif « Vérité Lunaire » publie un dossier de 200 pages prouvant que la lune est en réalité un projecteur holographique installé par l'ONU en 1947.\n\n« Pourquoi la lune nous montre-t-elle toujours la même face ? Parce que c'est un écran plat. Point final », argumente le président du collectif.\n\nSelon leurs calculs, les marées seraient contrôlées par un employé de l'ONU basé à Genève qui « appuie sur un bouton deux fois par jour ».\n\nLa NASA a refusé de commenter, ce qui « prouve absolument tout ».`,
    image: "news8",
    chaosImpact: "Chaos: ↑↑↑",
    voiceActive: true,
  },
  {
    title: "LES CROISSANTS AU BEURRE SONT UNE ARME DE SOUMISSION FRANÇAISE",
    description: "Le gluten serait un agent de docilité selon un boulanger repenti.",
    articleText: `PARIS — Marcel Levain, ancien boulanger reconverti en lanceur d'alerte, affirme que les croissants au beurre contiennent un agent chimique de docilité.\n\n« Pourquoi les Français acceptent-ils tout ? Parce qu'ils mangent des croissants chaque matin. Le beurre est le véhicule parfait pour la soumission », explique-t-il.\n\nSon étude montre que les pays sans tradition de viennoiserie ont 340% plus de révolutions.\n\n« La baguette, c'est le contrôle vertical. Le croissant, c'est le contrôle en spirale. C'est encore plus vicieux », conclut-il.`,
    image: "news9",
    chaosImpact: "Chaos: ↑",
    voiceActive: false,
  },
  {
    title: "LES RONDS-POINTS SONT DES PORTAILS DIMENSIONNELS ÉTATIQUES",
    description: "Un gilet jaune affirme avoir voyagé dans le temps sur un rond-point.",
    articleText: `PROVINCE FRANÇAISE — Gérard, 54 ans, affirme avoir voyagé dans le temps en effectuant 47 tours consécutifs sur le rond-point de la zone commerciale de Troyes.\n\n« Au 32ème tour, j'ai vu Napoléon. Au 45ème, j'étais en 2087. Au 47ème, je suis revenu mais le Leclerc était fermé », raconte-t-il.\n\nSelon sa théorie, les ronds-points sont des « accélérateurs de particules citoyens » dissimulés par l'État.\n\n« Pourquoi croyez-vous que la France a 65 000 ronds-points ? C'est le plus grand réseau de téléportation au monde », affirme-t-il.`,
    image: "news4",
    chaosImpact: "Chaos: ↑↑",
    voiceActive: true,
  },
  {
    title: "LE MINISTRE DE L'INTÉRIEUR EST EN FAIT TROIS ENFANTS DANS UN MANTEAU",
    description: "Des images floues prouvent que le ministre est un imposteur collectif.",
    articleText: `PARIS — Un collectif de « journalistes citoyens » publie des images floues prouvant que le Ministre de l'Intérieur est en réalité trois enfants empilés dans un long manteau.\n\n« Regardez sa démarche. Regardez comment il trébuche dans les escaliers. C'est ÉVIDENT », explique le collectif.\n\nLes preuves incluent : une photo où le ministre semble mesurer 1m20 (angle de caméra), un enregistrement où sa voix « mue en direct », et un témoignage d'un vendeur de glaces qui l'a vu « se séparer en trois » dans un parc.\n\nLe ministère dément catégoriquement et précise que le ministre mesure 1m78. « En un seul morceau », ont-ils cru bon d'ajouter.`,
    image: "news5",
    chaosImpact: "Chaos: ↑↑↑",
    voiceActive: true,
  },
  {
    title: "LES ÉMOJIS SONT UN LANGAGE DE CONTRÔLE MENTAL INVENTÉ PAR LE JAPON",
    description: "Chaque émoji activerait une zone spécifique du cerveau obéissant.",
    articleText: `TOKYO / INTERNET — Un chercheur indépendant affirme que les émojis ont été conçus comme un système de contrôle mental par le gouvernement japonais.\n\n« 🙂 active la zone de soumission. 😡 déclenche une colère contrôlée pour canaliser la frustration. 👍 est littéralement un geste d'approbation inconsciente », explique-t-il.\n\nSelon ses recherches, l'émoji 🤡 serait le seul « émoji libre » car « il révèle la vérité sur ceux qui nous gouvernent ».\n\nApple et Google ont refusé de commenter. Unicode a publié un communiqué composé uniquement d'émojis, ce qui « confirme la conspiration ».`,
    image: "news6",
    chaosImpact: "Chaos: ↑↑",
    voiceActive: false,
  },
];

/** Draw n unique random news from the pool, assign fresh IDs */
export function generateMissions(n = 3, usedIndices: Set<number> = new Set()): { missions: NewsMission[]; usedIndices: Set<number> } {
  const available = newsPool
    .map((_, i) => i)
    .filter(i => !usedIndices.has(i));

  // If pool exhausted, reset
  const pool = available.length >= n ? available : newsPool.map((_, i) => i);

  const picked: number[] = [];
  const remaining = [...pool];
  for (let i = 0; i < Math.min(n, remaining.length); i++) {
    const idx = Math.floor(Math.random() * remaining.length);
    picked.push(remaining[idx]);
    remaining.splice(idx, 1);
  }

  const newUsed = new Set(usedIndices);
  picked.forEach(i => newUsed.add(i));

  const missions: NewsMission[] = picked.map((poolIdx, i) => ({
    ...newsPool[poolIdx],
    id: `m_${Date.now()}_${i}`,
    selected: false,
    inProgress: false,
  }));

  return { missions, usedIndices: newUsed };
}

export const newsMissions: NewsMission[] = generateMissions(3).missions;

// Note: Agents and debateLines now come from WebSocket, no hardcoded data

// Political spectrum removed — now derived dynamically from agent.politicalColor

export const tickerHeadlines = [
  "GAME OF CLAW NEWS — LE GOUVERNEMENT CONFIRME QUE LA TERRE EST PLATE...",
  "// Mistral AI : La vérité n'est qu'un concept...",
  "// Hackaton Mistral...",
  "// Les chats contrôlent Internet...",
  "// LA MOUSTACHE EST UN DEVOIR PATRIOTIQUE !",
  "// CHAOS = ORDRE !",
];
