# Unit 4: Challenge – RAG und persönlicher Dokument-Upload

**Version 1 · 23. Oktober 2026 · Standardstart offline, Live-Start optional**

Einzelarbeit: eine Person wählt eines von vier Dossiers, erstellt 20 eigene geprüfte
Fragen/Referenzen und vergleicht später 20 RAG-Antworten (R0) mit 20 Antworten aus dem persönlichen PDF-Upload in ChatGPT oder Claude (V). Nur R0 erhält eine automatische Vorprüfung;
die endgültige Bewertung beider Bedingungen erfolgt durch die Person.

## Challenge-Dokument

- Inhaltliche Quelle: `docs/Challenge_4_RAG_und_Dokument_Upload_V1.md`.
- Editable Word: `docs/Challenge_4_RAG_und_Dokument_Upload_V1.docx`.
- PDF: `docs/Challenge_4_RAG_und_Dokument_Upload_V1.pdf`.
- Struktur und sechs Schritte folgen der bereitgestellten ursprünglichen Kollegenvorlage.

## Eigenständiges GitHub-Repository

Die Dateien dieses Ordners bilden direkt das Hauptverzeichnis des neuen Repositories.
Keinen zusätzlichen `challenge/`-Unterordner anlegen. In diesem ursprünglichen Slides-Repository
zuerst `cd challenge` ausführen; danach gelten dieselben Docker-Befehle wie im eigenständigen Repository.

```text
<neues-repository>/
├── README.md
├── Evidenzknacker.ipynb
├── Dockerfile
├── compose.yaml
├── compose.live.yaml
├── requirements.txt
├── requirements.resolved.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── instructor_config.example.json
├── .devcontainer/
├── docs/                 # Aufgabenblatt als Markdown, Word und PDF
├── corpus/
│   ├── pdfs/             # A2024.pdf, R2024.pdf, P2024.pdf, K2024.pdf
│   ├── sources.json
│   ├── passages.jsonl
│   └── passages.manifest.json
├── src/                  # Notebook-Logik, RAG, Auswertung, Excel-Export
├── scripts/              # Notebook-/Quellenwerkzeuge, Prüfung, Handout-Export
├── tests/
├── templates/            # Kurzbericht-Vorlage
├── evaluation/           # Nur Entwicklungsentwürfe, keine vorgegebenen Lernendenfragen
├── instructor/           # Nur frühere Entwicklungsentwürfe
└── outputs/.gitkeep      # Leerer Ausgabeordner
```

Für die Weitergabe ist ein bereinigtes ZIP vorbereitet. **Den Inhalt des ZIPs** ins neue
Repository übernehmen, einschliesslich der Punktdateien. `PACKAGE_MANIFEST.json` dokumentiert
die Dateien und Prüfsummen zum Zeitpunkt der Paketierung; die Notebook-Laufzeit verwendet
weiterhin die eigene Quellen-/Protokollintegrität.

Nicht hochladen: `.env`, `instructor_config.json`, vorhandene `outputs/`-Inhalte,
`cache/`, `.ipynb_checkpoints/`, `.pytest_cache/`, `__pycache__/`, `.venv/` und Slides-Dateien.
`.gitignore` schützt diese lokalen Dateien. Ausgaben im Notebook vor einem eigenen Commit leeren;
das vorbereitete ZIP enthält ein Notebook ohne Ausgaben.

Für den Live-Start `.env.example` einmal lokal nach `.env` kopieren und den Schlüssel eintragen
(die bestehende `.env` bei Updates erhalten). Im GitHub-Repository bleibt nur die leere Vorlage.
Die Modellzeilen stehen im Abschnitt «Live-Test starten».

## Start mit Docker

Im Hauptverzeichnis des eigenständigen Challenge-Repositories (neben `compose.yaml`):

```powershell
docker compose up --build
```

Jupyter-Link mit Token aus dem Terminal auf http://localhost:8889 öffnen, dann
`Evidenzknacker.ipynb`. Nach einem Update das Notebook erneut öffnen und
**Kernel → Restart Kernel and Run All Cells** wählen. Codezellen sind eingeklappt
und gegen versehentliches Bearbeiten geschützt; nur Eingabefelder bedienen.

```powershell
docker compose down
```

