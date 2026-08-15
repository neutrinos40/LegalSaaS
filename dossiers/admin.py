from django.contrib import admin
from .models import Dossier
from .models import Dossier, ProfilAvocat

admin.site.register(Dossier)
admin.site.register(ProfilAvocat)