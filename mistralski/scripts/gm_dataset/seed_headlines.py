"""Seed headlines for GM dataset generation.

100+ hardcoded satirical titles (Gorafi FR, Onion traduits, real news)
+ RSS fetch function for dynamic enrichment.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SeedHeadline:
    """A seed headline for dataset generation."""

    text: str
    style: str  # gorafi | onion | raw
    source: str


# --- Le Gorafi style (FR satire) ---
GORAFI_HEADLINES: list[SeedHeadline] = [
    SeedHeadline("Un homme qui n'a jamais quitté son village explique la géopolitique mondiale sur Facebook", "gorafi", "Le Gorafi"),
    SeedHeadline("Le gouvernement annonce un plan de relance de la confiance en ses plans de relance", "gorafi", "Le Gorafi"),
    SeedHeadline("Selon un sondage, 87% des sondés ne croient plus aux sondages", "gorafi", "Le Gorafi"),
    SeedHeadline("Un fact-checker hospitalisé après avoir tenté de vérifier toutes les infos d'un groupe WhatsApp familial", "gorafi", "Le Gorafi"),
    SeedHeadline("La Corée du Nord remporte le prix Nobel de la paix dans un sondage nord-coréen", "gorafi", "Le Gorafi"),
    SeedHeadline("Un député découvre que la loi qu'il a votée s'applique aussi à lui", "gorafi", "Le Gorafi"),
    SeedHeadline("L'ONU publie un communiqué demandant aux pays de lire ses communiqués", "gorafi", "Le Gorafi"),
    SeedHeadline("Une IA remplace un ministre sans que personne ne remarque la différence", "gorafi", "Le Gorafi"),
    SeedHeadline("Record : un tweet politique a survécu 3 heures sans être démenti par la réalité", "gorafi", "Le Gorafi"),
    SeedHeadline("Un homme politique promet des promesses encore plus ambitieuses que ses promesses précédentes", "gorafi", "Le Gorafi"),
    SeedHeadline("Le Parlement vote une loi pour interdire de critiquer les lois votées par le Parlement", "gorafi", "Le Gorafi"),
    SeedHeadline("Facebook crée un filtre qui transforme automatiquement les fake news en poésie", "gorafi", "Le Gorafi"),
    SeedHeadline("Un expert en communication réussit à dire le contraire de ce qu'il dit en le disant", "gorafi", "Le Gorafi"),
    SeedHeadline("La démocratie a été temporairement suspendue pour des raisons démocratiques", "gorafi", "Le Gorafi"),
    SeedHeadline("Un journaliste d'investigation découvre que son propre journal appartient à un oligarque", "gorafi", "Le Gorafi"),
    SeedHeadline("Le ministère de la Vérité dément avoir créé un ministère de la Vérité", "gorafi", "Le Gorafi"),
    SeedHeadline("Un homme pris en flagrant délit de lecture d'un article en entier avant de le commenter", "gorafi", "Le Gorafi"),
    SeedHeadline("L'inflation est maîtrisée selon le gouvernement qui a changé la définition de l'inflation", "gorafi", "Le Gorafi"),
    SeedHeadline("Le PIB mondial augmente de 3% grâce aux ventes de bunkers anti-apocalypse", "gorafi", "Le Gorafi"),
    SeedHeadline("Un lanceur d'alerte alerte sur le fait que personne n'écoute les lanceurs d'alerte", "gorafi", "Le Gorafi"),
    SeedHeadline("Un réseau social lance un bouton 'Je suis indigné mais je ne ferai rien'", "gorafi", "Le Gorafi"),
    SeedHeadline("Le comité d'éthique dissous pour des raisons éthiques", "gorafi", "Le Gorafi"),
    SeedHeadline("Un lobby pétrolier sponsorise une conférence sur le réchauffement climatique pour la climatisation de la salle", "gorafi", "Le Gorafi"),
    SeedHeadline("Record d'audience pour le débat présidentiel : les téléspectateurs regardaient en espérant un bug technique", "gorafi", "Le Gorafi"),
    SeedHeadline("L'OTAN lance une opération de maintien de la paix sur Twitter", "gorafi", "Le Gorafi"),
    SeedHeadline("Un algorithme de recommandation radicalise accidentellement un modérateur de contenu", "gorafi", "Le Gorafi"),
    SeedHeadline("Le FMI recommande l'austérité aux pays qu'il a ruinés avec ses précédentes recommandations d'austérité", "gorafi", "Le Gorafi"),
    SeedHeadline("Un pays crée un ministère de la Simplification Administrative doté de 47 sous-directions", "gorafi", "Le Gorafi"),
    SeedHeadline("Les services secrets publient accidentellement leur rapport annuel sur la transparence", "gorafi", "Le Gorafi"),
    SeedHeadline("Le président assure que la crise est derrière nous tout en se dirigeant vers la sortie de secours", "gorafi", "Le Gorafi"),
    SeedHeadline("La banque centrale imprime de l'argent pour financer une étude sur l'impression excessive d'argent", "gorafi", "Le Gorafi"),
    SeedHeadline("Un influenceur géopolitique confond le Kosovo et le Costco", "gorafi", "Le Gorafi"),
    SeedHeadline("Le Sénat rejette une loi anti-corruption car elle aurait touché trop de sénateurs", "gorafi", "Le Gorafi"),
    SeedHeadline("Un dictateur remporte une élection avec 147% des voix et qualifie le résultat de 'timide'", "gorafi", "Le Gorafi"),
    SeedHeadline("La CIA déclassifie des documents prouvant qu'elle avait classifié les documents par erreur", "gorafi", "Le Gorafi"),
    SeedHeadline("Un pays impose des sanctions à un autre pays qui lui impose des sanctions pour avoir imposé des sanctions", "gorafi", "Le Gorafi"),
    SeedHeadline("Le ministre de l'Éducation avoue ne pas avoir lu la réforme de l'éducation qu'il défend", "gorafi", "Le Gorafi"),
    SeedHeadline("Un deepfake du président plus convaincant que le vrai président", "gorafi", "Le Gorafi"),
    SeedHeadline("L'algorithme de YouTube radicalise accidentellement le directeur de la modération", "gorafi", "Le Gorafi"),
    SeedHeadline("Un pays déclare la guerre à la désinformation puis bombarde ses propres fact-checkers", "gorafi", "Le Gorafi"),
]

# --- The Onion style (traduits FR) ---
ONION_HEADLINES: list[SeedHeadline] = [
    SeedHeadline("Nation la plus puissante du monde incapable de compter ses propres bulletins de vote", "onion", "The Onion FR"),
    SeedHeadline("Un homme convaincu que les médias mentent partage un article d'un blog anonyme comme preuve", "onion", "The Onion FR"),
    SeedHeadline("Rapport : 90% des théories du complot se vérifient si on change la définition de 'vérifier'", "onion", "The Onion FR"),
    SeedHeadline("Un gouvernement annonce des sanctions économiques contre lui-même par erreur", "onion", "The Onion FR"),
    SeedHeadline("Étude : crier plus fort sur internet ne change toujours pas les opinions", "onion", "The Onion FR"),
    SeedHeadline("Un pays installe la démocratie par la force et s'étonne que ça ne marche pas", "onion", "The Onion FR"),
    SeedHeadline("Les réseaux sociaux suppriment la désinformation 6 mois après qu'elle soit devenue politique officielle", "onion", "The Onion FR"),
    SeedHeadline("Un milliardaire rachète un journal pour garantir la liberté de la presse de publier ce qu'il veut", "onion", "The Onion FR"),
    SeedHeadline("Le Pentagone admet que le budget défense pourrait financer 'deux ou trois' systèmes éducatifs", "onion", "The Onion FR"),
    SeedHeadline("Zone de conflit : les deux camps affirment que Dieu est de leur côté, Dieu pas disponible pour commenter", "onion", "The Onion FR"),
    SeedHeadline("Un politicien surpris en train de dire la vérité hospitalisé en urgence", "onion", "The Onion FR"),
    SeedHeadline("L'OMS déclare que la crédulité est désormais la pandémie la plus répandue au monde", "onion", "The Onion FR"),
    SeedHeadline("Un pays change de régime politique tous les 6 mois et appelle ça de la flexibilité", "onion", "The Onion FR"),
    SeedHeadline("Wall Street applaudit la catastrophe humanitaire qui fait monter les actions", "onion", "The Onion FR"),
    SeedHeadline("Un sommet international sur le climat se termine par un buffet de homards livrés par avion cargo", "onion", "The Onion FR"),
    SeedHeadline("Un robot conversationnel remplace un service client : satisfaction en hausse de 40%", "onion", "The Onion FR"),
    SeedHeadline("Dernier pays démocratique au monde ferme pour cause de manque de participants", "onion", "The Onion FR"),
    SeedHeadline("Un cryptobro prédit pour la 47ème fois que Bitcoin va remplacer les gouvernements", "onion", "The Onion FR"),
    SeedHeadline("Breaking : l'homme qui criait au loup avait finalement raison, personne ne l'écoute", "onion", "The Onion FR"),
    SeedHeadline("Un pays lance un programme spatial pour fuir ses problèmes économiques", "onion", "The Onion FR"),
    SeedHeadline("Les experts prédisent que la prochaine crise sera causée par les experts qui prédisent les crises", "onion", "The Onion FR"),
    SeedHeadline("Un hacker de 14 ans compromet la sécurité nationale en moins de temps qu'une pause café", "onion", "The Onion FR"),
    SeedHeadline("Rapport confidentiel fuite : tout le monde le savait déjà", "onion", "The Onion FR"),
    SeedHeadline("Le marché boursier perd 500 points après qu'un président tweete un emoji ambigu", "onion", "The Onion FR"),
    SeedHeadline("Un pays en développement développe une allergie aux conseils des pays développés", "onion", "The Onion FR"),
    SeedHeadline("Un chatbot diplomatique résout une crise internationale en 3 secondes puis insulte les deux parties", "onion", "The Onion FR"),
    SeedHeadline("Un ancien espion publie ses mémoires : personne n'y croit car elles sont vraies", "onion", "The Onion FR"),
    SeedHeadline("Les Nations Unies votent à l'unanimité pour un texte que personne n'a lu", "onion", "The Onion FR"),
    SeedHeadline("Un embargo économique booste accidentellement l'économie du pays ciblé", "onion", "The Onion FR"),
    SeedHeadline("Sondage : 100% des dictateurs se considèrent démocrates", "onion", "The Onion FR"),
]

# --- Real news headlines (for source_real field) ---
REAL_NEWS_HEADLINES: list[SeedHeadline] = [
    SeedHeadline("Sommet du G7 : les dirigeants s'engagent à lutter contre la désinformation en ligne", "raw", "France Info"),
    SeedHeadline("Élections anticipées en Europe : montée des extrêmes dans plusieurs pays", "raw", "France Info"),
    SeedHeadline("Cyberattaque massive contre des infrastructures critiques en Europe de l'Est", "raw", "Reuters"),
    SeedHeadline("Le FMI revoit à la baisse les prévisions de croissance mondiale", "raw", "Reuters"),
    SeedHeadline("Tensions commerciales : nouveaux tarifs douaniers entre les États-Unis et la Chine", "raw", "Reuters"),
    SeedHeadline("L'ONU alerte sur une crise humanitaire au Sahel", "raw", "France Info"),
    SeedHeadline("Record de température mondiale pour le troisième mois consécutif", "raw", "Reuters"),
    SeedHeadline("Le Parlement européen vote une loi sur la régulation de l'intelligence artificielle", "raw", "France Info"),
    SeedHeadline("Manifestations massives contre la réforme des retraites dans plusieurs villes françaises", "raw", "France Info"),
    SeedHeadline("Scandale d'espionnage : des logiciels de surveillance vendus à des régimes autoritaires", "raw", "Reuters"),
    SeedHeadline("Crise énergétique : les prix du gaz atteignent un nouveau record en Europe", "raw", "Reuters"),
    SeedHeadline("Le Conseil de sécurité de l'ONU bloqué par un veto sur la résolution de paix", "raw", "France Info"),
    SeedHeadline("Effondrement d'une banque régionale : contagion redoutée sur les marchés", "raw", "Reuters"),
    SeedHeadline("Rapport de l'IPCC : point de non-retour climatique plus proche que prévu", "raw", "Reuters"),
    SeedHeadline("Coupure internet en Afrique : un câble sous-marin endommagé", "raw", "France Info"),
    SeedHeadline("Nouvelle vague de sanctions internationales contre la Russie", "raw", "Reuters"),
    SeedHeadline("Élection présidentielle au Sénégal : résultats contestés par l'opposition", "raw", "France Info"),
    SeedHeadline("La Fed maintient ses taux d'intérêt : les marchés réagissent", "raw", "Reuters"),
    SeedHeadline("Fuite de données massive : 200 millions de comptes compromis", "raw", "Reuters"),
    SeedHeadline("Grève générale en Argentine contre les mesures d'austérité", "raw", "France Info"),
    SeedHeadline("Le Japon déverse les eaux traitées de Fukushima : polémique internationale", "raw", "Reuters"),
    SeedHeadline("Référendum constitutionnel au Chili : le 'non' l'emporte", "raw", "France Info"),
    SeedHeadline("L'Inde devient la 5ème économie mondiale en dépassant le Royaume-Uni", "raw", "Reuters"),
    SeedHeadline("Coup d'État militaire au Niger : condamnation internationale", "raw", "France Info"),
    SeedHeadline("Les BRICS s'élargissent : six nouveaux pays invités à rejoindre le bloc", "raw", "Reuters"),
    SeedHeadline("Procès historique pour corruption d'un ancien Premier ministre", "raw", "France Info"),
    SeedHeadline("L'Australie interdit les réseaux sociaux aux moins de 16 ans", "raw", "Reuters"),
    SeedHeadline("Crise migratoire en Méditerranée : nouveau record de traversées", "raw", "France Info"),
    SeedHeadline("Un satellite espion non identifié détecté en orbite basse", "raw", "Reuters"),
    SeedHeadline("Pénurie mondiale de semi-conducteurs : impact sur l'industrie automobile", "raw", "Reuters"),
]


def get_all_seed_headlines() -> list[SeedHeadline]:
    """Return all hardcoded seed headlines."""
    return GORAFI_HEADLINES + ONION_HEADLINES + REAL_NEWS_HEADLINES


def get_headlines_by_style(style: str) -> list[SeedHeadline]:
    """Return seed headlines filtered by style."""
    return [h for h in get_all_seed_headlines() if h.style == style]


async def fetch_rss_headlines(
    url: str,
    source_name: str,
    style: str = "raw",
    max_items: int = 20,
) -> list[SeedHeadline]:
    """Fetch headlines from an RSS feed.

    Args:
        url: RSS feed URL.
        source_name: Display name for the source.
        style: Headline style tag.
        max_items: Maximum number of headlines to fetch.

    Returns:
        List of SeedHeadline from the RSS feed.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        headlines: list[SeedHeadline] = []

        # Try RSS 2.0 format
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                headlines.append(SeedHeadline(
                    text=title_el.text.strip(),
                    style=style,
                    source=source_name,
                ))
                if len(headlines) >= max_items:
                    break

        # Try Atom format if RSS found nothing
        if not headlines:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                if title_el is not None and title_el.text:
                    headlines.append(SeedHeadline(
                        text=title_el.text.strip(),
                        style=style,
                        source=source_name,
                    ))
                    if len(headlines) >= max_items:
                        break

        logger.info("rss_fetched", source=source_name, count=len(headlines))
        return headlines

    except Exception as e:
        logger.warning("rss_fetch_failed", source=source_name, error=str(e))
        return []


RSS_FEEDS: list[dict[str, str]] = [
    {"url": "https://www.legorafi.fr/feed/", "name": "Le Gorafi", "style": "gorafi"},
    {"url": "https://www.theonion.com/rss", "name": "The Onion", "style": "onion"},
    {"url": "https://www.francetvinfo.fr/titres.rss", "name": "France Info", "style": "raw"},
]


async def fetch_all_rss() -> list[SeedHeadline]:
    """Fetch headlines from all configured RSS feeds."""
    all_headlines: list[SeedHeadline] = []
    for feed in RSS_FEEDS:
        headlines = await fetch_rss_headlines(
            url=feed["url"],
            source_name=feed["name"],
            style=feed["style"],
        )
        all_headlines.extend(headlines)
    return all_headlines
