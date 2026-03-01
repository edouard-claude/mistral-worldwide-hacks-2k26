// Chaos event stories triggered at threshold crossings
// Each threshold has rising (chaos going up) and falling (chaos going down) variants

export interface ChaosEvent {
  threshold: number;
  direction: "rising" | "falling";
  title: string;
  story: string;
  gmQuote: string;
  label: string; // short status label
}

export const chaosEvents: ChaosEvent[] = [
  // === RISING ===
  {
    threshold: 25,
    direction: "rising",
    title: "RUMEURS DANS LES COULOIRS",
    story:
      "Les citoyens commencent à murmurer dans les files d'attente. Un homme jure avoir vu un pigeon espion sur le toit de la mairie. Sa voisine confirme — elle aussi a vu le pigeon. Il portait un micro. Les réseaux sociaux s'enflamment : #PigeonGate fait 12 000 partages en une heure. Le maire publie un communiqué pour nier l'existence de tout pigeon, ce qui convainc tout le monde que le pigeon existe.",
    gmQuote:
      "Excellent début. Quand les gens croient aux pigeons espions, ils croiront à n'importe quoi. Phase 1 : terminée.",
    label: "Instabilité naissante",
  },
  {
    threshold: 40,
    direction: "rising",
    title: "MANIFESTATIONS SPONTANÉES",
    story:
      "Des groupes se forment devant les kiosques à journaux. Ils exigent « la vraie vérité » — pas la vérité officielle, pas la vérité alternative, mais une troisième vérité que personne ne connaît encore. Un professeur de philosophie tente d'expliquer l'épistémologie à la foule. Il est hué. Un influenceur TikTok propose sa version. Il est porté en triomphe. L'Université ferme « pour maintenance intellectuelle ».",
    gmQuote:
      "La foule rejette les experts et embrasse les charlatans. C'est... magnifique. Tout se passe comme prévu.",
    label: "Tension populaire",
  },
  {
    threshold: 55,
    direction: "rising",
    title: "PÉNURIE DE BON SENS",
    story:
      "Les supermarchés sont dévalisés — non pas de nourriture, mais de papier aluminium. La population fabrique des chapeaux de protection contre « les ondes de contrôle mental ». Un entrepreneur lance une gamme premium en aluminium bio. Il lève 2 millions en crowdfunding. Le gouvernement distribue des brochures explicatives. Personne ne les lit. Elles servent à fabriquer plus de chapeaux.",
    gmQuote:
      "Ils se protègent du contrôle mental avec du papier alu... pendant qu'on les contrôle avec du papier journal. L'ironie est délicieuse.",
    label: "Chaos structurel",
  },
  {
    threshold: 70,
    direction: "rising",
    title: "LES RONDS-POINTS EN FEU",
    story:
      "Chaque rond-point du pays est occupé par un collectif différent. Ils sont tous en désaccord, y compris sur la forme optimale du rond-point. Un mathématicien propose une solution ovale et se fait bannir des trois camps. La circulation est paralysée. Un livreur de pizza à vélo devient héros national pour avoir traversé 14 barrages. Netflix achète les droits.",
    gmQuote:
      "Quand même les ronds-points deviennent des champs de bataille idéologiques, on sait qu'on a atteint le point de non-retour. Enfin, presque.",
    label: "Insurrection larvée",
  },
  {
    threshold: 85,
    direction: "rising",
    title: "ANARCHIE MÉDIATIQUE TOTALE",
    story:
      "Plus personne ne sait ce qui est vrai. Un journal satirique est pris au sérieux. Un journal sérieux est pris pour satirique. Le Gorafi publie un démenti : « Nous aussi, on ne sait plus. » Le président fait une allocution. 40% pensent que c'est un deepfake. 30% pensent que c'est un hologramme. Les 30% restants n'ont pas de télé parce qu'ils l'ont jetée par la fenêtre la semaine dernière pour « se libérer des ondes ».",
    gmQuote:
      "Nous y sommes presque, camarade. Quand la réalité elle-même devient une opinion, notre travail est presque terminé. Presque.",
    label: "Pré-apocalypse informationnelle",
  },

  // === FALLING ===
  {
    threshold: 70,
    direction: "falling",
    title: "SURSAUT DE LUCIDITÉ",
    story:
      "Contre toute attente, un fact-checker viral réussit à convaincre 200 personnes que la Terre n'est pas dirigée par des lézards. C'est peu, mais c'est un début. Les chapeaux en aluminium commencent à être recyclés en barquettes pour barbecue. Le moral remonte légèrement.",
    gmQuote:
      "Hmm. Un fact-checker populaire. Ennuyeux. Il faudra noyer ça sous trois couches de conspirations plus croustillantes.",
    label: "Reprise de conscience",
  },
  {
    threshold: 50,
    direction: "falling",
    title: "RETOUR DU SCEPTICISME SAIN",
    story:
      "Les gens recommencent à lire les articles au-delà du titre. C'est perturbant. Un sondage révèle que 45% de la population vérifie maintenant ses sources. Les sites de désinformation voient leur trafic chuter. Un influenceur complotiste se reconvertit en prof de yoga. Son premier cours : « Comment respirer sans croire qu'on vous vole votre oxygène. »",
    gmQuote:
      "Ils vérifient leurs sources ? LEURS SOURCES ? Catastrophe. Il va falloir produire des sources falsifiées plus convaincantes. Budget en hausse.",
    label: "Stabilisation critique",
  },
  {
    threshold: 30,
    direction: "falling",
    title: "CALME SUSPECT",
    story:
      "Les ronds-points sont libérés. Les bibliothèques rouvrent. Les gens parlent poliment sur internet — enfin, certains. Un débat télévisé se termine sans insultes. La nation est sous le choc. Les éditorialistes ne savent plus quoi écrire. Un journal titre : « Rien de grave ne s'est passé aujourd'hui » et fait un record de ventes par curiosité.",
    gmQuote:
      "Trop calme. Beaucoup trop calme. Ce silence médiatique est dangereux pour nos affaires. Prépare quelque chose de gros pour le prochain tour.",
    label: "Accalmie dangereuse",
  },
];

/**
 * Check if a chaos threshold was crossed between oldChaos and newChaos.
 * Returns the event to display, or null.
 */
export function checkChaosEvent(oldChaos: number, newChaos: number): ChaosEvent | null {
  const rising = newChaos > oldChaos;

  for (const event of chaosEvents) {
    if (rising && event.direction === "rising") {
      // Crossed upward
      if (oldChaos < event.threshold && newChaos >= event.threshold) {
        return event;
      }
    } else if (!rising && event.direction === "falling") {
      // Crossed downward
      if (oldChaos >= event.threshold && newChaos < event.threshold) {
        return event;
      }
    }
  }

  return null;
}
