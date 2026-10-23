"""Author the individual R0/V notebook without touching learner work or source data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_notebook():
    cells = []
    def md(text):
        cells.append({"cell_type": "markdown", "metadata": {"editable": False, "deletable": False}, "source": text.splitlines(keepends=True)})
    def code(text):
        cells.append({"cell_type": "code", "execution_count": None, "outputs": [],
            "metadata": {"editable": False, "deletable": False, "jupyter": {"source_hidden": True}, "tags": ["setup-nicht-aendern"]},
            "source": text.splitlines(keepends=True)})
    md("""# Unit 4: Challenge – RAG und persönlicher Dokument-Upload

**Version 1 · 23. Oktober 2026 · Einzelarbeit · Standardstart offline**

Sie wählen **eines von vier Dossiers**, erstellen selbst **20 Fragen mit geprüften Referenzen**
und vergleichen später 20 RAG-Antworten (R0) mit 20 Antworten aus ChatGPT/Claude mit PDF-Upload (V).
Nur R0 erhält eine automatische Vorprüfung. Beide Bedingungen beurteilen Sie abschliessend selbst.

## Bedienung ohne Programmieren

1. Wählen Sie **Run → Run All Cells**. Die eingeklappten Codezellen nur ausführen; nicht bearbeiten.
2. Bearbeiten Sie danach ausschliesslich Dropdowns, Textfelder und Schaltflächen.
3. Speichern Sie **jede Textseite und jede Frage vor dem Wechsel**. Ungespeicherte Eingaben gehen beim Wechsel verloren.
4. Speichern Sie Vorhersage und Referenzen, bevor Sie diese einfrieren. Danach bleibt der Pflichtvergleich unverändert.
5. Bei einem Neustart alle Zellen erneut ausführen. Wählen Sie Ihr zuvor gespeichertes Dossier wieder aus.

| Hier bearbeiten | Hier nur ausführen / prüfen |
| --- | --- |
| Dossierauswahl, korrigierte Textfassung, eigene Fragen und Referenzen | Code, Modellzugang und technische Dateien |
| Vorhersage und dokumentierte KI-Unterstützung | Festgelegter R0-Auftrag und Konfiguration |
| Erste ChatGPT-/Claude-Antwort, Dienst und Modell, eigene Bewertungsurteile | Eingefrorener Volltext und Referenzen nach Beginn des Vergleichs |

**Standardstart offline:** Modellschaltflächen bleiben gesperrt. Nur der ausdrücklich gewählte
Live-Start durch die Lehrperson lädt Zugangsdaten über Docker Compose und aktiviert API-Schaltflächen.
Das Ausführen der Notebookzellen selbst startet keine Modellaufrufe. Im Live-Modus zuerst in Schritt 3
eine separate API-Probe mit eigener Probefrage und geprüfter Probe-Referenz ausführen.

**Nur ausführen – nicht ändern:**""")
    code("""from pathlib import Path
import os, sys
os.environ.setdefault('CHALLENGE_OFFLINE', '1')
ROOT = Path.cwd()
if not (ROOT / 'src').exists():
    ROOT = ROOT / 'challenge'
assert (ROOT / 'src').exists(), 'Notebook im Ordner mit src/ und compose.yaml starten.'
sys.path.insert(0, str(ROOT))
from src.assignment_ui import ChallengeNotebook
session = ChallengeNotebook(ROOT)""")
    md("""## 1. Dokument auswählen und prüfen

Wählen Sie genau eines der vier Dossiers. Der gewählte Initiativauszug ist Ihr «Dokument»;
das Originalbüchlein enthält auch weitere Vorlagen. Diese weiteren Vorlagen werden im
Pflichtvergleich nicht indexiert. Der Quellenbestand enthält genau diese vier Dossiers.

Lesen Sie die vollständigen Quellenseiten in den breiten Karten und öffnen Sie die Original-PDFs.
Prüfen Sie Lesereihenfolge, Tabellen, Zahlen und die Zuschreibung von Argumenten. Im Feld
**Textfassung** können Sie Extraktionsfehler berichtigen. Speichern Sie jede bearbeitete Seite.
Danach die Prüfung der gesamten Textfassung bestätigen und speichern. Historische Angaben
nicht aufgrund späterer Entwicklungen umschreiben.

Nach dem Einfrieren wird genau diese Textfassung für R0 und die Referenzprüfung verwendet;
V nutzt die entsprechenden Originalseiten als PDF.
Gespeicherte Arbeiten liegen unter `outputs/meine_challenge/`.

**Nur ausführen – nicht ändern:**""")
    code("session.show_dossier()")
    md("""## 2. Referenzdatensatz festlegen

Erstellen Sie **20 eigene unterschiedliche Fragen** und prüfen Sie die Referenzantworten am ganzen Dossier.
Es werden keine fertigen Fragen zugeteilt. Die Felder sind zu Beginn leer.

| IDs | Typ | Anzahl |
| --- | --- | --- |
| F01–F05 | Direkte Fundstelle | 5 |
| F06–F10 | Andere Formulierung, keine Wiederholung früherer Fragen | 5 |
| F11–F15 | Mindestens zwei Quellenseiten verbinden | 5 |
| F16–F20 | Im gesamten Dossier nicht beantwortbar | 5 |

