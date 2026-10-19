from django.contrib import admin
from .models import Cabinet, Partage


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    list_display = ('nom', 'chef')
    search_fields = ('nom',)
    list_filter = ('chef',)


@admin.register(Partage)
class PartageAdmin(admin.ModelAdmin):
    list_display = ('type_objet', 'client', 'dossier', 'partage_par', 'partage_avec', 'statut', 'date')
    list_filter = ('statut', 'type_objet')
    search_fields = ('partage_par__username', 'partage_avec__username')
