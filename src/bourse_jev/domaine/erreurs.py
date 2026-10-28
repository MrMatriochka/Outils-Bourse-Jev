"""Erreurs du domaine, levées par les adaptateurs et interprétées par l'application."""


class ConfigurationIncomplete(Exception):
    """Une ou plusieurs variables d'environnement obligatoires sont absentes ou vides."""


class QuotaAtteint(Exception):
    """La source a épuisé son quota (par minute ou par jour) : réessayer plus tard."""


class SourceIndisponible(Exception):
    """La source n'a pas pu fournir de cours exploitable pour ce titre."""
