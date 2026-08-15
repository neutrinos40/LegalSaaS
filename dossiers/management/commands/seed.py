from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from clients.models import Client
from dossiers.models import Dossier
from echeances.models import Echeance, RendezVous


PRENOMS = [
    'Marc', 'Sophie', 'Éric', 'Nadia', 'Pierre', 'Julie', 'Samuel', 'Karine',
    'Claude', 'Hélène', 'Jacques', 'Marie', 'Robert', 'Danielle', 'Jean',
    'Isabelle', 'François', 'Céline', 'Michel', 'Louise', 'Denis', 'Sylvie',
    'Richard', 'Chantal', 'André', 'Nathalie', 'Yves', 'Suzanne', 'Gaétan', 'Manon',
]

NOMS = [
    'Tremblay', 'Gagnon', 'Roy', 'Côté', 'Bouchard', 'Gauthier', 'Morin', 'Lavoie',
    'Fortin', 'Gagné', 'Ouellet', 'Pelletier', 'Bélanger', 'Lévesque', 'Bergeron',
    'Leblanc', 'Paquette', 'Girard', 'Simard', 'Boucher', 'Caron', 'Beaulieu',
    'Cloutier', 'Dubois', 'Poirier', 'Fournier', 'Lapointe', 'Leclerc', 'Lefebvre',
    'Gervais', 'Poulin', 'Rousseau', 'Blais', 'Nadeau',
]

TYPES_PROCEDURE = ['contestation', 'requete_introductive', 'appel_civil']
STATUTS = ['actif', 'actif', 'actif', 'actif', 'suspendu', 'ferme']
TYPES_DELAI = [
    'Production de conclusions', 'Signification', "Dépôt de la requête",
    'Audition', 'Conférence de gestion', 'Inventaire du patrimoine',
    "Mémoire d'appel", 'Expertise', 'Déclaration de valeur', 'Mainlevée',
]
TITRES = [
    'Litige civil', 'Succession', 'Divorce', "Contestation d'avis",
    'Accident de la route', 'Litige de voisinage', 'Requête en saisie',
    'Appel - Jugement civil', "Dossier d'assurances", 'Requête en divorce',
]
OFFSETS_LIMITE = [-4, 0, 1, 2, 5, 7, 10, 14, 21, 30, 45, 90]
MODES = ['presentiel', 'visio', 'telephone']


def sans_accents(s):
    accents = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'à': 'a', 'â': 'a',
        'ç': 'c', 'î': 'i', 'ï': 'i', 'ô': 'o', 'ù': 'u', 'û': 'u',
        'É': 'e', 'È': 'e', 'À': 'a', 'Ç': 'c',
    }
    return ''.join(accents.get(c, c) for c in s)


