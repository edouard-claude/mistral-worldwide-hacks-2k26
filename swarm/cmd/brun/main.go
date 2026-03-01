package main

import (
	"crypto/rand"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	mrand "math/rand"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/nats-io/nats.go"
)

// FakeNews titres du Gorafi
var fakeNewsTitles = []string{
	"Redoux – Elle retrouve le moral grâce au réchauffement climatique",
	"Sébastien Lecornu remporte le César du meilleur décor",
	"98% des jeunes pères de famille souffrent de surdité nocturne",
	"Municipales – À Rennes, une canette de 8.6 arrive en tête des sondages",
	"Jean-Luc Mélenchon : « Nous n'avons rien à voir avec La France insoumise »",
	"Milan-Cortina 2026 – Après avoir atteint 88 miles à l'heure, une équipe de bobsleigh se retrouve en 1955",
	"Dossiers Epstein – Le lien permettant d'accéder aux fichiers retrouvé mort dans la nuit",
	"Salon de l'agriculture – Un visiteur retrouvé sobre après 11h30",
	"La préfecture du Rhône scandalisée par la présence de néonazis à un rassemblement de néonazis",
	"12 heures après sa nomination, des cambrioleurs dérobent le nouveau président du Louvre",
	"Face à la douceur des températures, le gouvernement annonce l'activation du Plan Grand Tiède",
	"Pour préciser sa pensée, Martine Vassal annonce la sortie d'un livre intitulé \"Mon combat\"",
	"Fact-checking – Rachida Dati est-elle ministre de la culture ?",
	"Pour relancer la natalité, le gouvernement va interdire les préservatifs aux plus de 29 ans",
	"Test : Êtes-vous en crue ?",
	"Après les bébés nageurs, toujours aucun volontaire pour participer au premier cours de bébés base jumpers",
	"Après les gays, Karine Le Marchand déclare avoir \"un 6ème sens pour reconnaître les Noirs et les Arabes\"",
	"L'influenceur Cyril Schreiner abandonné à son tour par son chien Albert",
	"Par erreur, Didier Bourdon joue deux fois dans le même film",
	"Des scientifiques découvrent que la violence aurait été inventée avant les jeux vidéos",
	"Selon une étude, l'être humain n'utiliserait que 10% de son smartphone",
	"Après la SNCF, une maternité inaugure un espace « no kids »",
	"Pour dissuader les plus jeunes de fumer, le ministère de la Santé lance des vapoteuses goût « Jack Lang »",
	"Pour casser la routine, un couple de vautours décide de tourner dans l'autre sens",
	"Pour ou contre le col du fémur ?",
	"Prévue par Météo France, la tempête Benjam' a bien répondu \"présente\"",
	"Les artères coronaires rejoignent le mouvement Bloquons Tout : 150 000 morts",
	"Léon Marchand surpris en train de remonter la Garonne afin de s'accoupler",
	"Pour les rendre plus intéressants, les prochains JO d'hiver seront organisés en juillet",
	"France – Des dizaines de blessés dans des récupérations politiques mal maîtrisées",
	"Quatre stars américaines créent le malaise en raison de leur absence des dossiers Epstein",
	"Environ 17% des Français se déclareront candidat à l'élection présidentielle de 2027",
	"Après s'être plaint du mois de janvier, il se rend compte que sa vie est aussi nulle en février",
	"Fact-check – Pourquoi il est déconseillé de rouler à 200km/h sur les plaques de verglas",
	"Municipales – Jean Michel Aulas propose de remplacer la ville de Lyon par un stade de 1,4 million de places",
	"Caroline Lang assure qu'elle n'a « jamais entendu parler de Jack Lang »",
	"Show du Super Bowl – Donald Trump fait interdire la salsa, l'espagnol et l'Amérique du Sud",
	"Faute de bovins au Salon de l'Agriculture, les élus pourront tâter les fesses des agriculteurs",
	"Natalité – Emmanuel Macron recommande aux Français d'accrocher une photo de lui au-dessus de leur lit",
	"Milan-Cortina 2026 – La France échoue au pied du podium dans l'épreuve de raclette par équipe",
	"95% des Français souhaitent que François Hollande se présente, mais uniquement au conseil syndical de son immeuble",
	"Municipales 2026 – Sarah Knafo propose de renommer le pont des arts \"le pont des assistés\"",
	"Commission d'enquête sur l'Audiovisuel public – Léa Salamé affirme être mauvaise sans l'influence de personne",
	"Sébastien Lecornu affirme être victime d'une dépression post-budget 2026",
	"À nouveau accusé dans l'affaire Epstein, l'ancien Prince Andrew devient correspondant en Angleterre pour CNews",
	"Un restaurant d'altitude propose un menu sans entrée, sans plat et sans dessert à 29,90 €",
	"Toulouse – Il se présente aux urgences avec un char Leclerc dans le rectum",
	"Pour ou contre la météo à 30 jours avec un indice de fiabilité de 0,2/5 ?",
	"Fred la marmotte annonce six semaines de Sébastien Lecornu supplémentaires",
	"Le Parti socialiste annonce avoir terminé son programme pour la campagne présidentielle de 2022",
	"Le nom de Jeffrey Epstein retrouvé sur la liste des personnalités présentes sur l'île de Jeffrey Epstein",
	"Après ses excuses publiques, Jean-Marc Morandini nommé président du groupe Canal Plus",
	"Livret A – Les Français seront désormais taxés à 2 % pour pouvoir épargner",
	"76 % des Français favorables à la création de wagons SNCF sans cadres sup en conf' call",
	"Capgemini délocalise son siège social en 1942",
	"Fact-Check : C'est encore long 2026 ?",
	"Minneapolis – Pour plus de sécurité, les caméras de surveillance seront équipées d'une arme",
	"Pierre Niney viendra dîner chez vous ce soir pour faire la promotion de son prochain film",
	"Faire les choses à moitié : Pour ou",
	"Arno Klarsfeld propose de coudre un petit symbole sur la veste des OQTF",
	"Un paquet de Gitanes sans filtre interprétera Johnny Hallyday dans le biopic du chanteur",
	"La police de l'immigration déboulonne la Statue de la Liberté et l'expulse vers la France",
	"À 17 ans, il découvre que son père est hélas son vrai père",
	"Après les trains sans enfants, la SNCF renonce à lancer les trains sans retard",
	"Après plusieurs échecs, Raphaël Glucksmann demande finalement à Léa Salamé d'ouvrir un pot de moutarde",
	"Le centre-ville de Charleville-Mézières toujours absent des fonds d'écrans Windows",
	"Le dernier médecin qui acceptait de prendre des nouveaux patients meurt percuté par un bus",
	"Les supporters de Donald Trump inquiets de la \"trumpisation\" de Donald Trump",
	"Pour ou Contre la pharmacie du 700 Avenue Jean Moulin à Montauban ?",
	"Scandale – Les Mr. Freeze goût framboise étaient bien remplis de produit pour vitres",
	"Écologie – Une étude encourage à ne pas laisser couler l'eau pendant sa douche",
	"Ces Français qui font une croix sur leurs vacances d'été pour s'offrir une galette à la frangipane",
	"Le nouveau \"Monopoly Gaza\" ne contiendra qu'une seule rue",
	"Sondage : Environ 95% des Français sont contre les approximations ou un truc dans le genre",
	"Dry January – Un journaliste de CNews tente de tenir un mois sans parler d'islam et échoue au bout de 8 secondes",
	"14 radios encore classées numéro un des audiences en 2026",
	"Après les Trans Musicales, le RN propose de supprimer le café Arabica",
	"Après sa condamnation, Jean-Marc Morandini promu directeur d'antenne de CNews",
	"Salon de l'Agriculture – Face à l'épidémie de dermatose nodulaire, les vaches seront remplacées par des moules",
	"Déçu de ne pas avoir eu la fève dans la galette, Emmanuel Macron dissout à nouveau l'Assemblée nationale",
	"Il utilise le terme \"littéralement\" pour littéralement tout et n'importe quoi",
	"Jean-Noël Barrot débute un nouveau mois sans charisme",
	"Des agriculteurs qui tentaient de rejoindre Paris font demi-tour après avoir croisé une boucherie végane et un bar à œufs",
	"Au vu de l'actualité internationale, l'OMS déconseille vivement d'arrêter l'alcool en janvier",
	"Pour transpirer les kilos pris pendant les fêtes, il décide de regarder le spectacle de Marie s'infiltre",
	"Distrait, Bernard Arnault rachète un média qui lui appartenait déjà",
	"En burn-out, Sébastien Lecornu annonce à Donald Trump être à la tête d'un puissant cartel de drogue",
	"Les amateurs de brioche des Rois aux fruits confits seront désormais fichés S",
	"George Clooney naturalisé français après avoir réussi à placer sur une carte toutes ses résidences secondaires",
	"Donald Trump soutient qu'il fera tout pour assurer le bien-être du pétrole vénézuelien",
	"Fact-check : Y a-t-il des bons et des mauvais coups d'État ?",
	"Donald Trump bombarde le Groenland et capture un pingouin",
	"WhatsApp – Elle envoie « Happy Nouilles Year » sur son groupe de travail et perd son emploi",
	"35 ans plus tard, il parvient enfin à retrouver l'entame de son rouleau de ruban adhésif",
	"Selon une étude, la Mère Noël gagne toujours 22% de moins que son mari",
	"Les prochains colis Shein seront livrés directement dans la poubelle jaune",
	"Il ne fait pas attention à l'espace entre le marchepied et le quai et meurt dévoré par un ours",
	"Une crèche de Noël taxée de wokisme après l'introduction d'un roi mage noir",
	"Pour les fêtes, les fabricants de protoxyde d'azote sortent une bombe goût saumon fumé",
	"Il retrouve un peu de saveurs en mangeant le carton de sa Pasta Box",
}

