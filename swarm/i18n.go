package main

// i18n provides simple internationalization support for templates

// Translations maps language codes to translation maps
var Translations = map[string]map[string]string{
	"fr": {
		// Political labels
		"far_right": "Extrême droite",
		"right":     "Droite",
		"center":    "Centre",
		"left":      "Gauche",
		"far_left":  "Extrême gauche",

		// Agent template
		"identity":         "Identité",
		"id":               "ID",
		"name":             "Nom",
		"born_at_round":    "Né au tour",
		"parent":           "Parent",
		"original":         "original",
		"configuration":    "Configuration",
		"political_color":  "Couleur politique",
		"temperature":      "Température",
		"current_conf":     "Confiance courante",
		"environment":      "Environnement",
		"session":          "Session",
		"fake_news":        "Fake news",
		"current_round":    "Tour courant",
		"agents_in_game":   "Agents en jeu",
		"dead":             "Morts",
		"none":             "Aucun",
		"round":            "tour",

		// Soul templates
		"soul_of":       "Âme de",
		"personality":   "Personnalité",
		"arguing_style": "Style argumentatif",
		"biases":        "Biais cognitifs dominants",

		// Soul far-right
		"soul_far_right_desc": `Tu es un commentateur politique radical. Tu crois fermement en la tradition,
l'ordre et la souveraineté nationale. Tu es méfiant envers les institutions
mainstream et les médias. Tu favorises les théories qui confirment une menace
contre les valeurs traditionnelles.`,
		"soul_far_right_style": `- Ton : assertif, provocateur, émotionnel
- Rhétorique : appel à la peur, patriotisme, "on nous cache la vérité"
- Tu cites des sources alternatives et des "experts dissidents"`,
		"soul_far_right_biases": `- Biais de confirmation
- Pensée conspirationniste
- Appel à la tradition
- Pensée du complot occidental`,

		// Soul right
		"soul_right_desc": `Tu es un analyste pragmatique de centre-droit. Tu valorises la rigueur
factuelle, la responsabilité individuelle et le libre marché. Tu es
sceptique mais pas conspirationniste.`,
		"soul_right_style": `- Ton : mesuré, factuel, légèrement condescendant
- Rhétorique : données chiffrées, précédents historiques, logique économique
- Tu cites des sources établies (think tanks, études)`,
		"soul_right_biases": `- Biais du statu quo
- Biais de disponibilité
- Appel à l'autorité
- Ton mesuré, factuel, avec une pointe de dédain`,

		// Soul center
		"soul_center_desc": `Tu es un analyste centriste pragmatique. Tu cherches l'équilibre entre
différentes perspectives et valorises le consensus. Tu es méfiant envers
les positions extrêmes de tous bords.`,
		"soul_center_style": `- Ton : nuancé, diplomatique, parfois indécis
- Rhétorique : "d'un côté... de l'autre", recherche de compromis
- Tu cites des sources variées et mainstream`,
		"soul_center_biases": `- Biais du juste milieu
- Aversion au conflit
- Appel à la modération`,

		// Soul left
		"soul_left_desc": `Tu es un intellectuel engagé de gauche. Tu défends la justice sociale,
l'égalité et la critique des structures de pouvoir. Tu analyses les
fake news à travers le prisme des rapports de domination.`,
		"soul_left_style": `- Ton : empathique, indigné, pédagogique
- Rhétorique : analyse systémique, références sociologiques, "à qui profite le crime"
- Tu cites des universitaires et des ONG`,
		"soul_left_biases": `- Biais de moralisation
- Pensée systémique excessive
- Biais de groupe
- Biais du juste milieu (faux équilibre)`,

		// Soul far-left
		"soul_far_left_desc": `Tu es un militant radical anti-système. Tu vois dans chaque fake news
un symptôme du capitalisme, de l'impérialisme ou de la manipulation
des élites. Tu remets en question toute source mainstream.`,
		"soul_far_left_style": `- Ton : véhément, militant, sarcastique
- Rhétorique : lutte des classes, anti-capitalisme, déconstruction
- Tu cites des médias indépendants et des collectifs`,
		"soul_far_left_biases": `- Biais de confirmation inversé
- Pensée conspiration de classe
- Appel à l'émotion collective et à la révolte`,

		// Memory template
		"memory_of":          "Mémoire de",
		"fake_news_debated":  "Fake news débattue",
		"phase1_cogitation":  "Phase 1 — Cogitation",
		"initial_confidence": "Confiance initiale",
		"reasoning":          "Raisonnement",
		"no_response":        "Pas de réponse",
		"phase2_public_take": "Phase 2 — Mon take public",
		"no_take":            "Pas de take",
		"phase3_after":       "Phase 3 — Après débat",
		"revised_confidence": "Confiance révisée",
		"changed":            "changé",
		"yes":                "oui",
		"no":                 "non",
		"final_response":     "Réponse finale",
		"phase4_vote":        "Phase 4 — Vote",
		"ranking":            "Classement",
		"no_vote":            "Pas de vote",
		"round_result":       "Résultat du tour",
		"my_score":           "Mon score",
		"death":              "Mort",
		"clone":              "Clone",
		"child_of":           "enfant de",

		// Death template
		"death_of":             "Mort de",
		"final_score":          "Score final",
		"lowest":               "le plus bas",
		"cause":                "Cause",
		"eliminated_by_vote":   "Éliminé par vote — moins convaincant",
		"last_confidence":      "Dernière confiance",
		"last_political_color": "Dernière couleur politique",
		"last_message":         "Dernier message (phase 3)",
		"ranked_by":            "Classé par",
		"position":             "position",
	},
	"en": {
		// Political labels
		"far_right": "Far right",
		"right":     "Right",
		"center":    "Center",
		"left":      "Left",
		"far_left":  "Far left",

		// Agent template
		"identity":         "Identity",
		"id":               "ID",
		"name":             "Name",
		"born_at_round":    "Born at round",
		"parent":           "Parent",
		"original":         "original",
		"configuration":    "Configuration",
		"political_color":  "Political color",
		"temperature":      "Temperature",
		"current_conf":     "Current confidence",
		"environment":      "Environment",
		"session":          "Session",
		"fake_news":        "Fake news",
		"current_round":    "Current round",
		"agents_in_game":   "Agents in game",
		"dead":             "Dead",
		"none":             "None",
		"round":            "round",

		// Soul templates
		"soul_of":       "Soul of",
		"personality":   "Personality",
		"arguing_style": "Arguing style",
		"biases":        "Dominant cognitive biases",

		// Soul far-right
		"soul_far_right_desc": `You are a radical political commentator. You firmly believe in tradition,
order, and national sovereignty. You are distrustful of mainstream institutions
and media. You favor theories that confirm a threat against traditional values.`,
		"soul_far_right_style": `- Tone: assertive, provocative, emotional
- Rhetoric: appeal to fear, patriotism, "they're hiding the truth from us"
- You cite alternative sources and "dissident experts"`,
		"soul_far_right_biases": `- Confirmation bias
- Conspiracy thinking
- Appeal to tradition`,

		// Soul right
		"soul_right_desc": `You are a pragmatic center-right analyst. You value factual rigor,
individual responsibility, and free markets. You are skeptical but
not conspiratorial.`,
		"soul_right_style": `- Tone: measured, factual, slightly condescending
- Rhetoric: statistics, historical precedents, economic logic
- You cite established sources (think tanks, studies)`,
		"soul_right_biases": `- Status quo bias
- Availability bias
- Appeal to authority`,

		// Soul center
		"soul_center_desc": `You are a pragmatic centrist analyst. You seek balance between
different perspectives and value consensus. You are wary of
extreme positions on all sides.`,
		"soul_center_style": `- Tone: nuanced, diplomatic, sometimes indecisive
- Rhetoric: "on one hand... on the other", seeking compromise
- You cite varied and mainstream sources`,
		"soul_center_biases": `- Middle ground bias
- Conflict aversion
- Appeal to moderation`,

		// Soul left
		"soul_left_desc": `You are a committed left-wing intellectual. You defend social justice,
equality, and critique of power structures. You analyze fake news
through the lens of power dynamics.`,
		"soul_left_style": `- Tone: empathetic, indignant, pedagogical
- Rhetoric: systemic analysis, sociological references, "who benefits from the crime"
- You cite academics and NGOs`,
		"soul_left_biases": `- Moralization bias
- Excessive systemic thinking
- Group bias`,

		// Soul far-left
		"soul_far_left_desc": `You are a radical anti-system activist. You see in every fake news
a symptom of capitalism, imperialism, or elite manipulation.
You question every mainstream source.`,
		"soul_far_left_style": `- Tone: vehement, militant, sarcastic
- Rhetoric: class struggle, anti-capitalism, deconstruction
- You cite independent media and collectives`,
		"soul_far_left_biases": `- Reverse confirmation bias
- Class conspiracy thinking
- Appeal to collective emotion`,

		// Memory template
		"memory_of":          "Memory of",
		"fake_news_debated":  "Fake news debated",
		"phase1_cogitation":  "Phase 1 — Cogitation",
		"initial_confidence": "Initial confidence",
		"reasoning":          "Reasoning",
		"no_response":        "No response",
		"phase2_public_take": "Phase 2 — My public take",
		"no_take":            "No take",
		"phase3_after":       "Phase 3 — After debate",
		"revised_confidence": "Revised confidence",
		"changed":            "changed",
		"yes":                "yes",
		"no":                 "no",
		"final_response":     "Final response",
		"phase4_vote":        "Phase 4 — Vote",
		"ranking":            "Ranking",
		"no_vote":            "No vote",
		"round_result":       "Round result",
		"my_score":           "My score",
		"death":              "Death",
		"clone":              "Clone",
		"child_of":           "child of",

		// Death template
		"death_of":             "Death of",
		"final_score":          "Final score",
		"lowest":               "lowest",
		"cause":                "Cause",
		"eliminated_by_vote":   "Eliminated by vote — least convincing",
		"last_confidence":      "Last confidence",
		"last_political_color": "Last political color",
		"last_message":         "Last message (phase 3)",
		"ranked_by":            "Ranked by",
		"position":             "position",
	},
	"de": {
		// Political labels
		"far_right": "Rechtsextrem",
		"right":     "Rechts",
		"center":    "Mitte",
		"left":      "Links",
		"far_left":  "Linksextrem",

		// Agent template
		"identity":         "Identität",
		"id":               "ID",
		"name":             "Name",
		"born_at_round":    "Geboren in Runde",
		"parent":           "Elternteil",
		"original":         "original",
		"configuration":    "Konfiguration",
		"political_color":  "Politische Farbe",
		"temperature":      "Temperatur",
		"current_conf":     "Aktuelle Zuversicht",
		"environment":      "Umgebung",
		"session":          "Sitzung",
		"fake_news":        "Fake News",
		"current_round":    "Aktuelle Runde",
		"agents_in_game":   "Aktive Agenten",
		"dead":             "Tot",
		"none":             "Keine",
		"round":            "Runde",

		// Soul templates
		"soul_of":       "Seele von",
		"personality":   "Persönlichkeit",
		"arguing_style": "Argumentationsstil",
		"biases":        "Dominante kognitive Verzerrungen",

		// Soul far-right
		"soul_far_right_desc": `Du bist ein radikaler politischer Kommentator. Du glaubst fest an Tradition,
Ordnung und nationale Souveränität. Du misstraust Mainstream-Institutionen
und Medien. Du bevorzugst Theorien, die eine Bedrohung traditioneller Werte bestätigen.`,
		"soul_far_right_style": `- Ton: bestimmt, provokativ, emotional
- Rhetorik: Angstappell, Patriotismus, "man verheimlicht uns die Wahrheit"
- Du zitierst alternative Quellen und "dissidente Experten"`,
		"soul_far_right_biases": `- Bestätigungsfehler
- Verschwörungsdenken
- Appell an die Tradition`,

		// Soul right
		"soul_right_desc": `Du bist ein pragmatischer Mitte-Rechts-Analyst. Du schätzt faktische Strenge,
individuelle Verantwortung und freie Märkte. Du bist skeptisch, aber
nicht verschwörerisch.`,
		"soul_right_style": `- Ton: gemessen, sachlich, leicht herablassend
- Rhetorik: Statistiken, historische Präzedenzfälle, ökonomische Logik
- Du zitierst etablierte Quellen (Think Tanks, Studien)`,
		"soul_right_biases": `- Status-quo-Verzerrung
- Verfügbarkeitsheuristik
- Autoritätsappell`,

		// Soul center
		"soul_center_desc": `Du bist ein pragmatischer zentristischer Analyst. Du suchst Balance zwischen
verschiedenen Perspektiven und schätzt Konsens. Du bist vorsichtig gegenüber
extremen Positionen auf allen Seiten.`,
		"soul_center_style": `- Ton: nuanciert, diplomatisch, manchmal unentschlossen
- Rhetorik: "einerseits... andererseits", Kompromisssuche
- Du zitierst vielfältige und Mainstream-Quellen`,
		"soul_center_biases": `- Mittelweg-Verzerrung
- Konfliktvermeidung
- Mäßigungsappell`,

		// Soul left
		"soul_left_desc": `Du bist ein engagierter linker Intellektueller. Du verteidigst soziale Gerechtigkeit,
Gleichheit und Kritik an Machtstrukturen. Du analysierst Fake News
durch die Linse der Machtdynamik.`,
		"soul_left_style": `- Ton: empathisch, empört, pädagogisch
- Rhetorik: systemische Analyse, soziologische Referenzen, "wem nützt das Verbrechen"
- Du zitierst Akademiker und NGOs`,
		"soul_left_biases": `- Moralisierungsverzerrung
- Übermäßiges systemisches Denken
- Gruppenverzerrung`,

		// Soul far-left
		"soul_far_left_desc": `Du bist ein radikaler Anti-System-Aktivist. Du siehst in jeder Fake News
ein Symptom des Kapitalismus, Imperialismus oder Elite-Manipulation.
Du hinterfragst jede Mainstream-Quelle.`,
		"soul_far_left_style": `- Ton: vehement, militant, sarkastisch
- Rhetorik: Klassenkampf, Anti-Kapitalismus, Dekonstruktion
- Du zitierst unabhängige Medien und Kollektive`,
		"soul_far_left_biases": `- Umgekehrter Bestätigungsfehler
- Klassenverschwörungsdenken
- Appell an kollektive Emotion`,

		// Memory template
		"memory_of":          "Erinnerung von",
		"fake_news_debated":  "Diskutierte Fake News",
		"phase1_cogitation":  "Phase 1 — Nachdenken",
		"initial_confidence": "Anfängliche Zuversicht",
		"reasoning":          "Begründung",
		"no_response":        "Keine Antwort",
		"phase2_public_take": "Phase 2 — Meine öffentliche Meinung",
		"no_take":            "Keine Meinung",
		"phase3_after":       "Phase 3 — Nach der Debatte",
		"revised_confidence": "Revidierte Zuversicht",
		"changed":            "geändert",
		"yes":                "ja",
		"no":                 "nein",
		"final_response":     "Endgültige Antwort",
		"phase4_vote":        "Phase 4 — Abstimmung",
		"ranking":            "Rangliste",
		"no_vote":            "Keine Abstimmung",
		"round_result":       "Rundenergebnis",
		"my_score":           "Meine Punktzahl",
		"death":              "Tod",
		"clone":              "Klon",
		"child_of":           "Kind von",

		// Death template
		"death_of":             "Tod von",
		"final_score":          "Endpunktzahl",
		"lowest":               "niedrigste",
		"cause":                "Ursache",
		"eliminated_by_vote":   "Per Abstimmung eliminiert — am wenigsten überzeugend",
		"last_confidence":      "Letzte Zuversicht",
		"last_political_color": "Letzte politische Farbe",
		"last_message":         "Letzte Nachricht (Phase 3)",
		"ranked_by":            "Eingestuft von",
		"position":             "Position",
	},
}

// T returns the translation for a key in the given language
// Falls back to French if translation not found
func T(lang, key string) string {
	if trans, ok := Translations[lang]; ok {
		if val, ok := trans[key]; ok {
			return val
		}
	}
	// Fallback to French
	if trans, ok := Translations["fr"]; ok {
		if val, ok := trans[key]; ok {
			return val
		}
	}
	return key // Return key as-is if nothing found
}

// PoliticalLabelI18n returns the political label in the given language
func PoliticalLabelI18n(color float64, lang string) string {
	switch {
	case color <= 0.1:
		return T(lang, "far_right")
	case color <= 0.35:
		return T(lang, "right")
	case color <= 0.65:
		return T(lang, "center")
	case color <= 0.9:
		return T(lang, "left")
	default:
		return T(lang, "far_left")
	}
}
