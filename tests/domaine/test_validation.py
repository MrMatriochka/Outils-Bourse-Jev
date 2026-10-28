from decimal import Decimal as D

from bourse_jev.domaine.validation import MotifRejet, valider_cours
from tests.doublures import fabriquer_cours


def test_cours_normal_accepte():
    assert valider_cours(fabriquer_cours(), cloture_precedente=D("98")) is None


def test_premier_cours_sans_precedent_accepte():
    assert valider_cours(fabriquer_cours(), cloture_precedente=None) is None


def test_cloture_nulle_rejetee():
    c = fabriquer_cours(cloture=D("0"), bas=D("0"))
    assert valider_cours(c, D("98")) is MotifRejet.VALEUR_NON_POSITIVE


def test_volume_negatif_rejete():
    assert valider_cours(fabriquer_cours(volume=-1), D("98")) is MotifRejet.VALEUR_NON_POSITIVE


def test_haut_inferieur_au_bas_rejete():
    c = fabriquer_cours(haut=D("98"), bas=D("99"))
    assert valider_cours(c, D("98")) is MotifRejet.INCOHERENCE_HAUT_BAS


def test_cloture_au_dessus_du_haut_rejetee():
    c = fabriquer_cours(cloture=D("102"))
    assert valider_cours(c, D("98")) is MotifRejet.INCOHERENCE_HAUT_BAS


def test_hausse_de_50_pourcent_exactement_acceptee():
    c = fabriquer_cours(ouverture=D("150"), haut=D("150"), bas=D("149"), cloture=D("150"))
    assert valider_cours(c, D("100")) is None


def test_hausse_superieure_a_50_pourcent_rejetee():
    c = fabriquer_cours(ouverture=D("151"), haut=D("151"), bas=D("150"), cloture=D("151"))
    assert valider_cours(c, D("100")) is MotifRejet.VARIATION_ABERRANTE


def test_baisse_superieure_a_50_pourcent_rejetee():
    c = fabriquer_cours(ouverture=D("49"), haut=D("49"), bas=D("48"), cloture=D("49"))
    assert valider_cours(c, D("100")) is MotifRejet.VARIATION_ABERRANTE
