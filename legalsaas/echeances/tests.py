from datetime import date
from django.test import TestCase
from .calcul_delais import calculer_echeance, expliquer_calcul


class CalculDelaisTestCase(TestCase):
    """
    ⚠️ Ces tests vérifient le COMPORTEMENT du code (report sur jour ouvrable,
    calcul en jours/années), PAS l'exactitude juridique des délais eux-mêmes.
    Les durées et références légales dans regles_delais.py restent à valider
    par un avocat en exercice avant mise en production, comme indiqué dans
    la feuille de route.
    """

    def test_appel_civil_report_jour_ferie(self):
        """30 jours civils à partir du 16 mai 2025 tombe un dimanche (15 juin) :
        doit être reporté au lundi 16 juin 2025."""
        resultat = calculer_echeance('appel_civil', date(2025, 5, 16))
        self.assertEqual(resultat, date(2025, 6, 16))

    def test_contestation_report_jour_ferie_quebec(self):
        """15 jours civils à partir du 9 juin 2026 tombe le 24 juin 2026
        (Fête nationale du Québec, jour férié) : doit être reporté au 25 juin 2026."""
        resultat = calculer_echeance('contestation', date(2026, 6, 9))
        self.assertEqual(resultat, date(2026, 6, 25))

    def test_prescription_generale_en_annees(self):
        """3 ans à partir du 1er janvier 2023 = 1er janvier 2026,
        qui est férié : reporté au 2 janvier 2026."""
        resultat = calculer_echeance('prescription_generale', date(2023, 1, 1))
        self.assertEqual(resultat, date(2026, 1, 2))

    def test_type_procedure_inconnu_leve_erreur(self):
        """Un type de procédure absent de REGLES_DELAIS doit lever une ValueError
        explicite plutôt que planter silencieusement ou renvoyer une date fausse."""
        with self.assertRaises(ValueError):
            calculer_echeance('type_inexistant', date(2025, 1, 1))

    def test_expliquer_calcul_retourne_toutes_les_donnees(self):
        """expliquer_calcul() doit retourner tout ce dont l'UI a besoin pour
        afficher le raisonnement complet (pas juste la date)."""
        resultat = expliquer_calcul('appel_civil', date(2025, 5, 16))
        self.assertEqual(resultat['date_limite'], date(2025, 6, 16))
        self.assertIn('reference_legale', resultat)
        self.assertIn('description', resultat)
        self.assertEqual(resultat['duree'], 30)
        self.assertEqual(resultat['unite'], 'jours_civils')