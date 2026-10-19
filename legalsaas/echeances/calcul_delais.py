from datetime import timedelta
from dateutil.relativedelta import relativedelta
from .regles_delais import REGLES_DELAIS
from .jours_feries import JOURS_FERIES_QC


def ajouter_jours_ouvrables(date_depart, nb_jours):
    date_courante = date_depart
    jours_ajoutes = 0
    while jours_ajoutes < nb_jours:
        date_courante += timedelta(days=1)
        if date_courante.weekday() < 5 and date_courante not in JOURS_FERIES_QC:
            jours_ajoutes += 1
    return date_courante


def calculer_echeance(type_procedure, date_depart):
    if type_procedure not in REGLES_DELAIS:
        raise ValueError(f"Type de procédure inconnu : {type_procedure}")

    regle = REGLES_DELAIS[type_procedure]
    unite = regle['unite']
    duree = regle['duree']

    if unite == 'jours_civils':
        date_limite = date_depart + timedelta(days=duree)
    elif unite == 'jours_ouvrables':
        date_limite = ajouter_jours_ouvrables(date_depart, duree)
    elif unite == 'annees':
        date_limite = date_depart + relativedelta(years=duree)
    else:
        raise ValueError(f"Unité inconnue : {unite}")

    # Si la date limite tombe un jour non juridique, reporter au jour ouvrable suivant
    while date_limite.weekday() >= 5 or date_limite in JOURS_FERIES_QC:
        date_limite += timedelta(days=1)

    return date_limite


def expliquer_calcul(type_procedure, date_depart):
    regle = REGLES_DELAIS[type_procedure]
    date_limite = calculer_echeance(type_procedure, date_depart)
    return {
        'date_limite': date_limite,
        'description': regle['description'],
        'reference_legale': regle['reference_legale'],
        'duree': regle['duree'],
        'unite': regle['unite'],
        'point_depart': date_depart,
    }