Tragen Sie Frage, Referenzantwort und erforderliche Antwortbestandteile ein, ein Bestandteil pro Zeile.
Wählen Sie Fundstellen mit Strg/Cmd+Klick. Bei F16–F20 beschreiben Sie zusätzlich die fehlende Information.
Eine automatische Prüfung der ausgefüllten Felder ersetzt Ihre fachliche Prüfung nicht.
KI darf Vorschläge machen; Sie prüfen und korrigieren diese und dokumentieren die Unterstützung.

**Diese Frage speichern** anklicken, bevor Sie die nächste auswählen. Referenzen bleiben ausserhalb
der Antwortprompts und des Suchindex; erst die spätere R0-Vorprüfung darf sie sehen.

**Nur ausführen – nicht ändern:**""")
    code("session.show_references()")
    md("""## 3. Beide Bedingungen vorbereiten

R0 erhält automatisch ausgewählte Chunks Ihres Dossiers. V ist Ihr üblicher PDF-Upload in ChatGPT oder Claude mit denselben ausgewählten Originalseiten.
Antwortauftrag und Quellenkennzeichnungen sind gleich. Der Pflichtlauf verwendet eine festgehaltene
R0-Konfiguration ohne zusätzliches Entscheidungsgate oder automatische Nachsuche.

Prüfen Sie die RAG-Verbindung vorab mit einer **separaten Probefrage**. Das Upload-PDF für V steht nach dem Einfrieren bereit.
Die aktuelle Chunkansicht zeigt Grenzen, aber noch keine semantische Suche.
Modell-IDs werden vor dem Live-Test durch die Lehrperson festgelegt; die Offline-Fassung zeigt fehlende IDs offen an.

Formulieren Sie **vor den Hauptläufen** eine überprüfbare Vorhersage für bestimmte Fragetypen.
Notieren Sie KI-Unterstützung und wesentliche Korrekturen bei der Referenzerstellung.
Speichern Sie die Vorbereitung. **Referenzen einfrieren** prüft die Vollständigkeit und bewahrt
Text, Fragen, Auftrag und Konfiguration als unveränderlichen Ausgangsstand.

**Nur ausführen – nicht ändern:**""")
    code("session.show_protocol()")
    md("""## 4. R0 und V ausführen

Nach Freigabe entstehen 20 unabhängige R0-Antworten im Notebook. Jede Antwort wird mit den
tatsächlich übergebenen Chunks gespeichert. Im Pflichtvergleich kein Tuning und keine korrigierenden Folgefragen.

Für V laden Sie das **bereitgestellte Dossier-PDF** herunter und in **ChatGPT oder Claude** hoch.
Es enthält nur dieselben ausgewählten Originalseiten wie R0. Verwenden Sie Ihren üblichen Dienst und Ihr
verfügbares Modell. Stellen Sie dieselben 20 Fragen mit dem gemeinsamen Auftrag; der kurze Fragenauftrag
aus dem Feld enthält die Seitenzuordnung, aber keine eingefügten Volltexte oder Referenzantworten.

Wie gewohnt können Sie F01–F20 nacheinander in einer Unterhaltung stellen oder getrennte Chats nutzen.
Halten Sie Dienst, Modell und Vorgehen fest und behalten Sie es bei. Keine Websuche, zusätzlichen Quellen,
Referenzen, RAG-Antworten oder korrigierenden Folgefragen verwenden. Frühere V-Fragen in derselben
Unterhaltung sind Teil des dokumentierten Gesprächsverlaufs. Die interne Dokumentverarbeitung bleibt unbekannt.

Speichern Sie jede erste V-Antwort unverändert, mit Dienst, Modell, Einstellungen und Gesprächsvorgehen.
Bestätigen Sie den Upload des bereitgestellten Dossier-PDFs.
Eine bereits gespeicherte Antwort lässt sich nicht überschreiben.

Sie vergleichen vollständige Arbeitsweisen. Modell, Oberfläche, PDF-/Textaufbereitung und Gesprächsverlauf dokumentieren; Unterschiede können dann nicht allein dem Retrieval
zugeschrieben werden. Technische Wiederholungen protokollieren, unbefriedigende Antworten nicht ersetzen.

**Nur ausführen – nicht ändern:**""")
    code("session.show_runs()")
    md("""## 5. Antworten prüfen und vergleichen

Das Entscheidungsmodell liefert nach den R0-Läufen **nur für R0** Vorschläge zu Korrektheit,
Quellenbelegen und Verfügbarkeit der notwendigen Belege. Es verändert keine generierten Antworten.
Die Decisions API klassifiziert auch einzelne Pflichtbestandteile. Einzelentscheidungen und Wahrscheinlichkeiten
bleiben gespeichert. Konkrete Beleg-IDs und die Begründung ergänzen Sie selbst; es gibt keine generierte Erklärung.
Prüfen, bestätigen oder korrigieren Sie jeden Vorschlag selbst anhand Ihrer Referenzen und der Quellen.
Falls die Vorprüfung technisch ausfällt, bewerten Sie R0 manuell und dokumentieren den Ausfall.

