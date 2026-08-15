from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.db.models import Q
from django.http import HttpResponse

from .forms import CommunicationForm
from .models import Dossier, ProfilAvocat
from echeances.forms import EcheanceForm
from echeances.models import Echeance, RendezVous
from documents.models import Document
from documents.forms import DocumentForm
from facturation.forms import EntreeTempsForm
from facturation.services import (
    demarrer_chrono as demarrer_chrono_service,
    arreter_chrono as arreter_chrono_service,
    total_secondes_dossier,
    formater_secondes,
)
from facturation.models import TempsTravail

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
    """Retourne la classe CSS selon l'urgence : rouge, orange, vert."""
    jours_restants = (echeance.date_limite - timezone.now().date()).days
    if echeance.statut == 'depasse' or jours_restants <= seuil_rouge:
        return 'rouge'
    if jours_restants <= seuil_orange:
        return 'orange'
    return 'vert'


def get_profil(user):
    """Retourne le profil de l'avocat (créé au besoin)."""
    profil, _ = ProfilAvocat.objects.get_or_create(user=user)
    return profil


@login_required
def dashboard(request):
    profil = get_profil(request.user)

    actif = request.GET.get('actif', 'echeances')
    if actif not in ('dossiers', 'echeances', 'rdv', 'calendrier', 'revenus'):
     actif = 'echeances'

    dossiers = Dossier.objects.filter(avocat=request.user).order_by('-date_debut')
    pag_dossiers = Paginator(dossiers, 10 if actif == 'dossiers' else 5)
    dossiers = pag_dossiers.get_page(request.GET.get('page_dossiers', 1))

    echeances = Echeance.objects.filter(
        dossier__avocat=request.user,
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
        dossier__avocat=request.user,
        date_heure__gte=timezone.now(),
        statut='planifie'
    ).order_by('date_heure')
    pag_rdv = Paginator(rendez_vous, 10 if actif == 'rdv' else 5)
    rendez_vous = pag_rdv.get_page(request.GET.get('page_rdv', 1))

    documents_recents = (Document.objects.select_related('dossier')
                         .filter(Q(dossier__avocat=request.user) | Q(auteur=request.user))
                         .order_by('-date_upload')[:5])

    # --- KPI ---
    from clients.models import Client as ModeleClient
    from facturation.models import Facture as ModeleFacture

    nb_clients = ModeleClient.objects.filter(avocat=request.user).count()
    nb_dossiers = Dossier.objects.filter(avocat=request.user).count()
    nb_echeances = Echeance.objects.filter(
        dossier__avocat=request.user, statut__in=['a_venir', 'depasse']).count()
    nb_rdv = RendezVous.objects.filter(
        dossier__avocat=request.user, date_heure__gte=timezone.now(),
        statut='planifie').count()
    mois_courant = timezone.now().strftime('%Y-%m')
    factures_mois = ModeleFacture.objects.filter(avocat=request.user, mois=mois_courant)
    revenus_mois = sum(float(f.montant) for f in factures_mois)

    factures_avocat = ModeleFacture.objects.filter(avocat=request.user)
    factures_payees = factures_avocat.filter(statut='payee')
    factures_impayees = factures_avocat.filter(statut='envoyee')
    factures_brouillon = factures_avocat.filter(statut='brouillon')
    nb_payees = factures_payees.count()
    total_payees = sum(float(f.montant) for f in factures_payees)
    nb_impayees = factures_impayees.count()
    total_impayees = sum(float(f.montant) for f in factures_impayees)
    nb_brouillons = factures_brouillon.count()
    total_brouillons = sum(float(f.montant) for f in factures_brouillon)

    # --- Graphique : revenus par mois (par statut) ---
    from collections import defaultdict
    rev_par_mois = defaultdict(lambda: {'payee': 0.0, 'envoyee': 0.0, 'brouillon': 0.0})
    for f in factures_avocat:
        rev_par_mois[f.mois][f.statut] += float(f.montant)
    derniers_mois = sorted(rev_par_mois.keys())[-6:]
    rev_labels = derniers_mois
    rev_payees = [rev_par_mois[m]['payee'] for m in derniers_mois]
    rev_impayees = [rev_par_mois[m]['envoyee'] for m in derniers_mois]
    rev_brouillons = [rev_par_mois[m]['brouillon'] for m in derniers_mois]

    # --- Graphique : échéances par mois (6 prochains mois) ---
    from calendar import monthrange
    aujourd_hui = timezone.now().date()
    mois_labels = []
    mois_counts = []
    for i in range(6):
        annee = aujourd_hui.year + (aujourd_hui.month + i - 1) // 12
        mois = (aujourd_hui.month + i - 1) % 12 + 1
        debut = date(annee, mois, 1)
        fin = date(annee, mois, monthrange(annee, mois)[1])
        count = Echeance.objects.filter(
            dossier__avocat=request.user,
            date_limite__gte=debut, date_limite__lte=fin,
        ).count()
        mois_labels.append(date(annee, mois, 1).strftime('%m/%Y'))
        mois_counts.append(count)

    # --- Graphique : statuts des dossiers ---
    statut_labels = []
    statut_data = []
    for code, label in Dossier.STATUT_CHOICES:
        count = Dossier.objects.filter(avocat=request.user, statut=code).count()
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
    }
    return render(request, 'dashboard.html', context)