// InitPayload is the payload sent to arena.init
type InitPayload struct {
	SessionID string `json:"session_id"`
}

// WaitingMessage is the payload from arena.*.input.waiting
type WaitingMessage struct {
	Round   int  `json:"round"`
	Waiting bool `json:"waiting"`
}

// SessionState tracks a single session's state
type SessionState struct {
	ID          string
	TitleIndex  int // Index into shuffled titles for this session
	StartedAt   time.Time
	LastEventAt time.Time
	Completed   bool
}

// generateUUID generates a random UUID v4
func generateUUID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		panic(fmt.Sprintf("crypto/rand.Read failed: %v", err))
	}
	b[6] = (b[6] & 0x0f) | 0x40 // Version 4
	b[8] = (b[8] & 0x3f) | 0x80 // Variant RFC 4122
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

func main() {
	natsURL := flag.String("nats-url", "nats://demo.nats.io:4222", "NATS server URL")
	sessions := flag.Int("sessions", 15, "Number of sessions to run in parallel")
	flag.Parse()

	// Shuffle titles
	shuffledTitles := make([]string, len(fakeNewsTitles))
	copy(shuffledTitles, fakeNewsTitles)
	mrand.Shuffle(len(shuffledTitles), func(i, j int) {
		shuffledTitles[i], shuffledTitles[j] = shuffledTitles[j], shuffledTitles[i]
	})

	// Connect to NATS
	nc, err := nats.Connect(*natsURL)
	if err != nil {
		log.Fatalf("Erreur connexion NATS: %v", err)
	}
	defer nc.Close()

	fmt.Printf("🔌 Connecté à NATS: %s\n", *natsURL)
	fmt.Printf("📰 %d fake news chargées\n", len(shuffledTitles))
	fmt.Printf("🚀 Lancement de %d sessions en parallèle\n", *sessions)
	fmt.Println()

	// Track sessions
	var mu sync.Mutex
	sessionStates := make(map[string]*SessionState)
	titleIndex := 0
	completedCount := 0

	// Subscribe to waiting signals
	_, err = nc.Subscribe("arena.*.input.waiting", func(msg *nats.Msg) {
		parts := strings.Split(msg.Subject, ".")
		if len(parts) < 4 {
			return
		}
		sessionID := parts[1]

		var waitMsg WaitingMessage
		if err := json.Unmarshal(msg.Data, &waitMsg); err != nil {
			log.Printf("❌ Erreur parsing waiting: %v", err)
			return
		}

		if !waitMsg.Waiting {
			return
		}

		mu.Lock()
		state, exists := sessionStates[sessionID]
		if !exists {
			mu.Unlock()
			return // Not our session
		}

		if titleIndex >= len(shuffledTitles) {
			mu.Unlock()
			fmt.Printf("⚠️  [%s] Plus de fake news!\n", sessionID[:8])
			return
		}

		title := shuffledTitles[titleIndex]
		titleIndex++
		state.LastEventAt = time.Now()
		mu.Unlock()

		// Send fake news
		topic := fmt.Sprintf("arena.%s.input.fakenews", sessionID)
		if err := nc.Publish(topic, []byte(title)); err != nil {
			log.Printf("❌ [%s] Erreur envoi: %v", sessionID[:8], err)
			return
		}

		fmt.Printf("📤 [%s] T%d → \"%s\"\n", sessionID[:8], waitMsg.Round, truncate(title, 50))
	})
	if err != nil {
		log.Fatalf("Erreur subscribe waiting: %v", err)
	}

	// Subscribe to end events
	_, err = nc.Subscribe("arena.*.event.end", func(msg *nats.Msg) {
		parts := strings.Split(msg.Subject, ".")
		if len(parts) < 4 {
			return
		}
		sessionID := parts[1]

		mu.Lock()
		if state, exists := sessionStates[sessionID]; exists && !state.Completed {
			state.Completed = true
			completedCount++
			duration := time.Since(state.StartedAt)
			fmt.Printf("🏁 [%s] Terminée en %s (%d/%d)\n", sessionID[:8], duration.Round(time.Second), completedCount, *sessions)
		}
		mu.Unlock()
	})
	if err != nil {
		log.Fatalf("Erreur subscribe end: %v", err)
	}

	// Subscribe to death events
	_, err = nc.Subscribe("arena.*.event.death", func(msg *nats.Msg) {
		parts := strings.Split(msg.Subject, ".")
		if len(parts) < 4 {
			return
		}
		sessionID := parts[1]

		var ev struct {
			AgentName string `json:"agent_name"`
			Round     int    `json:"round"`
		}
		if err := json.Unmarshal(msg.Data, &ev); err == nil {
			fmt.Printf("💀 [%s] %s éliminé T%d\n", sessionID[:8], ev.AgentName, ev.Round)
		}
	})
	if err != nil {
		log.Fatalf("Erreur subscribe death: %v", err)
	}

	// Subscribe to clone events
	_, err = nc.Subscribe("arena.*.event.clone", func(msg *nats.Msg) {
		parts := strings.Split(msg.Subject, ".")
		if len(parts) < 4 {
			return
		}
		sessionID := parts[1]

		var ev struct {
			ParentName string `json:"parent_name"`
			ChildName  string `json:"child_name"`
		}
		if err := json.Unmarshal(msg.Data, &ev); err == nil {
			fmt.Printf("🧬 [%s] %s → %s\n", sessionID[:8], ev.ParentName, ev.ChildName)
		}
	})
	if err != nil {
		log.Fatalf("Erreur subscribe clone: %v", err)
	}

	// Handle interrupt
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Launch sessions
	fmt.Println("🎬 Lancement des sessions...")
	for i := 0; i < *sessions; i++ {
		sessionID := generateUUID()

		mu.Lock()
		sessionStates[sessionID] = &SessionState{
			ID:        sessionID,
			StartedAt: time.Now(),
		}
		mu.Unlock()

		// Send init
		payload := InitPayload{SessionID: sessionID}
		data, _ := json.Marshal(payload)
		if err := nc.Publish("arena.init", data); err != nil {
			log.Printf("❌ Erreur init session %d: %v", i+1, err)
			continue
		}

		fmt.Printf("🚀 Session %d/%d lancée: %s\n", i+1, *sessions, sessionID[:8])

		// Small delay between launches
		time.Sleep(100 * time.Millisecond)
	}

	fmt.Println()
	fmt.Println("⏳ En attente de fin des sessions... (Ctrl+C pour arrêter)")

	// Wait for completion or interrupt
	done := make(chan struct{})
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				mu.Lock()
				if completedCount >= *sessions {
					mu.Unlock()
					close(done)
					return
				}
				mu.Unlock()
			case <-sigChan:
				close(done)
				return
			}
		}
	}()

	<-done

	// Final stats
	mu.Lock()
	fmt.Printf("\n📈 Résumé: %d/%d sessions terminées, %d fake news utilisées\n", completedCount, *sessions, titleIndex)
	mu.Unlock()
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
