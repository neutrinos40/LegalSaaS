from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _

from dossiers.views import get_profil
from .models import Cabinet, Partage


@login_required
def gestion_cabinet(request):
    profil = get_profil(request.user)
    cabinet = profil.cabinet

    if not cabinet:
        cabinets = Cabinet.objects.all()
        return render(request, 'cabinet_rejoindre.html', {
            'cabinets': cabinets,
            'active': 'cabinet',
        })

    est_chef = (cabinet.chef == request.user)
    membres = User.objects.filter(profil__cabinet=cabinet).select_related('profil')

    demandes_en_attente = Partage.objects.filter(
        partage_avec=request.user, statut='en_attente'
    ).select_related('partage_par', 'client', 'dossier')

    demandes_creees = Partage.objects.filter(
        partage_par=request.user
    ).select_related('partage_avec', 'client', 'dossier')

    context = {
        'cabinet': cabinet,
        'est_chef': est_chef,
        'membres': membres,
        'demandes_en_attente': demandes_en_attente,
        'demandes_creees': demandes_creees,
        'active': 'cabinet',
    }
    return render(request, 'cabinet_liste.html', context)


@login_required
def creer_cabinet(request):
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if nom:
            cabinet = Cabinet.objects.create(
                nom=nom,
                chef=request.user,
                logo=request.FILES.get('logo'),
                adresse=request.POST.get('adresse', '').strip(),
                telephone=request.POST.get('telephone', '').strip(),
                email=request.POST.get('email', '').strip(),
                site_web=request.POST.get('site_web', '').strip(),
            )
            profil = get_profil(request.user)
            profil.cabinet = cabinet
            profil.save()
            messages.success(request, _("Cabinet « %(nom)s » créé.") % {'nom': nom})
            return redirect('gestion_cabinet')
        else:
            messages.error(request, _("Le nom du cabinet est requis."))
    return render(request, 'cabinet_creer.html', {'active': 'cabinet'})


@login_required
def rejoindre_cabinet(request):
    if request.method == 'POST':
        cabinet_id = request.POST.get('cabinet_id', '')
        try:
            cabinet = Cabinet.objects.get(id=cabinet_id)
        except Cabinet.DoesNotExist:
            messages.error(request, _("Cabinet introuvable."))
            return redirect('gestion_cabinet')

        profil = get_profil(request.user)
        profil.cabinet = cabinet
        profil.save()
        messages.success(request, _("Vous avez rejoint le cabinet « %(nom)s ».") % {'nom': cabinet.nom})
        return redirect('gestion_cabinet')
    cabinets = Cabinet.objects.all()
    return render(request, 'cabinet_rejoindre.html', {'cabinets': cabinets, 'active': 'cabinet'})


@login_required
def partager_objet(request):
    if request.method == 'POST':
        profil = get_profil(request.user)
        if not profil.cabinet:
            messages.error(request, _("Aucun cabinet assigné."))
            return redirect('reglages')

        type_objet = request.POST.get('type_objet')
        objet_id = request.POST.get('objet_id')
        avec_id = request.POST.get('partage_avec')

        try:
            destinataire = User.objects.get(id=avec_id)
        except User.DoesNotExist:
            messages.error(request, _("Destinataire introuvable."))
            return redirect('gestion_cabinet')

        if destinataire == request.user:
            messages.error(request, _("Vous ne pouvez pas partager avec vous-même."))
            return redirect('gestion_cabinet')

        destinataire_profil = getattr(destinataire, 'profil', None)
        if not destinataire_profil or destinataire_profil.cabinet != profil.cabinet:
            messages.error(request, _("Cet avocat n'est pas dans votre cabinet."))
            return redirect('gestion_cabinet')

        kwargs = {'type_objet': type_objet, 'partage_par': request.user,
                  'partage_avec': destinataire, 'statut': 'en_attente'}

        if type_objet == 'client':
            from clients.models import Client
            objet = get_object_or_404(Client, id=objet_id, avocat=request.user)
            kwargs['client'] = objet
        elif type_objet == 'dossier':
            from dossiers.models import Dossier
            objet = get_object_or_404(Dossier, id=objet_id, avocat=request.user)
            kwargs['dossier'] = objet
        else:
            messages.error(request, _("Type d'objet invalide."))
            return redirect('gestion_cabinet')

        existant = Partage.objects.filter(
            client=kwargs.get('client'), dossier=kwargs.get('dossier'),
            partage_par=request.user, partage_avec=destinataire,
        ).exists()
        if existant:
            messages.warning(request, _("Ce partage existe déjà."))
        else:
            Partage.objects.create(**kwargs)
            messages.success(request, _("Demande de partage envoyée à %(nom)s.") %
                             {'nom': destinataire.get_full_name() or destinataire.username})

        if type_objet == 'client':
            return redirect('fiche_client', client_id=objet_id)
        return redirect('fiche_dossier', dossier_id=objet_id)

    return redirect('gestion_cabinet')


@login_required
def repondre_partage(request, partage_id):
    partage = get_object_or_404(Partage, id=partage_id, partage_avec=request.user, statut='en_attente')

    action = request.POST.get('action')
    if action == 'accepter':
        partage.statut = 'accepte'
        partage.save()
        messages.success(request, _("Partage accepté."))
    elif action == 'refuser':
        partage.statut = 'refuse'
        partage.save()
        messages.info(request, _("Partage refusé."))

    return redirect('gestion_cabinet')
