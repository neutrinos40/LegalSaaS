from django.contrib import admin
from .models import Abonnement, UsageIA, Facture, TempsTravail


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ('avocat', 'nom_plan', 'prix_mensuel', 'quota_mensuel', 'actif')
    list_filter = ('nom_plan', 'actif')
    search_fields = ('avocat__username',)


@admin.register(UsageIA)
class UsageIAAdmin(admin.ModelAdmin):
    list_display = ('avocat', 'type_usage', 'octets', 'date')
    list_filter = ('type_usage',)
    search_fields = ('avocat__username',)


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('avocat', 'mois', 'montant', 'payee', 'date_emission')
    list_filter = ('payee', 'mois')
    search_fields = ('avocat__username',)


@admin.register(TempsTravail)
class TempsTravailAdmin(admin.ModelAdmin):
    list_display = ('avocat', 'dossier', 'debut', 'fin', 'duree', 'description')
    list_filter = ('debut', 'fin')
    search_fields = ('dossier__titre', 'avocat__username', 'description')
