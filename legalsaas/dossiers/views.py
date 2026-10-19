from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.db.models import Q
from django.http import HttpResponse
from cabinet.models import Cabinet
from clients.models import Client

from .forms import CommunicationForm, DossierForm, DossierCreationForm
from .models import Dossier, ProfilAvocat, Communication
from echeances.forms import EcheanceForm, RendezVousForm, TacheForm
from echeances.models import Echeance, RendezVous
from echeances.calcul_delais import expliquer_calcul
from documents.models import Document
from documents.forms import DocumentForm, DocumentEditForm
from facturation.forms import EntreeTempsForm, EntreeTempsEditForm, PaiementForm
from facturation.services import (
    demarrer_chrono as demarrer_chrono_service,
    arreter_chrono as arreter_chrono_service,
    mettre_en_pause_chrono as mettre_en_pause_chrono_service,
    reprendre_chrono as reprendre_chrono_service,
    total_secondes_dossier,
    formater_secondes,
)
from facturation.models import TempsTravail, EntreeTemps, Paiement

ONGLETS_DOSSIER = ['apercu', 'documents', 'chronologie', 'communications',
                   'rendez-vous', 'echeances', 'facturation']


def url_onglet(dossier_id, onglet, source=''):
    url = reverse('fiche_dossier', kwargs={'dossier_id': dossier_id}) + f'?onglet={onglet}'
    if source:
        url += f'&source={source}'
    return url


def taux_horaire_effectif(dossier, profil):
    return dossier.taux_horaire or profil.taux_horaire_defaut or 0


def niveau_urgence(echeance, seuil_rouge=2, seuil_orange=7):
    jours_restants = (echeance.date_limite - timezone.now().date()).days
    if echeance.statut == 'depasse' or jours_restants <= seuil_rouge:
        return 'rouge'
    if jours_restants <= seuil_orange:
        return 'orange'
    return 'vert'


def get_profil(user):
    profil, _ = ProfilAvocat.objects.get_or_create(user=user)
    return profil