class Command(BaseCommand):
    help = "Crée des données fictives : clients, dossiers, échéances, rendez-vous."

    def handle(self, *args, **options):
        avocat = User.objects.get(username='avocat_test2')
        aujourdhui = timezone.now().date()

        # ---------------- Partie 1 : les 8 clients de départ ----------------
        if not Client.objects.filter(prenom='Marc', nom='Tremblay').exists():
            clients = [
                {'prenom': 'Marc', 'nom': 'Tremblay', 'email': 'marc.tremblay@example.com', 'telephone': '+15145556677'},
                {'prenom': 'Sophie', 'nom': 'Gagnon', 'email': 'sophie.gagnon@example.com', 'telephone': '+15145557888'},
                {'prenom': 'Éric', 'nom': 'Bouchard', 'email': 'eric.bouchard@example.com', 'telephone': '+15145558999'},
                {'prenom': 'Nadia', 'nom': 'Roy', 'email': 'nadia.roy@example.com', 'telephone': '+15145559000'},
                {'prenom': 'Pierre', 'nom': 'Côté', 'email': 'pierre.cote@example.com', 'telephone': '+15145551011'},
                {'prenom': 'Julie', 'nom': 'Morin', 'email': 'julie.morin@example.com', 'telephone': '+15145551122'},
                {'prenom': 'Samuel', 'nom': 'Lévesque', 'email': 'samuel.levesque@example.com', 'telephone': '+15145551233'},
                {'prenom': 'Karine', 'nom': 'Bergeron', 'email': 'karine.bergeron@example.com', 'telephone': '+15145551344'},
            ]
            for d in clients:
                Client.objects.create(**d)
            self.stdout.write("8 clients de départ créés.")

            dossiers = [
                ('Marc Tremblay', 'Succession de Louise Tremblay', 'requete_introductive', 'actif', 3),
                ('Marc Tremblay', 'Litige de voisinage', 'contestation', 'actif', 1),
                ('Sophie Gagnon', 'Divorce sans enfant', 'requete_introductive', 'actif', 2),
                ('Éric Bouchard', 'Appel - Jugement civil', 'appel_civil', 'actif', 4),
                ('Nadia Roy', 'Contestation de facture', 'contestation', 'actif', 5),
                ('Nadia Roy', 'Requête en saisie', 'requete_introductive', 'suspendu', 6),
                ('Pierre Côté', 'Accident de la route', 'contestation', 'actif', 2),
                ('Julie Morin', 'Succession de Jean Morin', 'requete_introductive', 'actif', 1),
                ('Samuel Lévesque', 'Appel - Condominium', 'appel_civil', 'actif', 3),
                ('Karine Bergeron', "Contestation d'avis", 'contestation', 'actif', 4),
                ('Karine Bergeron', 'Requête en divorce', 'requete_introductive', 'ferme', 8),
                ('Julie Morin', 'Dossier des assurances', 'contestation', 'actif', 2),
            ]
            for prenom_nom, titre, type_procedure, statut, mois in dossiers:
                prenom, nom = prenom_nom.split(' ')
                client = Client.objects.get(prenom=prenom, nom=nom)
                Dossier.objects.create(
                    client=client,
                    avocat=avocat,
                    titre=titre,
                    type_procedure=type_procedure,
                    date_debut=aujourdhui - timedelta(days=mois * 30),
                    statut=statut,
                )
            self.stdout.write(f"{len(dossiers)} dossiers de départ créés.")

            echeances = [
                ('Litige de voisinage', 'Production des conclusions', -5, 'depasse'),
                ('Litige de voisinage', 'Signification', 1, 'a_venir'),
                ('Divorce sans enfant', "Dépôt de la requête", 2, 'a_venir'),
                ('Succession de Louise Tremblay', 'Inventaire du patrimoine', 4, 'a_venir'),
                ('Contestation de facture', 'Audition', 6, 'a_venir'),
                ('Accident de la route', "Constitution d'avocat", 8, 'a_venir'),
                ('Succession de Jean Morin', 'Déclaration de valeur', 10, 'a_venir'),
                ('Appel - Condominium', "Mémoire d'appel", 12, 'a_venir'),
                ("Contestation d'avis", 'Conférence de gestion', 15, 'a_venir'),
                ('Requête en saisie', 'Audition', -10, 'depasse'),
                ('Appel - Jugement civil', 'Production du mémoire', 20, 'a_venir'),
                ('Dossier des assurances', 'Expertise', 25, 'a_venir'),
                ('Requête en divorce', 'Jugement de divorce', 40, 'a_venir'),
                ('Requête en saisie', 'Mainlevée', 30, 'a_venir'),
            ]
            for titre_dossier, type_delai, offset, statut in echeances:
                dossier = Dossier.objects.get(titre=titre_dossier, avocat=avocat)
                Echeance.objects.create(
                    dossier=dossier,
                    type_delai=type_delai,
                    date_limite=aujourdhui + timedelta(days=offset),
                    statut=statut,
                )
            self.stdout.write(f"{len(echeances)} échéances de départ créées.")

            rdvs = [
                ('Marc Tremblay', 'Succession de Louise Tremblay', 1, 'presentiel', 'Cabinet'),
                ('Sophie Gagnon', 'Divorce sans enfant', 3, 'visio', 'Zoom'),
                ('Éric Bouchard', 'Appel - Jugement civil', 5, 'presentiel', 'Cabinet'),
                ('Nadia Roy', 'Contestation de facture', 7, 'telephone', 'Par téléphone'),
                ('Pierre Côté', 'Accident de la route', 9, 'presentiel', 'Cabinet'),
                ('Julie Morin', 'Succession de Jean Morin', 11, 'visio', 'Teams'),
                ('Samuel Lévesque', 'Appel - Condominium', 14, 'presentiel', 'Cabinet'),
                ('Karine Bergeron', "Contestation d'avis", 18, 'telephone', 'Par téléphone'),
                ('Marc Tremblay', 'Litige de voisinage', -3, 'presentiel', 'Cabinet'),
                ('Julie Morin', 'Dossier des assurances', -7, 'presentiel', 'Cabinet'),
            ]
            for prenom_nom, titre_dossier, offset, mode, lieu in rdvs:
                prenom, nom = prenom_nom.split(' ')
                client = Client.objects.get(prenom=prenom, nom=nom)
                dossier = Dossier.objects.get(titre=titre_dossier, avocat=avocat)
                RendezVous.objects.create(
                    client=client,
                    dossier=dossier,
                    avocat=avocat,
                    date_heure=timezone.now() + timedelta(days=offset, hours=10),
                    mode=mode,
                    lieu_ou_lien=lieu,
                    statut='complete' if offset < 0 else 'planifie',
                )
            self.stdout.write(f"{len(rdvs)} rendez-vous de départ créés.")
        else:
            self.stdout.write("Clients de départ déjà présents (partie 1 ignorée).")

        # ------------- Partie 2 : 100 clients supplémentaires -------------
        sentinelle = 'marc.tremblay1@exemple.com'
        if Client.objects.filter(email=sentinelle).exists():
            self.stdout.write("Les 100 clients supplémentaires existent déjà. Rien à faire.")
            return

        nb_clients = nb_dossiers = nb_echeances = nb_rdv = 0
        for i in range(100):
            prenom = PRENOMS[i % len(PRENOMS)]
            nom = NOMS[(i * 13) % len(NOMS)]
            email = f"{sans_accents(prenom).lower()}.{sans_accents(nom).lower()}{i + 1}@exemple.com"
            telephone = f"+1514210{i:04d}"

            client = Client.objects.create(prenom=prenom, nom=nom, email=email, telephone=telephone)
            nb_clients += 1

            dossier = Dossier.objects.create(
                client=client,
                avocat=avocat,
                titre=f"{TITRES[i % len(TITRES)]} - {prenom} {nom}",
                type_procedure=TYPES_PROCEDURE[i % 3],
                date_debut=aujourdhui - timedelta(days=(i * 13) % 240),
                statut=STATUTS[i % len(STATUTS)],
            )
            nb_dossiers += 1

            offset = OFFSETS_LIMITE[i % len(OFFSETS_LIMITE)]
            Echeance.objects.create(
                dossier=dossier,
                type_delai=TYPES_DELAI[i % len(TYPES_DELAI)],
                date_limite=aujourdhui + timedelta(days=offset),
                statut='depasse' if offset < 0 else 'a_venir',
            )
            nb_echeances += 1

            RendezVous.objects.create(
                client=client,
                dossier=dossier,
                avocat=avocat,
                date_heure=timezone.now() + timedelta(days=(i % 21), hours=10),
                mode=MODES[i % 3],
                lieu_ou_lien='Cabinet',
                statut='planifie',
            )
            nb_rdv += 1

        self.stdout.write(self.style.SUCCESS(
            f"Partie 2 : {nb_clients} clients, {nb_dossiers} dossiers, "
            f"{nb_echeances} échéances, {nb_rdv} rendez-vous créés."
        ))