Port 8889 ist nur an die lokale Schnittstelle gebunden. Das Verzeichnis ist eingebunden;
gespeicherte Arbeiten bleiben beim Stoppen erhalten. Der Build lädt Abhängigkeiten und
Tokenisierungsvokabular; die spätere Quellenarbeit benötigt kein Netzwerk.

## Arbeitsablauf im Notebook

1. **Dokument auswählen und prüfen:** 13. AHV-Rente, Renteninitiative,
   Prämien-Entlastungs-Initiative oder Kostenbremse-Initiative. Volltextkarten lesen,
   Extraktionsfehler bei Bedarf am Original korrigieren und Prüfung bestätigen.
2. **Referenzdatensatz festlegen:** 20 leere Frageformulare, fünf je Typ. Eigene
   Referenzantwort, erforderliche Bestandteile und Fundstellen eintragen; jede Frage speichern.
3. **Beide Bedingungen vorbereiten:** feste R0-Konfiguration prüfen, Vorhersage und
   KI-Unterstützung dokumentieren. Geprüfte Vorbereitung einfrieren.
4. **R0 und V ausführen:** R0-Modelllauf ist beim Standardstart gesperrt; der separate Live-Start aktiviert ihn. Nach dem Einfrieren sind
   das Upload-Dossier-PDF und kurze Fragenaufträge für ChatGPT/Claude vorhanden. Kopieren über Textfeld oder gespeicherte
   TXT-Dateien. Erste V-Antwort mit Dienst, Modell, Gesprächsvorgehen und Upload-Bestätigung unverändert speichern.
5. **Antworten prüfen und vergleichen:** automatischer R0-Vorschlag wird getrennt von
   menschlichen Urteilen gespeichert; V bleibt manuell. Urteil, Belege und Begründung
   speichern. Noch nicht bearbeitete Fragen sind keine technischen Ausfälle.
6. **Schlussfolgerung und Regel ableiten:** Tabelle aktualisieren, drei Fragepaare
   erläutern, eigenen Kurzbericht erstellen und Arbeitsdateien als ZIP exportieren.

Die Originalfrageentwürfe in `evaluation/` und `instructor/` sind Reserve-/Entwicklungsmaterial.
Die aktuelle Lernendenansicht lädt sie nicht. Sie beginnt mit 20 leeren Feldern für eigene Fragen.
Das frühere A/B-Tuning und Entscheidungsgate sind kein Teil des Pflichtvergleichs.

## Speicherung und unveränderliche Evidenz

`outputs/meine_challenge/<Dossier-ID>/vorbereitung.json` bewahrt gespeicherte Eingaben.
Jede Seite und Frage vor dem Wechsel speichern. Bei einem Neustart dasselbe Dossier wählen.
Alte Arbeitsblätter aus der vorausgehenden Offline-Übung werden nicht gelöscht.

Beim Einfrieren entstehen unter `vergleich/<ID>/`:

- `protocol.json`, `references.json`, `integrity.json` und `fulltext.txt`;
- ausgewähltes Upload-Dossier-PDF mit SHA-256/Seitenzuordnung und 20 kurze referenzfreie Aufträge unter `v_prompts/`;
- später erste Antworten unter `answers/R0/` und `answers/V/`;
- unveränderte Modellversuche/Fehler und die tatsächlich übergebenen R0-Chunks;
- automatische Vorprüfungen nur unter `automatic_r0/` und menschliche Urteile getrennt;
- Vergleichstabelle und Kennzahlen beim Export.

Hashprüfungen erkennen Änderungen an eingefrorenen Grundlagen. Erste gespeicherte
Antworten werden nicht überschrieben. Menschliche Bewertungsänderungen bleiben als
Verlauf erhalten. Nur menschlich bestätigte Urteile bestimmen die Quoten. Fehlende
Antworten/Urteile lassen Quoten offen; erklärte ungelöste Ausfälle zählen im festen Nenner als 0.

Der ZIP-Export enthält Quellen, Text/Referenzen, Systemdateien, Modellbelege und den
eingefrorenen Arbeitsstand. Unter `system/` lässt sich dieser offline wieder öffnen.
Die Berichtsvorlage muss durch den tatsächlichen Kurzbericht ergänzt werden.
Konfigurationsdateien mit Zugangsdaten werden nicht exportiert.

