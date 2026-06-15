#!/usr/bin/env python3

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Integer,
    DefaultValue,
    MigrateToIndividualOrStoredPassword,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _formspec():
    return Dictionary(
        title=Title("Reolink Kamera"),
        help_text=Help(
            "Überwacht eine Reolink IP-Kamera: HDD-Gesundheit, "
            "Speicherauslastung und CPU-Last."
        ),
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Benutzername"),
                    help_text=Help("Benutzername für die Kamera-Weboberfläche"),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=MigrateToIndividualOrStoredPassword(
                    title=Title("Passwort"),
                    help_text=Help(
                        "Passwort für die Kamera-Weboberfläche. "
                        "Kann direkt eingegeben oder aus dem CheckMK Password Store gewählt werden."
                    ),
                ),
            ),
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("HTTP-Port"),
                    help_text=Help("Standard: 80"),
                    prefill=DefaultValue(80),
                ),
            ),
        },
    )


rule_spec_reolink = SpecialAgent(
    topic=Topic.APPLICATIONS,
    name="reolink",
    title=Title("Reolink IP-Kamera"),
    parameter_form=_formspec,
)