"""
⚠️ ATTENTION — À VALIDER PAR UN AVOCAT EN EXERCICE AVANT MISE EN PRODUCTION.
Ces règles sont des estimations générales du Code de procédure civile du Québec
et peuvent comporter des erreurs, exceptions non couvertes, ou être dépassées.
"""

REGLES_DELAIS = {
    'appel_civil': {
        'duree': 30,
        'unite': 'jours_civils',
        'point_depart': 'date_jugement',
        'description': "Délai d'appel en matière civile",
        'reference_legale': "Art. 360 C.p.c. (à valider)",
    },
    'contestation': {
        'duree': 15,
        'unite': 'jours_civils',
        'point_depart': 'date_signification',
        'description': "Délai de contestation (défense)",
        'reference_legale': "Art. 145 C.p.c. (à valider)",
    },
    'prescription_generale': {
        'duree': 3,
        'unite': 'annees',
        'point_depart': 'fait_generateur',
        'description': "Prescription générale",
        'reference_legale': "Art. 2925 C.c.Q. (à valider)",
    },
}