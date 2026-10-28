"""Cas d'usage `collecter` : collecte quotidienne idempotente, avec rattrapage des jours manqués."""

from datetime import date, timedelta

from bourse_jev.domaine.erreurs import QuotaAtteint
from bourse_jev.domaine.modeles import (
    CoursBrut,
    CoursJournalier,
    Declencheur,
    RapportExecution,
    StatutExecution,
    Titre,
)
from bourse_jev.domaine.ports import CalendrierDeMarche, Depot, Horloge, SourceDeCours
from bourse_jev.domaine.validation import valider_cours

# Assez de jours calendaires pour contenir la fenêtre de rattrapage (10 jours de bourse).
HORIZON_CALENDAIRE = timedelta(days=30)


def collecter(
    aujourd_hui: date,
    declencheur: Declencheur,
    depot: Depot,
    source: SourceDeCours,
    calendrier: CalendrierDeMarche,
    horloge: Horloge,
    fenetre_rattrapage: int = 10,
) -> list[RapportExecution]:
    """Collecte les jours de bourse sans exécution réussie, du plus ancien au plus récent.

    Relancer le même jour ne refait rien : les jours `ok` ou `sans_objet` sont sautés et un
    cours déjà stocké n'est jamais écrasé.
    """
    jours = calendrier.jours_de_bourse(aujourd_hui - HORIZON_CALENDAIRE, aujourd_hui)
    jours = jours[-fenetre_rattrapage:]
    a_traiter = []
    if jours:
        reussies = depot.dates_reussies(depuis=jours[0])
        a_traiter = [j for j in jours if j not in reussies]

    if not a_traiter:
        if aujourd_hui not in jours:
            return [_marquer_sans_objet(aujourd_hui, declencheur, depot, horloge)]
        return []

    rapports = []
    for jour in a_traiter:
        declencheur_du_jour = declencheur if jour == aujourd_hui else Declencheur.RATTRAPAGE
        rapport, quota_atteint = _collecter_un_jour(
            jour, declencheur_du_jour, depot, source, horloge
        )
        rapports.append(rapport)
        if quota_atteint:
            # Les jours suivants restent sans exécution réussie : ils seront rattrapés.
            break
    return rapports


def _marquer_sans_objet(
    jour: date, declencheur: Declencheur, depot: Depot, horloge: Horloge
) -> RapportExecution:
    execution_id = depot.debuter_execution(jour, declencheur, horloge.maintenant())
    rapport = RapportExecution(jour, StatutExecution.SANS_OBJET, 0, [], [], 0)
    depot.terminer_execution(execution_id, rapport, horloge.maintenant())
    return rapport


def _collecter_un_jour(
    jour: date,
    declencheur: Declencheur,
    depot: Depot,
    source: SourceDeCours,
    horloge: Horloge,
) -> tuple[RapportExecution, bool]:
    execution_id = depot.debuter_execution(jour, declencheur, horloge.maintenant())
    credits_avant = source.credits_consommes
    erreurs: list[str] = []
    en_retard: list[str] = []
    reussis = enregistres = 0

    titres = depot.titres_a_collecter()
    for rang, titre in enumerate(titres):
        try:
            brut = source.cours_du_jour(titre.symbole, jour)
        except QuotaAtteint:
            en_retard = [t.symbole for t in titres[rang:]]
            break
        except Exception as erreur:
            erreurs.append(f"{titre.symbole} : {erreur}")
            continue
        if brut is None:
            # Jamais de repli sur le cours de la veille : on s'abstient.
            erreurs.append(f"{titre.symbole} : cours absent pour {jour.isoformat()}")
            continue
        cours = _rattacher(titre, brut, source.nom, horloge)
        motif = valider_cours(cours, depot.cloture_precedente(cours.titre_id, avant=jour))
        if motif is not None:
            erreurs.append(f"{titre.symbole} : rejeté ({motif})")
            continue
        if depot.enregistrer_cours(cours):
            enregistres += 1
        reussis += 1  # un cours déjà présent compte comme réussi

    if not erreurs and not en_retard:
        statut = StatutExecution.OK
    elif reussis == 0:
        statut = StatutExecution.ECHEC
    else:
        statut = StatutExecution.PARTIELLE
    rapport = RapportExecution(
        date_marche=jour,
        statut=statut,
        nb_cours_enregistres=enregistres,
        erreurs=erreurs,
        titres_en_retard=en_retard,
        credits_consommes=source.credits_consommes - credits_avant,
    )
    depot.terminer_execution(execution_id, rapport, horloge.maintenant())
    return rapport, bool(en_retard)


def _rattacher(titre: Titre, brut: CoursBrut, source: str, horloge: Horloge) -> CoursJournalier:
    """Rattache un cours brut à son titre, horodaté par l'horloge (horodatage de connaissance)."""
    if titre.id is None:
        raise ValueError(f"{titre.symbole} : titre sans identifiant, non enregistré au dépôt")
    return CoursJournalier(
        titre_id=titre.id,
        jour=brut.jour,
        ouverture=brut.ouverture,
        haut=brut.haut,
        bas=brut.bas,
        cloture=brut.cloture,
        volume=brut.volume,
        source=source,
        recupere_le=horloge.maintenant(),
    )