## Antworten prüfen und Excel herunterladen

**Speichern** in den Formularen sichert jeweils den aktuellen Eintrag in den Arbeitsdateien;
es startet keinen Download. Fragen/Textseiten vor dem Wechsel speichern. Menschliche Urteile
in Schritt 5 speichern. Danach in Schritt 6 **Prüftabelle als Excel erstellen** und den
erscheinenden Link **Excel-Prüftabelle herunterladen** anklicken.

`Challenge_4_Prueftabelle.xlsx` enthält:

- **Hinweise:** Anleitung und Bewertungsregeln für Studierende und Lehrpersonen.
- **Übersicht:** 20 Fragen mit R0-/V-Urteilen, Bearbeitungsstand und korrigierten R0-Vorschlägen.
- **Prüftabelle:** 40 Zeilen, je Frage und Bedingung eine; Frage, Referenz, Originalantwort,
  Fundstellen, R0-Vorschlag, menschliche Urteile/Begründungen und Modelle gemeinsam sichtbar.
- **Vorprüfung R0:** automatische Klassifikationen und gespeicherte Einzelwahrscheinlichkeiten.
- **Quellenseiten / R0-Chunks:** vollständige geprüfte Texte bzw. tatsächlich übergebene Chunks;
  interne Links aus der Prüftabelle öffnen die erste zugehörige Stelle, alle IDs bleiben sichtbar.
- **Kennzahlen:** nur menschlich bestätigte Quoten; offene Arbeit bleibt offen.
- **Langtexte:** Texte über der Excel-Zellgrenze vollständig in nummerierten Teilen.

Lehrpersonen öffnen zuerst **Übersicht**, filtern **Prüftabelle** nach Frage-ID/Bedingung und
prüfen Antwort gegen Referenz und Fundstellen; bei R0 zusätzlich die tatsächlich übergebenen Chunks.
Die letzte Spalte bietet Platz für Kommentare der Lehrperson. Filter, fixierte Spalten/Kopfzeilen
und umbrochener Text erleichtern die Prüfung. Zeilenhöhe bei Bedarf vergrössern.

Die Excel-Datei ist eine exportierte Ansicht: Änderungen darin werden nicht ins Notebook
zurückgelesen und ändern keine Kennzahlen. Studierende ändern/speichern eigene Bewertungen in
Schritt 5 und erstellen die Excel-Datei neu. Vor erneuter Erstellung eine von Lehrpersonen
kommentierte Kopie separat sichern. Alle Exporte funktionieren offline, ohne neue Modellaufrufe.

**Arbeitsdateien als ZIP exportieren** erstellt ebenfalls die aktuelle Excel-Datei und zeigt
Download-Links für Excel und ZIP. Im ZIP liegt die Prüftabelle direkt im Hauptverzeichnis.
Gespeichert wird sie unter `outputs/meine_challenge/<Dossier-ID>/vergleich/<Vergleich-ID>/`.
Die ZIP liegt unter `outputs/meine_challenge/<Dossier-ID>/`. Eigenen Kurzbericht ergänzen.

Nach diesem Update den Container mit `--build` neu erstellen (Excel-Bibliothek ergänzt),
Notebook vom Datenträger neu öffnen und Kernel/alle Zellen neu starten. Arbeitsdateien bleiben erhalten.

## Quellenbestand

Der Quellenbestand enthält genau vier PDFs: `A2024.pdf`, `R2024.pdf`, `P2024.pdf`
und `K2024.pdf`. Die vier Dossiers umfassen je zwölf ausgewählte Seiten, insgesamt 48,
mit URLs, Seitenkennzeichnungen, Quellenrollen und Prüfsummen. Nur das ausgewählte
Dossier wird für R0 und V verwendet. R0 verwendet die geprüfte Textextraktion, V einen PDF-Auszug derselben Originalseiten.

Einige Originalbüchlein enthalten mehrere Vorlagen. Beim Einfrieren entsteht deshalb
`<Dossier-ID>_Dossier.pdf` mit genau den zwölf ausgewählten Originalseiten für V.
Grafiken, Tabellen und Lesereihenfolge müssen am Original geprüft werden.

