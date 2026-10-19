from .models import ProfilAvocat


def cabinet_context(request):
    if request.user.is_authenticated:
        profil, _ = ProfilAvocat.objects.get_or_create(user=request.user)
        if profil.cabinet:
            return {'cabinet_nom': profil.cabinet.nom}
    return {}