def inscription(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        erreur = None

        if not username or not email or not password1:
            erreur = _("Tous les champs sont obligatoires.")
        elif User.objects.filter(username=username).exists():
            erreur = _("Ce nom d'utilisateur est déjà pris.")
        elif password1 != password2:
            erreur = _("Les mots de passe ne correspondent pas.")
        elif len(password1) < 8:
            erreur = _("Le mot de passe doit contenir au moins 8 caractères.")

        if erreur:
            return render(request, 'inscription.html', {'erreur': erreur})

        user = User.objects.create_user(username=username, email=email, password=password1)
        get_profil(user)
        user = authenticate(request, username=username, password=password1)
        if user:
            login(request, user)
        messages.success(request, _("Bienvenue ! Votre compte a été créé."))
        return redirect('dashboard')

    return render(request, 'inscription.html')


def _dossiers_accesibles(user):
    """Dossiers visibles : les siens + ceux partagés avec lui."""
    from cabinet.models import Partage
    return Dossier.objects.filter(
        Q(avocat=user) | Q(partages__partage_avec=user, partages__statut='accepte')
    ).distinct()


def _dossier_accessible(dossier, user):
    if dossier.avocat == user:
        return True
    from cabinet.models import Partage
    return Partage.objects.filter(
        type_objet='dossier', dossier=dossier,
        partage_avec=user, statut='accepte'
    ).exists()


@login_required
def dashboard(request):
    profil = get_profil(request.user)

    actif = request.GET.get('actif', 'echeances')
    if actif not in ('dossiers', 'echeances', 'rdv', 'calendrier', 'revenus'):
     actif = 'echeances'

    dossiers = _dossiers_accesibles(request.user).order_by('-date_debut')
    pag_dossiers = Paginator(dossiers, 10 if actif == 'dossiers' else 5)
    dossiers = pag_dossiers.get_page(request.GET.get('page_dossiers', 1))

    echeances = Echeance.objects.filter(
        dossier__in=_dossiers_accesibles(request.user),
        statut__in=['a_venir', 'depasse'],
    ).order_by('date_limite')
    pag_echeances = Paginator(echeances, 10 if actif == 'echeances' else 5)
    echeances_page = pag_echeances.get_page(request.GET.get('page_echeances', 1))

    echeances_affichees = []
    for echeance in echeances_page:
        jours_restants = (echeance.date_limite - timezone.now().date()).days
        echeances_affichees.append((
            echeance,
            niveau_urgence(echeance, profil.seuil_rouge, profil.seuil_orange),
            jours_restants,
        ))

    rendez_vous = RendezVous.objects.filter(
        dossier__in=_dossiers_accesibles(request.user),
        date_heure__gte=timezone.now(),
        statut='planifie'
    ).order_by('date_heure')
    pag_rdv = Paginator(rendez_vous, 10 if actif == 'rdv' else 5)
    rendez_vous = pag_rdv.get_page(request.GET.get('page_rdv', 1))

    documents_recents = (Document.objects.select_related('dossier')
                         .filter(
                             Q(dossier__avocat=request.user) | Q(auteur=request.user)
                             | Q(dossier__partages__partage_avec=request.user, dossier__partages__statut='accepte')
                         )
                         .distinct()
                         .order_by('-date_upload')[:5])

    # --- KPI ---
    from clients.models import Client
    from facturation.models import Facture

    nb_clients = Client.objects.filter(
        Q(avocat=request.user) | Q(partages__partage_avec=request.user, partages__statut='accepte')
    ).distinct().count()
    nb_dossiers = _dossiers_accesibles(request.user).count()
    nb_echeances = Echeance.objects.filter(
        dossier__in=_dossiers_accesibles(request.user), statut__in=['a_venir', 'depasse']).count()
    nb_rdv = RendezVous.objects.filter(
        dossier__in=_dossiers_accesibles(request.user), date_heure__gte=timezone.now(),
        statut='planifie').count()
    mois_courant = timezone.now().strftime('%Y-%m')
    factures_mois = Facture.objects.filter(avocat=request.user, mois=mois_courant)
    revenus_mois = sum(float(f.montant) for f in factures_mois)

    factures_avocat = Facture.objects.filter(avocat=request.user)
    factures_payees = factures_avocat.filter(statut='payee')
    factures_impayees = factures_avocat.filter(statut='envoyee')
    factures_brouillon = factures_avocat.filter(statut='brouillon')
    nb_payees = factures_payees.count()
    total_payees = sum(float(f.montant) for f in factures_payees)
    nb_impayees = factures_impayees.count()
    total_impayees = sum(float(f.montant) for f in factures_impayees)
    nb_brouillons = factures_brouillon.count()
    total_brouillons = sum(float(f.montant) for f in factures_brouillon)

    from collections import defaultdict
    rev_par_mois = defaultdict(lambda: {'payee': 0.0, 'envoyee': 0.0, 'brouillon': 0.0})
    for f in factures_avocat:
        rev_par_mois[f.mois][f.statut] += float(f.montant)
    derniers_mois = sorted(rev_par_mois.keys())[-6:]
    rev_labels = derniers_mois
    rev_payees = [rev_par_mois[m]['payee'] for m in derniers_mois]
    rev_impayees = [rev_par_mois[m]['envoyee'] for m in derniers_mois]
    rev_brouillons = [rev_par_mois[m]['brouillon'] for m in derniers_mois]

    from calendar import monthrange
    aujourd_hui = timezone.now().date()
    mois_labels = []
    mois_counts = []
    dossiers_acces = _dossiers_accesibles(request.user)
    for i in range(6):
        annee = aujourd_hui.year + (aujourd_hui.month + i - 1) // 12
        mois = (aujourd_hui.month + i - 1) % 12 + 1
        debut = date(annee, mois, 1)
        fin = date(annee, mois, monthrange(annee, mois)[1])
        count = Echeance.objects.filter(
            dossier__in=dossiers_acces,
            date_limite__gte=debut, date_limite__lte=fin,
        ).count()
        mois_labels.append(date(annee, mois, 1).strftime('%m/%Y'))
        mois_counts.append(count)

    statut_labels = []
    statut_data = []
    for code, label in Dossier.STATUT_CHOICES:
        count = dossiers_acces.filter(statut=code).count()
        if count:
            statut_labels.append(label)
            statut_data.append(count)

    context = {
        'dossiers': dossiers,
        'echeances': echeances_affichees,
        'echeances_page': echeances_page,
        'rendez_vous': rendez_vous,
        'documents_recents': documents_recents,
        'actif': actif,
        'nb_clients': nb_clients,
        'nb_dossiers': nb_dossiers,
        'nb_echeances': nb_echeances,
        'nb_rdv': nb_rdv,
        'revenus_mois': revenus_mois,
        'nb_impayees': nb_impayees,
        'nb_payees': nb_payees,
        'total_payees': total_payees,
        'total_impayees': total_impayees,
        'nb_brouillons': nb_brouillons,
        'total_brouillons': total_brouillons,
        'rev_labels': rev_labels,
        'rev_payees': rev_payees,
        'rev_impayees': rev_impayees,
        'rev_brouillons': rev_brouillons,
        'factures_payees': factures_payees.order_by('-mois'),
        'factures_impayees': factures_impayees.order_by('-mois'),
        'factures_brouillon': factures_brouillon.order_by('-mois'),
        'mois_labels': mois_labels,
        'mois_counts': mois_counts,
        'statut_labels': statut_labels,
        'statut_data': statut_data,
        'clients_calendrier': Client.objects.filter(
            Q(avocat=request.user)
            | Q(partages__partage_avec=request.user, partages__statut='accepte')
            | Q(dossiers__in=_dossiers_accesibles(request.user))
        ).distinct().order_by('nom', 'prenom'),
        'dossiers_calendrier': _dossiers_accesibles(request.user).order_by('titre'),
    }
    return render(request, 'dashboard.html', context)


def prochaine_echeance(dossier):
    return dossier.echeances.filter(statut__in=['a_venir', 'depasse']).order_by('date_limite').first()


@login_required
def ajouter_dossier(request):
    profil = get_profil(request.user)
    if request.method == 'POST':
        form = DossierForm(request.POST, user=request.user)
        if form.is_valid():
            dossier = form.save(commit=False)
            dossier.avocat = request.user
            dossier.cabinet = profil.cabinet
            dossier.save()
            messages.success(request, _("Dossier créé avec succès."))
            return redirect('fiche_dossier', dossier_id=dossier.id)
    else:
        form = DossierForm(user=request.user, initial={
            'statut': 'actif', 'date_debut': timezone.localdate()})
    return render(request, 'dossiers_ajouter.html', {
        'form': form,
        'profil': profil,
    })


@login_required
def liste_dossiers(request):
    profil = get_profil(request.user)
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '')
    type_procedure = request.GET.get('type_procedure', '')

    # Auto-stop chrono if requested from global stop button
    if request.GET.get('chrono_stop'):
        sec = request.GET.get('sec')
        try:
            acc = int(sec) if sec else 0
        except ValueError:
            acc = 0
        session = TempsTravail.objects.filter(avocat=request.user, fin__isnull=True).first()
        if session:
            session.fin = timezone.now()
            session.save()
            minutes = max(int(acc or session.duree_secondes // 60), 1)
            profil_cur = get_profil(request.user)
            taux = taux_horaire_effectif(session.dossier, profil_cur)
            entree = EntreeTemps.objects.create(
                dossier=session.dossier,
                avocat=request.user,
                date=timezone.localdate(),
                duree_minutes=minutes,
                taux_horaire_applique=taux,
                saisie_manuelle=False,
            )
            messages.success(request, _("Chrono arrêté — entrée de temps enregistrée ({}).").format(entree.duree_formatee))
        else:
            messages.info(request, _("Aucun chrono en cours."))
        return redirect('liste_dossiers')

    dossiers = _dossiers_accesibles(request.user).select_related('client')

    if statut:
        dossiers = dossiers.filter(statut=statut)
    if type_procedure:
        dossiers = dossiers.filter(type_procedure=type_procedure)
    if q:
        dossiers = dossiers.filter(
            Q(client__nom__icontains=q) | Q(client__prenom__icontains=q)
            | Q(client__raison_sociale__icontains=q)
            | Q(client__nom_representant__icontains=q) | Q(titre__icontains=q)
        )

    ordre_statut = {'actif': 0, 'suspendu': 1, 'ferme': 2}
    dossiers = sorted(dossiers, key=lambda d: (ordre_statut.get(d.statut, 3), -d.date_debut.toordinal()))

    resultats = []
    for dossier in dossiers:
        echeance = prochaine_echeance(dossier)
        urgence = niveau_urgence(echeance, profil.seuil_rouge, profil.seuil_orange) if echeance else None
        jours = (echeance.date_limite - timezone.now().date()).days if echeance else None
        resultats.append((dossier, echeance, urgence, jours))

    context = {
        'resultats': resultats,
        'q': q,
        'statut': statut,
        'type_procedure': type_procedure,
    }
    return render(request, 'dossiers_liste.html', context)


@login_required
def fiche_dossier(request, dossier_id):
    profil = get_profil(request.user)
    dossier = get_object_or_404(
        Dossier.objects.select_related('client'),
        id=dossier_id,
    )
    if not _dossier_accessible(dossier, request.user):
        messages.error(request, _("Vous n'avez pas accès à ce dossier."))
        return redirect('liste_dossiers')

    onglet = request.GET.get('onglet', 'apercu')
    if onglet not in ONGLETS_DOSSIER:
        onglet = 'apercu'

    source = request.GET.get('source', '')
    if source != 'clients':
        source = ''

    session_chrono = TempsTravail.objects.filter(
        dossier=dossier, avocat=request.user, fin__isnull=True).first()
    # Check for a paused session (has fin but we can detect by last stopped one)
    session_pause = TempsTravail.objects.filter(
        dossier=dossier, avocat=request.user, fin__isnull=False
    ).order_by('-fin').first()
    session_active = TempsTravail.objects.filter(
        dossier=dossier, avocat=request.user, fin__isnull=True).first()
    session_chrono = session_active or None
    derniere_pause = session_pause if session_pause and session_pause.fin else None
    # determine if paused
    en_pause = (session_active is None and session_pause is not None)
    if en_pause:
        # compute total seconds including last pause
        total_secondes = total_secondes_dossier(dossier)
        echeances = []
    else:
        echeances = []
    for echeance in dossier.echeances.all().order_by('date_limite'):
        jours_restants = (echeance.date_limite - timezone.now().date()).days
        echeances.append((
            echeance,
            niveau_urgence(echeance, profil.seuil_rouge, profil.seuil_orange),
            jours_restants,
        ))

    documents = Document.objects.filter(
        Q(dossier=dossier) | Q(dossier__client=dossier.client,
                               dossier__partages__partage_avec=request.user,
                               dossier__partages__statut='accepte')
    ).distinct().order_by('-date_upload')
    rendez_vous = dossier.rendez_vous.all().order_by('-date_heure')
    communications = dossier.communications.all().order_by('-date')
    entrees_temps = dossier.entrees_temps.all().order_by('-date', '-cree_le')

    total_secondes = total_secondes_dossier(dossier)
    entrees_facturables = entrees_temps.filter(non_facturable=False)
    total_montant = sum((e.montant for e in entrees_facturables), Decimal('0'))
    total_minutes = sum(e.duree_minutes for e in entrees_facturables)
    taux = taux_horaire_effectif(dossier, profil)

    paiements = dossier.paiements.all().order_by('-date', '-cree_le')
    total_paye = sum((p.montant for p in paiements), Decimal('0'))
    balance = (total_paye - total_montant).quantize(Decimal('0.01'))
    if total_minutes:
        taux_moyen = (total_montant / (Decimal(total_minutes) / Decimal(60))).quantize(Decimal('0.01'))
    else:
        taux_moyen = Decimal('0.00')

    fusa = timezone.get_current_timezone()
    chronologie = []
    for echeance, _u, _j in echeances:
        chronologie.append({
            'date': timezone.make_aware(datetime.combine(echeance.date_limite, time.min), fusa),
            'type': 'echeance', 'objet': echeance,
        })
    for rdv in rendez_vous:
        chronologie.append({'date': rdv.date_heure, 'type': 'rdv', 'objet': rdv})
    for comm in communications:
        chronologie.append({'date': comm.date, 'type': 'communication', 'objet': comm})
    for entree in entrees_temps:
        chronologie.append({
            'date': timezone.make_aware(datetime.combine(entree.date, time.min), fusa),
            'type': 'temps', 'objet': entree,
        })
    for doc in documents:
        chronologie.append({'date': doc.date_upload, 'type': 'document', 'objet': doc})
    chronologie.sort(key=lambda x: x['date'], reverse=True)

    minutes_ecoulees = 0
    if session_chrono is not None:
        minutes_ecoulees = max(session_chrono.duree_secondes // 60, 1)

    est_proprietaire = (dossier.avocat == request.user)
    from cabinet.models import Partage, Cabinet
    partages_dossier = Partage.objects.filter(
        type_objet='dossier', dossier=dossier
    ).select_related('partage_avec', 'partage_par')

    from django.contrib.auth.models import User as UserModel
    if profil.cabinet:
        membres_cabinet = UserModel.objects.filter(
            profil__cabinet=profil.cabinet
        ).exclude(id=request.user.id)
    else:
        membres_cabinet = UserModel.objects.none()

    context = {
        'dossier': dossier,
        'onglet': onglet,
        'onglets': ONGLETS_DOSSIER,
        'session_chrono': session_chrono,
        'documents': documents,
        'rendez_vous': rendez_vous,
        'echeances': echeances,
        'communications': communications,
        'entrees_temps': entrees_temps,
        'total_secondes': total_secondes,
        'total_temps': formater_secondes(total_secondes),
        'total_montant': total_montant,
        'total_minutes': total_minutes,
        'paiements': paiements,
        'total_paye': total_paye,
        'balance': balance,
        'taux_moyen': taux_moyen,
        'taux': taux,
        'chronologie': chronologie,
        'entree_temps_form': EntreeTempsForm(dossier=dossier, initial={
            'date': timezone.localdate(),
            'duree_minutes': minutes_ecoulees,
            'taux_horaire_applique': taux,
        }),
        'entree_temps_ajout_form': EntreeTempsForm(dossier=dossier, initial={
            'date': timezone.localdate(),
            'taux_horaire_applique': taux,
        }),
        'echeance_form': EcheanceForm(),
        'rendez_vous_form': RendezVousForm(user=request.user, dossier=dossier),
        'tache_form': TacheForm(user=request.user, dossier=dossier),
        'communication_form': CommunicationForm(),
        'document_form': DocumentForm(
            initial={'dossier': dossier, 'client': dossier.client},
            user=request.user,
        ),
        'active': 'clients' if source == 'clients' else 'dossiers',
        'source': source,
        'est_proprietaire': est_proprietaire,
        'partages_dossier': partages_dossier,
        'membres_cabinet': membres_cabinet,
        'chrono_en_pause': en_pause,
        'derniere_pause': derniere_pause,
    }
    return render(request, 'fiche_dossier.html', context)


def demarrer_chrono(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        for actif in TempsTravail.objects.filter(
                avocat=request.user, fin__isnull=True).exclude(dossier=dossier):
            actif.fin = timezone.now()
            actif.save()
        demarrer_chrono_service(dossier, request.user)
        messages.success(request, _("Chrono démarré."))
    return redirect(url_onglet(dossier.id, 'apercu', request.GET.get('source', '')))


@login_required
def reprendre_chrono(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        for actif in TempsTravail.objects.filter(
                avocat=request.user, fin__isnull=True).exclude(dossier=dossier):
            actif.fin = timezone.now()
            actif.save()
        reprendre_chrono_service(dossier, request.user)
        messages.success(request, _("Chrono repris."))
    return redirect(url_onglet(dossier.id, 'apercu', request.GET.get('source', '')))

@login_required
def arreter_chrono(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        session = arreter_chrono_service(dossier, request.user)
        if session is not None and session.fin:
            action = request.POST.get('action') or request.GET.get('action')
            if action == 'pause':
                mettre_en_pause_chrono_service(dossier, request.user)
                messages.success(request, _("Chrono mis en pause."))
                next_url = request.POST.get('next') or url_onglet(dossier.id, 'apercu', request.GET.get('source', ''))
                return redirect(next_url)
            profil = get_profil(request.user)
            form = EntreeTempsForm(request.POST, dossier=dossier)
            if form.is_valid():
                entree = form.save(commit=False)
            else:
                minutes = max(int(session.duree_secondes // 60), 1)
                entree = EntreeTemps(
                    date=timezone.localdate(),
                    duree_minutes=minutes,
                    taux_horaire_applique=taux_horaire_effectif(dossier, profil),
                )
            entree.dossier = dossier
            entree.avocat = request.user
            entree.saisie_manuelle = False
            entree.save()
            messages.success(request, _("Chrono arrêté — entrée de temps enregistrée ({}).")
                             .format(entree.duree_formatee))
        else:
            messages.info(request, _("Aucun chrono en cours sur ce dossier."))
    return redirect(url_onglet(dossier.id, 'apercu', request.GET.get('source', '')))


@login_required
def ajouter_communication(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = CommunicationForm(request.POST)
        if form.is_valid():
            comm = form.save(commit=False)
            comm.dossier = dossier
            comm.avocat = request.user
            comm.save()
            messages.success(request, _("Communication ajoutée."))
        else:
            messages.error(request, _("Erreur dans la communication."))
    return redirect(url_onglet(dossier.id, 'communications', request.GET.get('source', '')))


@login_required
def ajouter_echeance(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = EcheanceForm(request.POST)
        if form.is_valid():
            echeance = form.save(commit=False)
            echeance.dossier = dossier

            if form.cleaned_data['mode_saisie'] == 'automatique':
                type_procedure = form.cleaned_data['type_procedure']
                date_depart = form.cleaned_data['date_depart']
                try:
                    resultat = expliquer_calcul(type_procedure, date_depart)
                except ValueError as e:
                    messages.error(request, str(e))
                    return redirect(url_onglet(dossier.id, 'echeances', request.GET.get('source', '')))

                echeance.type_delai = resultat['description']
                echeance.date_limite = resultat['date_limite']
                echeance.calcul_automatique = True
                echeance.date_depart = date_depart
                echeance.reference_legale = resultat['reference_legale']
                echeance.duree_delai = f"{resultat['duree']} {resultat['unite'].replace('_', ' ')}"

            echeance.save()
            messages.success(request, _("Échéance ajoutée."))
        else:
            messages.error(request, _("Erreur dans l'échéance."))
    return redirect(url_onglet(dossier.id, 'echeances', request.GET.get('source', '')))


@login_required
def ajouter_entree_temps(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = EntreeTempsForm(request.POST, dossier=dossier)
        if form.is_valid():
            entree = form.save(commit=False)
            entree.dossier = dossier
            entree.avocat = request.user
            entree.saisie_manuelle = True
            entree.save()
            messages.success(request, _("Entrée de temps enregistrée."))
        else:
            messages.error(request, _("Erreur dans l'entrée de temps."))
    return redirect(url_onglet(dossier.id, 'facturation', request.GET.get('source', '')))


@login_required
def ajouter_paiement(request, dossier_id):
    dossier = get_object_or_404(Dossier.objects.select_related('client'), id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    profil = get_profil(request.user)
    retour = url_onglet(dossier.id, 'facturation', request.GET.get('source', ''))
    if request.method == 'POST':
        form = PaiementForm(request.POST)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.dossier = dossier
            paiement.client = dossier.client
            paiement.avocat = request.user
            paiement.cabinet = profil.cabinet
            paiement.save()
            messages.success(request, _("Paiement enregistré et crédité au compte du dossier."))
            return redirect(retour)
        messages.error(request, _("Erreur dans le paiement."))
    else:
        total_montant = sum((e.montant for e in dossier.entrees_temps.filter(non_facturable=False)),
                            Decimal('0'))
        total_paye = sum((p.montant for p in dossier.paiements.all()), Decimal('0'))
        solde = (total_montant - total_paye)
        initial = {'date': timezone.localdate()}
        if total_paye == 0 and total_montant > 0:
            initial['montant'] = total_montant
        form = PaiementForm(initial=initial)
    return render(request, 'element_modifier.html', {
        'titre': _("Enregistrer un paiement / une avance"),
        'form': form,
        'retour': retour,
        'dossier': dossier,
    })


@login_required
def supprimer_paiement(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)
    dossier = paiement.dossier
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        paiement.delete()
        messages.success(request, _("Paiement supprimé."))
    return redirect(url_onglet(dossier.id, 'facturation', request.GET.get('source', '')))


@login_required
def ajouter_document(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.dossier = dossier
            doc.client = dossier.client
            doc.auteur = request.user
            doc.nom_original = doc.fichier.name
            doc.taille_octets = doc.fichier.size
            doc.type_fichier = doc.fichier.name.lower().rsplit('.', 1)[-1]
            doc.save()
            messages.success(request, _("Document ajouté au dossier."))
        else:
            messages.error(request, _("Erreur dans le document."))
    return redirect(url_onglet(dossier.id, 'documents', request.GET.get('source', '')))


@login_required
def exporter_etat_compte(request, dossier_id):
    dossier = get_object_or_404(
        Dossier.objects.select_related('client'),
        id=dossier_id,
    )
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    entrees = dossier.entrees_temps.all().order_by('date', 'cree_le')

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle)
    import reportlab

    dossier_fonts = Path(reportlab.__file__).parent / 'fonts'
    pdfmetrics.registerFont(TTFont('Vera', str(dossier_fonts / 'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('VeraBd', str(dossier_fonts / 'VeraBd.ttf')))
    pdfmetrics.registerFontFamily('Vera', normal='Vera', bold='VeraBd',
                                  italic='Vera', boldItalic='VeraBd')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="etat_compte_dossier_{dossier.id}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)

    titres = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=titres['Title'], fontName='VeraBd', fontSize=18, leading=22)
    h2 = ParagraphStyle('h2', parent=titres['Heading2'], fontName='VeraBd', fontSize=12, leading=15)
    corps = ParagraphStyle('corps', parent=titres['BodyText'], fontName='Vera', fontSize=9.5, leading=13)

    client = dossier.client
    entrees_facturables = entrees.filter(non_facturable=False)
    total_montant = sum((e.montant for e in entrees_facturables), Decimal('0'))
    total_minutes = sum(e.duree_minutes for e in entrees_facturables)
    heures = total_minutes // 60
    minutes = total_minutes % 60

    history = []
    history.append(Paragraph(_("État de compte"), h1))
    history.append(Paragraph(f"{request.user.get_full_name() or request.user.username} — Cabinet", corps))
    history.append(Paragraph(timezone.now().strftime('%d/%m/%Y %H:%M'), corps))
    history.append(Spacer(1, 0.6 * cm))

    history.append(Paragraph(_("Dossier"), h2))
    history.append(Paragraph(
        f"<b>{dossier.titre}</b> — {dossier.get_type_procedure_display()} — "
        f"<b>{dossier.get_statut_display()}</b> — {dossier.date_debut.strftime('%d/%m/%Y')}", corps))
    history.append(Paragraph(
        f"Taux horaire : {taux_horaire_effectif(dossier, get_profil(request.user))} $/h", corps))
    history.append(Spacer(1, 0.4 * cm))

    history.append(Paragraph(_("Client"), h2))
    history.append(Paragraph(f"<b>{client.nom_complet}</b>", corps))
    if client.adresse:
        history.append(Paragraph(client.adresse, corps))
    if client.email:
        history.append(Paragraph(client.email, corps))
    if client.telephone:
        history.append(Paragraph(client.telephone, corps))
    history.append(Spacer(1, 0.6 * cm))

    data = [[Paragraph(_("Date"), corps), Paragraph(_("Description"), corps),
             Paragraph(_("Catégorie"), corps), Paragraph(_("Durée"), corps),
             Paragraph(_("Taux ($/h)"), corps), Paragraph(_("Montant ($)"), corps)]]
    for e in entrees:
        etiquette = _("Non facturable") if e.non_facturable else e.get_categorie_activite_display()
        data.append([
            Paragraph(e.date.strftime('%d/%m/%Y'), corps),
            Paragraph(e.description or '—', corps),
            Paragraph(etiquette, corps),
            Paragraph(e.duree_formatee, corps),
            Paragraph(str(e.taux_horaire_applique), corps),
            Paragraph(f"{e.montant} $", corps),
        ])
    data.append([
        Paragraph(_("TOTAL"), ParagraphStyle('tot', parent=corps, fontName='VeraBd')),
        '', '', Paragraph(f"{heures}h {minutes:02d}min", corps),
        '', Paragraph(f"{total_montant} $", ParagraphStyle('tot2', parent=corps, fontName='VeraBd')),
    ])

    table = Table(data, colWidths=[2.2 * cm, 6.4 * cm, 2.8 * cm, 2.2 * cm, 2.2 * cm, 2.4 * cm])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -2), 0.4, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0069D0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'VeraBd'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F3F6FB')),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, colors.HexColor('#0069D0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    history.append(table)

    doc.build(history)
    return response


@login_required
def reglages(request):
    profil = get_profil(request.user)
    message = None
    message_ok = False
    cabinets = Cabinet.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action', 'seuils')

        if action == 'cabinet':
            cabinet_id = request.POST.get('cabinet_id', '')
            if cabinet_id:
                try:
                    cab = Cabinet.objects.get(id=cabinet_id)
                    profil.cabinet = cab
                    profil.save()
                    message = _("Cabinet « %(nom)s » enregistré.") % {'nom': cab.nom}
                    message_ok = True
                except Cabinet.DoesNotExist:
                    message = _("Cabinet introuvable.")
            else:
                profil.cabinet = None
                profil.save()
                message = _("Aucun cabinet sélectionné.")
                message_ok = True
        else:
            try:
                seuil_rouge = int(request.POST.get('seuil_rouge', profil.seuil_rouge))
                seuil_orange = int(request.POST.get('seuil_orange', profil.seuil_orange))
                if 0 < seuil_rouge < seuil_orange:
                    profil.seuil_rouge = seuil_rouge
                    profil.seuil_orange = seuil_orange
                    profil.save()
                    message = _("Réglages enregistrés.")
                    message_ok = True
                else:
                    message = _("Erreur : le seuil rouge doit être inférieur au seuil orange.")
            except ValueError:
                message = _("Erreur : valeurs numériques attendues.")

    context = {'profil': profil, 'cabinets': cabinets, 'message': message, 'message_ok': message_ok}
    return render(request, 'reglages.html', context)


@login_required
def ajouter_dossier(request):
    profil = get_profil(request.user)
    if request.method == 'POST':
        form = DossierCreationForm(request.POST, user=request.user)
        if form.is_valid():
            cd = form.cleaned_data
            client = cd.get('client_existant')
            if client is None:
                nom = cd['nom_complet'].strip()
                if cd['type_client'] == 'compagnie':
                    client = Client(raison_sociale=nom, type_client='compagnie')
                else:
                    client = Client(nom=nom, type_client='individu')
                client.email = cd.get('email') or None
                client.telephone = cd.get('telephone') or None
                client.avocat = request.user
                client.cabinet = profil.cabinet if profil else None
                client.save()
            titre = (cd.get('titre') or '').strip()
            if not titre:
                libelle = dict(Dossier.TYPE_PROCEDURE_CHOICES).get(cd['type_procedure'])
                titre = f"{libelle} – {client.nom_complet}"
            dossier = Dossier.objects.create(
                client=client,
                avocat=request.user,
                cabinet=profil.cabinet if profil else None,
                titre=titre,
                type_procedure=cd['type_procedure'],
                date_debut=cd['date_debut'],
                statut=cd['statut'],
                notes=cd.get('notes') or None,
            )
            if cd.get('echeance_date'):
                Echeance.objects.create(
                    dossier=dossier,
                    type_delai=cd['echeance_type'],
                    date_limite=cd['echeance_date'],
                    statut='a_venir',
                )
            messages.success(request, _("Dossier créé avec succès."))
            return redirect('fiche_dossier', dossier_id=dossier.id)
    else:
        form = DossierCreationForm(user=request.user)
    return render(request, 'dossiers_ajouter.html', {
        'form': form,
        'profil': profil,
    })


@login_required
def modifier_dossier(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = DossierForm(request.POST, instance=dossier, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Dossier modifié."))
            return redirect(url_onglet(dossier.id, 'apercu', request.GET.get('source', '')))
    else:
        form = DossierForm(instance=dossier, user=request.user)
    return render(request, 'element_modifier.html', {
        'form': form,
        'titre': _("Modifier le dossier"),
        'retour': url_onglet(dossier.id, 'apercu', request.GET.get('source', '')),
    })


@login_required
def supprimer_communication(request, com_id):
    comm = get_object_or_404(Communication, id=com_id)
    dossier = comm.dossier
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        comm.delete()
        messages.success(request, _("Communication supprimée."))
    return redirect(url_onglet(dossier.id, 'communications', request.GET.get('source', '')))


@login_required
def modifier_communication(request, com_id):
    comm = get_object_or_404(Communication, id=com_id)
    dossier = comm.dossier
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = CommunicationForm(request.POST, instance=comm)
        if form.is_valid():
            form.save()
            messages.success(request, _("Communication modifiée."))
            return redirect(url_onglet(dossier.id, 'communications', request.GET.get('source', '')))
    else:
        form = CommunicationForm(instance=comm)
    return render(request, 'element_modifier.html', {
        'form': form,
        'titre': _("Modifier la communication"),
        'retour': url_onglet(dossier.id, 'communications', request.GET.get('source', '')),
    })


@login_required
def supprimer_echeance(request, echeance_id):
    echeance = get_object_or_404(Echeance, id=echeance_id)
    dossier = echeance.dossier
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        echeance.delete()
        messages.success(request, _("Échéance supprimée."))
    return redirect(url_onglet(dossier.id, 'echeances', request.GET.get('source', '')))


@login_required
def modifier_echeance(request, echeance_id):
    echeance = get_object_or_404(Echeance, id=echeance_id)
    dossier = echeance.dossier
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = EcheanceForm(request.POST, instance=echeance)
        if form.is_valid():
            echeance = form.save(commit=False)
            if form.cleaned_data.get('mode_saisie') == 'automatique':
                try:
                    resultat = expliquer_calcul(
                        form.cleaned_data['type_procedure'],
                        form.cleaned_data['date_depart'])
                except ValueError as e:
                    messages.error(request, str(e))
                    return redirect(url_onglet(dossier.id, 'echeances', request.GET.get('source', '')))
                echeance.type_delai = resultat['description']
                echeance.date_limite = resultat['date_limite']
                echeance.calcul_automatique = True
                echeance.date_depart = form.cleaned_data['date_depart']
                echeance.reference_legale = resultat['reference_legale']
                echeance.duree_delai = f"{resultat['duree']} {resultat['unite'].replace('_', ' ')}"
            echeance.dossier = dossier
            echeance.save()
            messages.success(request, _("Échéance modifiée."))
            return redirect(url_onglet(dossier.id, 'echeances', request.GET.get('source', '')))
    else:
        form = EcheanceForm(instance=echeance)
    return render(request, 'element_modifier.html', {
        'form': form,
        'titre': _("Modifier l'échéance"),
        'retour': url_onglet(dossier.id, 'echeances', request.GET.get('source', '')),
    })


@login_required
def supprimer_entree_temps(request, entree_id):
    entree = get_object_or_404(EntreeTemps, id=entree_id)
    dossier = entree.dossier
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        entree.delete()
        messages.success(request, _("Entrée de temps supprimée."))
    return redirect(url_onglet(dossier.id, 'facturation', request.GET.get('source', '')))


@login_required
def modifier_entree_temps(request, entree_id):
    entree = get_object_or_404(EntreeTemps, id=entree_id)
    dossier = entree.dossier
    if not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        form = EntreeTempsEditForm(request.POST, instance=entree)
        if form.is_valid():
            form.save()
            messages.success(request, _("Entrée de temps modifiée."))
            return redirect(url_onglet(dossier.id, 'facturation', request.GET.get('source', '')))
    else:
        form = EntreeTempsEditForm(instance=entree)
    return render(request, 'element_modifier.html', {
        'form': form,
        'titre': _("Modifier l'entrée de temps"),
        'retour': url_onglet(dossier.id, 'facturation', request.GET.get('source', '')),
    })


@login_required
def supprimer_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    dossier = doc.dossier
    if dossier and not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    if request.method == 'POST':
        try:
            doc.fichier.delete(save=False)
        except Exception:
            pass
        doc.delete()
        messages.success(request, _("Document supprimé."))
    if dossier:
        return redirect(url_onglet(dossier.id, 'documents', request.GET.get('source', '')))
    return redirect('liste_documents')


@login_required
def modifier_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    dossier = doc.dossier
    if dossier and not _dossier_accessible(dossier, request.user):
        return redirect('liste_dossiers')
    retour = url_onglet(dossier.id, 'documents', request.GET.get('source', '')) if dossier else reverse('liste_documents')
    if request.method == 'POST':
        form = DocumentEditForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, _("Document modifié."))
            return redirect(retour)
    else:
        form = DocumentEditForm(instance=doc)
    return render(request, 'element_modifier.html', {
        'form': form,
        'titre': _("Modifier le document"),
        'retour': retour,
    })