`scripts/download_sources.py` und `scripts/configure_sources.py` sind Organisatorwerkzeuge.
`scripts/prepare_corpus.py` extrahiert mit pypdf und versiegelt den Textbestand erneut;
das kann mehrere Minuten dauern. Das Notebook lädt den vorbereiteten Bestand schnell.

## Offline-Sperre und spätere Modellfreigabe

Der Standardstart setzt `CHALLENGE_OFFLINE=1`, liest keine `.env` und sperrt Modellaufrufe.
Der zusätzliche Live-Start liest die vorhandene `.env` neben `compose.yaml` über Compose und setzt
`CHALLENGE_OFFLINE=0`. Das Notebook startet beim Ausführen der Zellen keine API-Aufrufe;
nur ein Klick auf eine Modellschaltfläche löst diese aus.

Die API-Funktionen `run_rag` und `evaluate_rag_only` sind getrennt vorbereitet und lokal
mit Test-Doubles geprüft. R0 ruft einmal ab und generiert ohne Referenzen und ohne Gate.
Nur der spätere Evaluator erhält Referenzen, vollständiges Dossier, R0-Antwort und Chunks.
Die R0-Vorprüfung nutzt `client.decisions.create` am dedizierten Endpoint
`POST /v1/decisions` mit `gpt-6-luna`. Sie klassifiziert Korrektheit, Beleglage,
Evidenzverfügbarkeit und jeden Pflichtbestandteil. Die vollständige Anfrage/Antwort
mit Wahrscheinlichkeiten und Tokenverbrauch bleibt gespeichert. Es gibt keine generierte
Erklärung und keine generierten Beleg-IDs; diese ergänzt die Person selbst.
Verweigerte/ungültige Antworten werden als Rohdaten erhalten und nicht als Note übernommen.

Offizielle API-Dokumentation: https://developers.openai.com/api/docs/guides/decisions

Er erzeugt Vorschläge, keine endgültigen Noten. Es gibt keine automatische V-Bewertung.

## Live-Test starten

In `.env` neben `compose.yaml` die vorhandene API-Key-Zeile erhalten und diese Modellzeilen ergänzen/prüfen:

```dotenv
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_GENERATION_MODEL=gpt-6-luna
OPENAI_DECISION_MODEL=gpt-6-luna
```

`gpt-6-luna` dient hier als Startwert auch für die Generation über Responses. Die
Modellfreigabe des eigenen API-Projekts muss mit der Probe geprüft werden. Eine vorhandene
`instructor_config.json` hat für Modell-IDs Vorrang vor diesen Umgebungsvariablen.

Im Hauptverzeichnis des eigenständigen Challenge-Repositories (neben `compose.yaml`):

```powershell
docker compose -f compose.yaml -f compose.live.yaml up --build --force-recreate
```

Jupyter-Link mit Token aus dem Terminal öffnen (Port 8889), `Evidenzknacker.ipynb` öffnen,
**Kernel → Restart Kernel and Run All Cells** wählen. Oben muss **Live-Modus** stehen.
Ein Dossier wählen. In Schritt 3 eine separate Probefrage und eine selbst am Dossier
geprüfte Probe-Referenz eingeben; dann **Eine API-Probe starten** anklicken.
Die Probe testet Embeddings → FAISS → RAG-Generation → Decisions-Vorprüfung mit einer Frage.
Sie benötigt weder 20 Fragen noch das Einfrieren. Sie erzeugt keine Hauptvergleichsantworten.
Rohdaten, Antwort, Vorprüfung und Tokenverbrauch liegen separat unter `outputs/live_probes/`.
Es gibt keine automatischen SDK-Wiederholungen; bei Fehlern bleiben Versuche erhalten.

Erst nach erfolgreicher technischer und inhaltlicher Prüfung die 20 eigenen Fragen
fertigstellen, Referenzen einfrieren, in Schritt 4 **20 R0-Antworten erzeugen** und danach
in Schritt 5 **20 R0-Antworten mit Decisions prüfen** anklicken. Alle Vorprüfungen selbst prüfen.
Neue/unverfrorene Vorbereitungen übernehmen die Live-Modellnamen. Bereits eingefrorene
Offline-Testprotokolle werden nicht verändert; fehlt darin das Antwortmodell, für den
Hauptvergleich eine neue Vorbereitung anlegen, statt das alte Protokoll umzuschreiben.