**V bewerten Sie vollständig selbst.** Es gibt keine automatische V-Bewertung. Für beide Bedingungen:

- Korrektheit 1: alle erforderlichen Bestandteile richtig, keine falschen Zusätze; sonst 0.
- Bei unbeantwortbaren Fragen zählt zutreffende Begrenzung ohne erfundene Antwort als 1.
- Belege: belegt / teilweise belegt / unbelegt; reine Begrenzung ohne Sachbehauptung: nicht anwendbar.
- Bei R0 und beantwortbaren Fragen zusätzlich: notwendige Belege vollständig, teilweise oder nicht vorhanden?

Markieren Sie ausdrücklich, ob eine Antwort Sachbehauptungen enthält; daraus ergibt sich der Nenner
der Belegquote. Begründen und bestätigen Sie jedes endgültige Urteil. Vorschläge werden nicht automatisch übernommen.
Ein ungelöster technischer Ausfall zählt als 0 im festen Nenner. Markieren Sie ihn nur nach tatsächlichem
Versuch; eine Offline-Sperre oder eine noch nicht bearbeitete Frage ist kein Experimentergebnis.

**Nur ausführen – nicht ändern:**""")
    code("session.show_evaluation()")
    md("""## 6. Schlussfolgerung und Regel ableiten

Aktualisieren Sie die Vergleichstabelle nach dem Bewerten. Solange Antworten oder menschliche Urteile
fehlen, bleiben Erfolgsquoten offen. Berichten Sie x/20, x/15, x/5 nach Fragetyp,
richtige Begrenzungen x/5 und vollständig belegte Antworten x/n. Bei n=0: nicht anwendbar.

Klicken Sie **Prüftabelle als Excel erstellen**, danach auf **Excel-Prüftabelle herunterladen**.
In `Challenge_4_Prueftabelle.xlsx` zeigt **Übersicht** alle 20 Fragen; **Prüftabelle** enthält 40 Zeilen
mit Frage, Referenz, Antwort und Urteil (R0 und V getrennt). Filtern Sie nach Frage-ID oder Bedingung.
Interne Links führen zu Quellenseiten und tatsächlichen R0-Chunks. **Vorprüfung R0** und **Kennzahlen**
enthalten Vorschläge und Ergebnisse; **Hinweise** erklärt die Prüfung für Studierende und Lehrpersonen.
Bewertungsänderungen in Schritt 5 des Notebooks speichern und Excel neu exportieren. Excel wird nicht
zurückgelesen. Lehrpersonen können Kommentare in der letzten Spalte ergänzen. Nur gespeicherte Eingaben
sind enthalten. Die ZIP-Abgabe enthält dieselbe Excel-Datei direkt im Hauptverzeichnis.

Untersuchen Sie **drei tatsächliche Fragepaare** genauer: Fehlten R0 Belege, wurden vorhandene Belege
falsch verwendet oder unterschied sich der persönliche Dokument-Upload? Beschreiben Sie auch Korrekturen an der automatischen R0-Vorprüfung.
Die unterschiedliche Bewertungsunterstützung ist eine Vergleichsgrenze.

Schreiben Sie einen Kurzbericht von etwa 3–4 Seiten mit Beobachtung, Erklärung, Grenzen und Transferregel.
Die Vorlage liegt unter `templates/Kurzbericht_Vorlage.md`. Der ZIP-Export sammelt die Arbeitsdateien;
ergänzen Sie Ihren echten Bericht. Keine Zugangsdaten beilegen. Auch Gleichstand oder schlechtere RAG-Leistung
sind gültige Ergebnisse. Die Quelle belegt zunächst Dokumenttreue, nicht automatisch Wahrheit.

**Nur ausführen – nicht ändern:**""")
    code("session.show_results()")
    md("""## Optionale Erweiterung: RAG-Genauigkeit verbessern

Erst nach dem Pflichtvergleich: fünf zusätzliche eigene Fragen A01–A05 mit Referenzen reservieren,
darunter alle vier Typen. Nur mit F01–F20 entwickeln, R1 vor dem Abschlusstest festlegen und danach
R0/R1 auf denselben fünf Abschlussfragen vergleichen (zehn neue Antworten). Kein erneuter V-Lauf nötig.
Ursprüngliche R0/V-Ergebnisse bewahren; nach dem Abschlusstest nicht weiter tunen.
Entwicklung und Abschluss getrennt im optionalen Anhang dokumentieren. Selbst erstellte Fragen sind kein blinder Test.

Die erste Notebookfassung unterstützt den Pflichtvergleich; ein optionales Tuningprojekt wird separat angelegt.""")
    for i, cell in enumerate(cells):
        cell["id"] = f"individual-v1-{i:02d}"
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 5}
    target = ROOT / "Evidenzknacker.ipynb"
    backup = ROOT / "outputs/notebook_before_individual_v1.ipynb"
    if target.exists() and not backup.exists():
        backup.parent.mkdir(exist_ok=True)
        backup.write_bytes(target.read_bytes())
    target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_notebook()