def prochaine_echeance(dossier):
    """Retourne la prochaine échéance à venir du dossier (ou None)."""
    return dossier.echeances.filter(statut__in=['a_venir', 'depasse']).order_by('date_limite').first()


@login_required
def liste_dossiers(request):
    profil = get_profil(request.user)
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '')
    type_procedure = request.GET.get('type_procedure', '')

    dossiers = Dossier.objects.filter(avocat=request.user).select_related('client')

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
        avocat=request.user,
    )

    onglet = request.GET.get('onglet', 'apercu')
    if onglet not in ONGLETS_DOSSIER:
        onglet = 'apercu'

    source = request.GET.get('source', '')
    if source != 'clients':
        source = ''

    session_chrono = TempsTravail.objects.filter(
        dossier=dossier, avocat=request.user, fin__isnull=True).first()
    if session_chrono is None and not TempsTravail.objects.filter(
            dossier=dossier, avocat=request.user).exists():
        session_chrono = TempsTravail.objects.create(dossier=dossier, avocat=request.user)

    documents = Document.objects.filter(
        Q(client=dossier.client) | Q(dossier__client=dossier.client)
    ).filter(
        Q(dossier__avocat=request.user) | Q(auteur=request.user)
    ).distinct().order_by('-date_upload')
    rendez_vous = dossier.rendez_vous.all().order_by('-date_heure')
    communications = dossier.communications.all().order_by('-date')
    entrees_temps = dossier.entrees_temps.all().order_by('-date', '-cree_le')

    echeances = []
    for echeance in dossier.echeances.all().order_by('date_limite'):
        jours_restants = (echeance.date_limite - timezone.now().date()).days
        echeances.append((
            echeance,
            niveau_urgence(echeance, profil.seuil_rouge, profil.seuil_orange),
            jours_restants,
        ))

    total_secondes = total_secondes_dossier(dossier)
    entrees_facturables = entrees_temps.filter(non_facturable=False)
    total_montant = sum((e.montant for e in entrees_facturables), Decimal('0'))
    total_minutes = sum(e.duree_minutes for e in entrees_facturables)
    taux = taux_horaire_effectif(dossier, profil)

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
        'taux': taux,
        'chronologie': chronologie,
        'entree_temps_form': EntreeTempsForm(initial={
            'date': timezone.localdate(),
            'duree_minutes': minutes_ecoulees,
            'taux_horaire_applique': taux,
        }),
        'entree_temps_ajout_form': EntreeTempsForm(initial={
            'date': timezone.localdate(),
            'taux_horaire_applique': taux,
        }),
        'echeance_form': EcheanceForm(),
        'communication_form': CommunicationForm(),
        'document_form': DocumentForm(
            initial={'dossier': dossier, 'client': dossier.client},
            user=request.user,
        ),
        'active': 'clients' if source == 'clients' else 'dossiers',
        'source': source,
    }
    return render(request, 'fiche_dossier.html', context)


@login_required
def demarrer_chrono(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id, avocat=request.user)
    if request.method == 'POST':
        for actif in TempsTravail.objects.filter(
                avocat=request.user, fin__isnull=True).exclude(dossier=dossier):
            actif.fin = timezone.now()
            actif.save()
        demarrer_chrono_service(dossier, request.user)
        messages.success(request, _("Chrono démarré."))
    return redirect(url_onglet(dossier.id, 'apercu', request.GET.get('source', '')))

@login_required
def arreter_chrono(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id, avocat=request.user)
    if request.method == 'POST':
        session = arreter_chrono_service(dossier, request.user)
        if session is not None and session.fin:
            profil = get_profil(request.user)
            form = EntreeTempsForm(request.POST)
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
    dossier = get_object_or_404(Dossier, id=dossier_id, avocat=request.user)
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
    dossier = get_object_or_404(Dossier, id=dossier_id, avocat=request.user)
    if request.method == 'POST':
        form = EcheanceForm(request.POST)
        if form.is_valid():
            echeance = form.save(commit=False)
            echeance.dossier = dossier
            echeance.save()
            messages.success(request, _("Échéance ajoutée."))
        else:
            messages.error(request, _("Erreur dans l'échéance."))
    return redirect(url_onglet(dossier.id, 'echeances', request.GET.get('source', '')))


@login_required
def ajouter_entree_temps(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id, avocat=request.user)
    if request.method == 'POST':
        form = EntreeTempsForm(request.POST)
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
def ajouter_document(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id, avocat=request.user)
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
        avocat=request.user,
    )
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

    if request.method == 'POST':
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

    context = {'profil': profil, 'message': message, 'message_ok': message_ok}
    return render(request, 'reglages.html', context)