Zurück zu Offline (Container neu erstellen, gespeicherte Arbeiten bleiben erhalten):

```powershell
docker compose up --force-recreate
```

Schlüssel bleiben ausserhalb von Git und Abgabe-ZIPs. API-Aufrufe sind kostenpflichtig.
Der Live-Start allein sendet keine Daten; die Modellschaltflächen starten die Aufrufe.

## Prüfen und Dokumente neu erzeugen

```powershell
docker compose run --rm challenge python scripts/verify.py
```

Tests und Notebookprüfung können auch mit deaktiviertem Containernetzwerk laufen.
Die automatisierten Prüfungen verwenden lokale Test-Doubles statt echter API-Aufrufe. Weitere Rechnerarchitekturen sind noch nicht geprüft.

Prüfung am 23. Oktober 2026: **45 Tests bestanden**, Notebook vollständig ohne
Containernetzwerk ausgeführt, eingefrorene Formularansicht und Archiv geprüft.
Das siebenseitige Word/PDF-Dokument hat dieselben Hauptüberschriften und sechs Schritte
wie die Kollegenvorlage. Der gemeinsame Antwortauftrag stimmt mit dem Notebook überein.

`scripts/build_notebook.py` erzeugt nur das Notebook und bewahrt eine Sicherung der
vorherigen Fassung unter `outputs/`. Quellen und gespeicherte Lernendenarbeit bleiben erhalten.

Word/PDF im eigenständigen Repository neu erzeugen (benötigt lokal Windows und Word; für die Challenge-Ausführung nicht erforderlich):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_exercise_handout.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/style_challenge_handout.ps1
```

Nach manuellen Word-Änderungen diese zuerst in Markdown rückführen; keine Lehrerredaktion
ungeprüft überschreiben. Die optionale RAG-Optimierung bleibt ein getrennt dokumentiertes Projekt.


## Pflege im ursprünglichen Slides-Repository

Die inhaltliche Handout-Quelle bleibt hier `exercises/challenge_4_rag_volltext.md`,
die aktuellen Word-/PDF-Exporte liegen unter `output/exercises/`. Nach Änderungen dort
vom Slides-Repository aus `python scripts/package_challenge.py` ausführen. Dieses Werkzeug
synchronisiert die freigegebenen Dokumente nach `challenge/docs/`, stellt eigenständige
Handout-Exportskripte bereit und erzeugt `output/challenge/Challenge_4_GitHub_Repository.zip`.
Im getrennten Repository sind dagegen `docs/` und die dort mitgelieferten Skripte massgeblich;
es besteht keine Abhängigkeit zum Slides-Repository.

## Vergleich mit dem persönlichen ChatGPT-/Claude-Workflow

R0 = unsere feste RAG-Pipeline. V = PDF-Upload im persönlich gewählten Dienst ChatGPT oder Claude.
Kein Einfügen des gesamten Dossiertexts erforderlich. In Schritt 4 das bereitgestellte Dossier-PDF
herunterladen, hochladen und die kurzen Fragenaufträge verwenden. Wie gewohnt eine Unterhaltung
für alle Fragen oder neue Chats verwenden; das gewählte Vorgehen mit Dienst/Modell pro Antwort speichern.
Fragen, Auftrag, Quellenseiten und Bewertung bleiben gleich. Die interne Dokumentverarbeitung von V
ist unbekannt; Unterschiede können durch Modell, Oberfläche, Aufbereitung, Retrieval und Gesprächsverlauf
entstehen. Es geht um den Vergleich vollständiger Arbeitsweisen, nicht um die isolierte Wirkung von Retrieval.
Excel weist Dienst und Gesprächsvorgehen aus. Nur R0 erhält die automatische Vorprüfung.

Bereits eingefrorene alte Volltext-Protokolle behalten ihren gespeicherten Modus und werden nicht umgedeutet.
Für den neuen Upload-Vergleich eine neue Vorbereitung nutzen; vorhandene Originalantworten nicht überschreiben.
Die aktuellen Handouts heissen Challenge_4_RAG_und_Dokument_Upload_V1.docx/.pdf. Frühere Volltext-Handouts sind überholt.
