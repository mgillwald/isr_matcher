"""Script that contains dictionaries with explanations and transformations for track properties."""

from isr_matcher._constants._parse import (
    identity,
    str_to_int,
    str_to_float,
    incline_to_array,
    db_km_to_km,
    str_to_lat_lon,
    db_km_alt_to_km,
)

# fmt: off

##### ISR - Infrastrukturregister der Deutschen Bahn

### Abkürzungen

# ALG - Allgemein
# ISR - Infrastrukturregister
# INF - Infrastruktur
# BET - Betrieb
# LST - Zugsteuerung, Zugsicherung und Signalgebung
# ENE - Energie

### STRECKENABSCHNITTE 

# TODO: Check if integer properties should use identity (int -> int) or str_to_int (str -> int). (Depends on json string)

ISR_PROPERTIES_TRACK_SEGMENTS = {
    "ALG_BESONDERE_PRUEF": ["Streckenkilometer bestimmter Stellen, die besondere Prüfung erfordern", "Lage bestimmter Stellen, die wegen Abweichungen von den oben genannten Lichtraumprofilen besondere Prüfungen erfordern", identity],
    "ALG_BESONDERE_PRUEF_DOK": ["Dokument mit den Querschnitten der Stellen, die besondere Prüfung erfordern", "Elektronisches Dokument, das vom Infrastrukturbetreiber zur Verfügung gestellt und von der ERA gespeichert wird, mit den Querschnitten der Stellen, die wegen Abweichungen von den oben genannten Lichtraumprofilen besondere Prüfungen erfordern. Dem Dokument mit dem Querschnitt können gegebenenfalls Hinweise für die Prüfung der bestimmten Stellen beigefügt werden.", identity],
    "ALG_BSTGZIELHOEHE": ["Bahnsteigzielhöhe [mm]", "Soll-Abstand zwischen der Bahnsteigoberkante und der Lauffläche des benachbarten Gleises. Die angegebenen Bahnsteighöhen sind Systemhöhen. Diese beinhalten auch Übergangsflächen zwischen verschiedenen Systemhöhen und beziehen sich immer auf die Soll-Gleislage. Die tatsächliche Bahnsteighöhe kann auf Grund der Ist-Gleislage und Instandhaltungstoleranzen von der Systemhöhe abweichen.", str_to_float],
    "ALG_DBNETZ_STRECKE": [],
    "ALG_GUE_KORR_7": ["Angabe, ob die Strecke dem Schienengüterverkehrskorridor 7 gemäß EU-Verordnung (EU)913/2010 zugeordnet ist", "Ein Güterverkehrskorridor (englisch Rail Freight Corridor, RFC) ist eine ausgewiesene Eisenbahnstrecke zwischen zwei oder mehr Staaten der Europäischen Union, die zwei oder mehr Bahnhöfe entlang einer Hauptroute miteinander verbindet. Sie werden auch SGV-Korridore genannt.", identity],
    "ALG_GUE_KORR_9": ["Angabe, ob die Strecke dem Schienengüterverkehrskorridor 9 gemäß EU-Verordnung (EU)913/2010 zugeordnet ist", "Ein Güterverkehrskorridor (englisch Rail Freight Corridor, RFC) ist eine ausgewiesene Eisenbahnstrecke zwischen zwei oder mehr Staaten der Europäischen Union, die zwei oder mehr Bahnhöfe entlang einer Hauptroute miteinander verbindet. Sie werden auch SGV-Korridore genannt.", identity],
    "ALG_GUE_KORR_A": ["Angabe, ob die Strecke dem Schienengüterverkehrskorridor 1 gemäß EU-Verordnung (EU)913/2010 zugeordnet ist", "Ein Güterverkehrskorridor (englisch Rail Freight Corridor, RFC) ist eine ausgewiesene Eisenbahnstrecke zwischen zwei oder mehr Staaten der Europäischen Union, die zwei oder mehr Bahnhöfe entlang einer Hauptroute miteinander verbindet. Sie werden auch SGV-Korridore genannt.", identity],
    "ALG_GUE_KORR_B": ["Angabe, ob die Strecke dem Schienengüterverkehrskorridor 3 gemäß EU-Verordnung (EU)913/2010 zugeordnet ist", "Ein Güterverkehrskorridor (englisch Rail Freight Corridor, RFC) ist eine ausgewiesene Eisenbahnstrecke zwischen zwei oder mehr Staaten der Europäischen Union, die zwei oder mehr Bahnhöfe entlang einer Hauptroute miteinander verbindet. Sie werden auch SGV-Korridore genannt.", identity],
    "ALG_GUE_KORR_D": ["Angabe, ob die Strecke dem Schienengüterverkehrskorridor 4 gemäß EU-Verordnung (EU)913/2010 zugeordnet ist", "Ein Güterverkehrskorridor (englisch Rail Freight Corridor, RFC) ist eine ausgewiesene Eisenbahnstrecke zwischen zwei oder mehr Staaten der Europäischen Union, die zwei oder mehr Bahnhöfe entlang einer Hauptroute miteinander verbindet. Sie werden auch SGV-Korridore genannt.", identity],
    "ALG_GUE_KORR_F": ["Angabe, ob die Strecke dem Schienengüterverkehrskorridor 8 gemäß EU-Verordnung (EU)913/2010 zugeordnet ist", "Ein Güterverkehrskorridor (englisch Rail Freight Corridor, RFC) ist eine ausgewiesene Eisenbahnstrecke zwischen zwei oder mehr Staaten der Europäischen Union, die zwei oder mehr Bahnhöfe entlang einer Hauptroute miteinander verbindet. Sie werden auch SGV-Korridore genannt.", identity],
    "ALG_IM_CODE": ["Infrastrukturbetreiber Code - Kennung des Infrastrukturbetreibers", "Numerische Codierung des Infrastrukturbetreibers gemäß UIC-Liste (verfügbar unter http://www.uic.org -> Company Codes) z. B. 0080 für die DB Netz AG.", identity],
    "ALG_INFRA_BETR": ["Infrastrukturbetreiber", "Infrastrukturbetreiber bezeichnet eine Einrichtung oder ein Unternehmen, die bzw. das insbesondere für die Einrichtung und Unterhaltung der Fahrwege der Eisenbahn zuständig ist.", identity],
    "ALG_INT_LIRA_PROFIL": ["Interoperables Lichtraumprofil", "Lichtraumprofile GA, GB, GC G1, DE3 gemäß europäischer Norm (EN 15273-3:2013).", identity],
    "ALG_KV_PROFIL": ["KV Kodifizierung", "Kodierung für den kombinierten Verkehr mit Wechselbehälter gemäß UIC-Merkblatt 596-6. Angabe nur auf Strecken wo auch kombinierter Verkehr tatsächlich gefahren wird.", identity],
    "ALG_LAENGE_ABSCHNITT": ["Länge des Streckenabschnittes [km]", "Länge der Strecke zwischen den Betriebsstellen am Beginn und Ende des Streckenabschnitts.", str_to_float],
    "ALG_MIN_LIRA_PROFIL": ["Multinationales Lichtraumprofil", "Multinationales Lichtraumprofil oder internationales Lichtraumprofil außer GA, GB, GC, G1, DE3, S, IRL1 gemäß europäischer Norm (in Deutschland nur G2)", identity],
    "ALG_NAT_LIRA_PROFIL": ["Nationales Lichtraumprofil", "Inländisches Lichtraumprofil gemäß europäischer Norm oder anderes lokales Lichtraumprofil (in Deutschland zurzeit DE1 und DE2). Die fahrzeugbezogenen Streckenfreigaben werden in den Anlagen 5.x zu den Grundsätzen des ISR veröffentlicht.", identity],
    "ALG_SPEZ_INFO": ["Spezifische Informationen", "Relevante Informationen des Infrastrukturbetreibers in Bezug auf die Trassierung.", identity],
    "ALG_STAAT": ["Staat", "Mitgliedstaat der europäischen Union (+UK +NO +CH).", identity],
    "ALG_STRECKENKLASSE": ["Streckenklasse", "Angabe der maximalen Radsatzlast und der zulässigen Last je Längeneinheit. Die Strecken der DB Netz AG werden in die Streckenklassen A – D4 nach DIN EN 15528 eingeteilt. Zusätzlich gelten folgende nationale Erweiterungen: https://fahrweg.dbnetze.com/resource/blob/1357560/5ce6d02c8c5ed5da47f7d065a269e61c/allgemein_grundsaetze_isr-data.pdf, Abschn. 2.1.1., Streckenklasse.", identity],
    "ALG_TEN_GIS_ID": ["TEN-GIS ID", "Angabe der GIS ID des Abschnitts der TEN-V-Datenbank, zu dem der Streckenabschnitt gehört.", identity],
    "ALG_TEN_GUETER": ["TSI Streckenkategorie Güterverkehr", "Die TSI-Streckenkategorie ergibt sich aus einer Kombination so genannter Verkehrscodes (Traffic Code). Die Einteilung werden durch folgende Leistungskennwerte bestimmt: Lichtraumprofil - Achsfahrmasse - Streckengeschwindigkeit - Zuglänge.", identity],
    "ALG_TEN_KLASSIFIZIERUNG": ["TEN Klassifizierung", "Angabe des Teils des transeuropäischen Netzes, zu dem die Strecke gehört nach TSI Infrastruktur (VERORDNUNG (EU) Nr. 1299/2014) gültig seit 01.01.2015.", identity],
    "ALG_TEN_PERSON": ["TSI Streckenkategorie Personenverkehr", "Die TSI-Streckenkategorie ergibt sich aus einer Kombination so genannter Verkehrscodes (Traffic Code). Die Einteilung werden durch folgende Leistungskennwerte bestimmt: Lichtraumprofil - Achsfahrmasse - Streckengeschwindigkeit - Bahnsteignutzlänge.", identity],
    "ALG_TEN_REGPERSON": ["TSI Streckenkategorie regionaler Personenverkehr", "TSI-Streckenkategorie für den regionalen Personenverkehr, wir ebenfalls durch die Leistungskennwerte Lichtraumprofil, Achsfahrmasse, Streckengeschwindigkeit und Bahnsteignutzlänge bestimmt.", identity],
    "ALG_VERKEHRSART": ["Verkehrsart", "Angabe der Verkehrsart (Pz, Gz, Mischverkehr, S-Bahn), 'Pz', 'Gz' oder 'S-Bahn' bedeutet, dass die jeweils anderen Verkehrsarten ausgeschlossen sind.", identity],
    "BET_BETRIEBSVERFAHREN": ["Betriebsverfahren", "Angabe des anzuwendenden Betriebsverfahren zum Verkehren von Zügen, Rangierfahrten und anderem (z. B. Betriebsverfahren nach Richtlinie 408, Zugleitbetrieb nach Richtlinie 436, 438 oder FV-NE, Signalisierter Zugleitbetrieb nach Richtlinie 437).", identity],
    "BET_EINSCHR_DOK": [],
    "BET_GESCHWINDIGKEIT": ["Geschwindigkeit [km/h]", "Zulässige betriebliche Höchstgeschwindigkeit auf der Strecke in Kilometer/Stunde.", str_to_float],
    "BET_NOTBREMS_UEBERBRUECK": ["Notbremsüberbrückung", "Angabe ob auf dem Streckenabschnitt, eine Notbremsüberbrückungseinrichtung erforderlich ist. Nach der EBA-Richtlinie 'Anforderung des Brand- und Katastrophenschutzes an den Bau und den Betrieb von Eisenbahntunneln (Stand 01.07.2008) gelten für TEN-Strecken die Vorschriften der TSI. Außerhalb des Geltungsbereiches des TEN und bei Ausnahmen zur TSI müssen die Notbremsen von allen in Reisezügen eingestellten Fahrzeugen, die lange und sehr lange Tunnel befahren, so beschaffen sein, dass eine durch Reisende eingeleitete Notbremsung bis zum Verlassen des Tunnels aufgehoben werden kann.", identity],
    "BET_OEFFNUNGSZEITEN": ["Streckenöffnungszeiten", "Informationen zu Öffnungszeiten der Strecken sind als Sachdaten zu den Betriebsstellen im ISR hinterlegt.", identity],
    "BET_PFV": ["Personenfernverkehr", "Angabe ob auf einem Streckenabschnitt Züge des Personenfernverkehrs verkehren.", identity],
    "DET_KAPAZITAETSBINDUNG": [],
    "ENE_ANF_STROMABN": ["Anforderung bzgl. der Zahl der ausgefahrenen Stromabnehmer und deren Abstand zueinander, bei gegebener Geschwindigkeit", "Angabe der zulässigen Höchstzahl der ausgefahrenen Stromabnehmer je Zug und des Mindestabstands der Mittellinien benachbarter Stromabnehmerwippen in Metern bei vorgegebener Geschwindigkeit. Zugelassen ist im Netz der DB ein Betrieb mit maximal zwei gehobenen Stromabnehmern in einem Abstand von x < 35 m bzw. x > 85 m.", identity],
    "ENE_AUTO_STROMABN_SENK": ["Automatische Stromabnehmer-Senkeinrichtung erforderlich", "Angabe, ob am Fahrzeug eine automatische Absenkeinrichtung vorhanden sein muss.", identity],   
    "ENE_BEGRENZ_BORD": ["Strombegrenzung an Bord erforderlich", "Angabe, ob eine fahrzeugseitige Strom- oder Leistungsbegrenzungsfunktion erforderlich ist.", identity],       
    "ENE_EGPRUEF_DOK": ["EG-Prüfung TSI ENE", "Eindeutige Nummer der EG-Erklärung gemäß den Formatvorgaben in 'Document aboutpractical arrangements for transmitting interoperability documents'.", identity],      
    "ENE_MAXSTROM_GZ": ["Höchster Zugstrom (Güterzug) [A]", "Angabe der maximal zulässigen Stromaufnahme der Güterzüge in Ampere (A). Je nach Zugsicherungssystem kann der angegebene Wert nicht vollständig ausgenutzt werden.", str_to_float],
    "ENE_MAXSTROM_PZ": ["Höchster Zugstrom (Personenzug) [A]","Angabe der maximal zulässigen Stromaufnahme der Personenzüge in Ampere (A). Je nach Zugsicherungssystem kann der angegebene Wert nicht vollständig ausgenutzt werden.", str_to_float],
    "ENE_MAXSTROM_STILL": ["Maximale Stromaufnahme bei Stillstand je Stromabnehmer [A]", "Angabe der maximal zulässigen Stromaufnahme der Züge bei Stillstand in Ampere (A). Für DC-Systeme überwiegend in den Grenzbereichen, eventuell auch Auskunft in den Grenzbetriebsvereinbarungen beachten.", str_to_float],
    "ENE_MAX_FAHRDRAHTHOEHE": ["Maximale Fahrdrahthöhe [mm]", "Angabe der maximalen Fahrdrahthöhe in Millimetern.", str_to_float],
    "ENE_MIN_FAHRDRAHTHOEHE": ["Minimale Fahrdrahthöhe [mm]", "Angabe der Mindestfahrdrahthöhe in Millimetern. Nach EBO Anlage 3 Abs. 3 liegt die Mindestfahrdrahthöhe bei 4,95m. Ausnahmen davon werden in der Liste sowie in der Übersichtskarte als Anlage 6 veröffentlicht. Die Daten zur freien Strecke finden sich zudem in der interaktiven Karte des ISR wieder.", str_to_float],
    "ENE_MITTL_KONTAKTKRAFT": ["Mittlere Kontaktkraft - Kurve", "Angabe der Kurve zur Bestimmung der zulässigen Kontaktkraft (AC C, AC C1, AC C2, DC 1,5 kV, DC 3 kV). Zur Bestimmung der mittleren Kontaktkraft siehe https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32008D0284&from=PL#d1e260-1-1, Abschn. 4.2.15.", identity],
    "ENE_NUTZBREMS_ERL": ["Erlaubnis für Nutzbremsung vorhanden", "Angabe, ob Nutzbremsung erlaubt ist oder nicht. Bei Wechselstrom 15kV 16,7Hz und 25kV 50Hz immer erlaubt im Oberleitungsnetz der DB. Ebenso. im Oberleitungsnetz der DB, bei Gleichstrom 1,5 kV 3000A und 3kV 2400A. Für die S-Bahn Hamburg und Berlin kann keine Aussage getroffen werden.", identity],
    "ENE_PHASENTRENNSTR": ["Phasentrennstrecken (Schutzstrecken)", "Angabe, ob Phasentrennung vorhanden ist.", identity],
    "ENE_PHASENTRENNSTRSPEC": ["Phasentrennstrecken - Spezifikation", "Angabe mehrerer erforderlicher Daten zur Phasentrennung. Aus programmtechnischen Gründen erfolgt die Anzeige nur in Englisch. Bsp: ''length 144 + switch off breaker Y + lower pantograph Y' (length: Länge des spannungslosen Abschnitts in Meter, switch off breaker Y/N: Hauptschalter ausschalten Ja/Nein, lower pantograph Y/N: Stromabnehmer senken Ja/Nein).", identity],
    "ENE_SYSTEMTRENNSTR": ["Systemtrennstrecken", "Angabe, ob eine Systemtrennung vorhanden ist. Sind nur im Bereich von Grenzbahnhöfen und/oder grenzüberschreitenden Strecken vorhanden (Stromsystemwechsel). Regelungen sind in den Grenzvereinbarungen zu finden.", identity],
    "ENE_SYSTEMTRENNSTRSPEC": ["Systemtrennstrecken - Spezifikation", "Angabe mehrerer erforderlicher Daten zur Systemtrennung. Aus programmtechnischen Gründen erfolgt die Anzeige nur in Englisch. Bsp: 'length 144 + switch off breaker Y + lower pantograph Y + change supply system Y' (lenght: Länge des spannungslosen Abschnitts in Meter, switch off breaker Y/N: Hauptschalter ausschalten Ja/Nein, lower pantograph Y/N: Stromabnehmer senken Ja/Nein, change supply system Y/N: Wechsel des Versorgungssystems Ja/Nein).", identity],
    "ENE_TRAKT_STROMART": ["Stromversorgungssystem (Spannung und Frequenz)", "Angabe des Stromversorgungssystems (Nennspannung und –frequenz).", identity],
    "ENE_ZUL_SSWERKSTOFF": ["Zulässiger Schleifstückwerkstoff", "Angabe, welche Schleifstückwerkstoffe verwendet werden dürfen. In Deutschland reine Hartkohle und (ab 2017) imprägnierte Kohle mit Zusatz-Werkstoffen.", identity],
    "ENE_ZUL_STROMABN_BREITE": ["Zugelassene Stromabnehmerbreite [mm]", "Angabe von TSI-konformen Stromabnehmerwippen, die verwendet werden dürfen. Generell ist im 15kV-Netz der DB nur eine Stromabnehmerbreite von 1950mm zulässig. Liegt eine passende EG-Prüfung vor, kann auch eine Breite von 1600mm zugelassen sein.", str_to_float],
    "ID": ["Identifikatinsnummer", "Identifkitationsnummer im Infrastrukturregister.", identity],
    "INF_BUE_BESCHLEUNIGUNG": ["An Bahnübergängen erlaubte Beschleunigung [m/s^2]", "Grenzwert für die Beschleunigung des Zuges, falls er in der Nähe eines Bahnübergangs hält, in Meter pro Sekunde zum Quadrat.", str_to_float],
    "INF_EGPRUEF_DOK": ["EG Prüfung TSI INF", "Eindeutige Nummer der EG-Erklärung gemäß den Formatvorgaben in 'Document about practical arrangements for transmitting interoperability' (ERA/INF/10-2009/INT verfügbar auf der ERA-Webseite).", identity],
    "INF_ELEKTROMAG_BED": ["Bedingungen für den Einsatz von Magnetschienenbremsen", "Elektronisches Dokument, das vom Infrastrukturbetreiber zur Verfügung gestellt und von der ERA gespeichert wird, mit den Bedingungen für den Einsatz von Magnetschienenbremsen.", identity],
    "INF_ELEKTROMAG_ERL": ["Elektromagnetische Bremsen", "Angabe der Einschränkungen für den Einsatz von Magnetschienenbremsen.", identity],
    "INF_GLEISANZAHL": ["Gleis", "Angabe, ob die Streckenführung ein- oder zweigleisig ist. Bei zweigleisigen Strecken wird gemäß Ril 883.1000 zwischen dem Richtungsgleis und dem Gegengleis unterschieden. 'Bei zweigleisigen Strecken ist das Richtungsgleis das vom Streckenanfang in Richtung auf das Streckenende rechts gelegene Gleis. Das Gegenrichtungsgleis ist das in diesem Sinne links gelegene Gleis.' (Ril 883.1000)", identity],
    "INF_HOA_VORH": ["Streckenseitige Heißläuferortungsanlagen (HOA) vorhanden", "Die folgenden Alarmarten sind für alle Arten von HOA gültig: Warmalarm (Radsatzlager – Umgebungstemperatur), Heißalarm (Radsatzlager – Umgebungstemperatur), Differenzalarm (Differenz zwischen linkem und rechtem Achslager), Alarmgrenzwerte. Die folgenden Alarmgrenzwerte sind für alle Arten von HOA gültig: Warmalarm 70K, Heißalarm 100K, Differenzalarm 65K.", identity],
    "INF_HOECHSTHOEHE": ["Höchsthöhe [m]", "Höchster Punkt des Streckenabschnitts über Meereshöhe bezogen auf NAP (Normal Amsterdam’s Peil) in Metern.", str_to_float],
    "INF_HSLM": ["Konformität von Bauwerken mit dem dynamischen Lastmodell HSLM", "Für Streckenabschnitte mit zulässiger Höchstgeschwindigkeit von mindestens 200km/h. Informationen zum Verfahren zur Durchführung der Prüfung der dynamischen Kompatibilität.", identity],
    "INF_HSLM_DOK": ["Dokument mit dem Verfahren für statische und dynamische Streckenkompatibilitätsprüfungen", "Elektronisches Dokument, das vom Infrastrukturbetreiber zur Verfügung gestellt und von der ERA gespeichert wird, mit dem genauen Verfahren für statische und dynamische Prüfungen der Streckenkompatibilität oder einschlägigen Informationen für die Durchführung der Prüfungen an bestimmten Bauwerken.", identity],
    "INF_HSLM_KM": ["Streckenkilometrierung von Bauwerken, die besondere Prüfungen erfordern", "Lage von Bauwerken, die besondere Prüfungen erfordern.", identity],
    "INF_KOMM_SYSTEM": ["Kommunikationssystem", "Angaben des installierten Zugfunksystems (analoger Zugfunk, VZF 95 II, GSM-R oder GSM).", identity], 
    "INF_LEISE_STRECKE": ["Gehört zu einer leiseren Eisenbahnstrecke", "Gehört nach Artikel 5b der Verordnung (EU) Nr. 1304/2014 der Kommission zu einer 'leiseren Eisenbahnstrecke'.", identity],
    "INF_MAX_RAD_DURCHMESSER": ["Radmindestdurchmesser für stumpfe Kreuzungen [mm]", "Die maximal zulässige Herzstücklücke einer festen stumpfen Kreuzung beruht auf einem in Millimetern angegebenen Radmindestdurchmesser, auch nach Abnutzung, im Betrieb.", str_to_float],
    "INF_MAX_UEBERH_FEHLBETRAG": ["Maximaler Überhöhungsfehlbetrag [mm]", "Maximaler Überhöhungsfehlbetrag in Millimetern, definiert als Differenz zwischen der tatsächlichen Überhöhung und einer höheren Ausgleichserhöhung, für die die Strecke ausgelegt ist.", str_to_float],
    "INF_MAX_ZUGVERZOEGERUNG": ["Maximale Zugverzögerung [m/s^2]", "Grenzwert für die Gleislagestabilität in Längsrichtung, angegeben als höchstzulässige Zugverzögerung in Metern pro Sekunde zum Quadrat.", str_to_float],
    "INF_MIN_BOGENRADIUS": ["Kleinster Bogenhalbmesser [m]", "Halbmesser des kleinsten horizontalen Bogens des Gleises in Metern. Die dargestellten Mindestradien gelten richtungsbezogen auch für die Fahrt im durchgehenden Hauptgleis. Beim Befahren von Weichenverbindungen und anderen Gleisen können, gemäß EBO, auch Radien bis 150m auftreten.", str_to_float],
    "INF_NEIGETECHNIK": ["Neigetechnik", "Angabe der Zugbeeinflussungssysteme, welche auf diesen Streckenabschnitten (ZUB 262, ZUB 122 oder ZUB 122/ZUB) vorhanden sind.", identity],
    "INF_REGELSPURWEITE": ["Regelspurweite [mm]", "Die Regelspurweite ist das lichte Innenmaß zwischen den zwei Schienenköpfen. Die Regelspurweite beträgt in Deutschland und den meisten europäischen Ländern 1435 mm (auch: Normalspur).", str_to_float],
    "INF_SCHIENENNEIGUNG": ["Schienenneigung", "Neigung des Kopfes einer im Gleis verlegten Schiene gegenüber der Lauffläche (1:20 oder 1:40).", identity],
    "INF_SCHOTTER_VORH": ["Schotter vorhanden", "Angabe, ob das Phänomen Schotterflug beim Hochgeschwindigkeitsverkehr auftreten kann. Angaben nur bei Strecken mit Vmax > 250km/h.", identity],
    "INF_SEITENWINDREST": [],
    "INF_SPURKRANZ": ["Einsatz von Spurkranzschmierung untersagt", "Angabe, ob die Nutzung von fahrzeugseitigen Einrichtungen zur Spurkranzschmierung verboten ist.", identity],
    "INF_STEIGUNGSPROFIL": ["Steigungsprofil", "Abfolge der Steigungswerte und Angabe der Orte, an denen sich die Steigung ändert. Wird im Format [±NN.N] ([±NNNN.NNN]) Neigung (Ort) angegeben und beliebig oft wiederholt. Dabei ist der erste Ort die Lage der Startbetriebsstelle und damit der Beginn des ersten Neigungswertes. Die letzte Ortsangabe ist der Beginn des letzten Neigungswert, der dann in der Endbetriebsstelle endet. Der minimale Neigungswechsel beträgt 0,5 mm/m.", incline_to_array],
    "INF_STRECKENNEIGUNG": ["Streckenneigung", "Angabe der maximalen Neigung zwischen 2 Betriebsstellen in 5‰-Schritten zur besseren Darstellung als thematische Karte. Detaillierte Angaben zu Steigung und Gefälle auf dem Streckenabschnitt finden sich in den Angaben zum 'Steigungsprofil'.", identity],
    "INF_STRENG_KLIMA": ["Vorliegen strenger klimatischer Bedingungen", "Strenge oder normale klimatische Bedingung auf der Strecke gemäß europäischer Norm.", identity],
    "INF_STRIKT_LOKAL": ["Vorschriften und Einschränkungen strikt lokaler Art vorhanden", "Vorschriften und Einschränkungen strikt lokaler Art vorhanden.", identity],
    "INF_STRIKT_LOKAL_DOK": ["Dokument des Infrastrukturbetreibers zu Vorschriften und Einschränkungen strikt lokaler Art", "Elektronisches Dokument, das vom Infrastrukturbetreiber zur Verfügung gestellt und der ERA gespeichert wird, mit zusätzlichen Angaben zu den Vorschriften und Einschränkungen strikt lokaler Art.", identity],
    "INF_TEMP_SPANNE": ["Temperaturspanne [°C]", "Temperaturspanne für den uneingeschränkten Zugang zur Strecke gemäß europäischer Norm.", identity],
    "INF_TRAKTIONSART": ["Traktionsart", "Angabe über die Elektrifizierung (Oberleitung, Stromschiene) oder ohne Elektrifizierung.", identity],
    "INF_TSI_EINHALT_BETRIEBSWERT": ["TSI-Einhaltung der Betriebswerte für Weichen und Kreuzungen", "Weichen und Kreuzungen werden gemäß den in den TSI spezifizierten Betriebsgrenzwerten instandgehalten.", identity],
    "INF_WIRBELSTROM_BED": ["Bedingungen für den Einsatz von Wirbelstrombremsen", "Elektronisches Dokument, das vom Infrastrukturbetreiber zur Verfügung gestellt und von der ERA gespeichert wird, mit den Bedingungen für den Einsatz von Wirbelstrombremsen.", identity],
    "INF_WIRBELSTROM_ERL": ["Wirbelstrombremse", "Angabe der Einschränkungen für den Einsatz von Wirbelstrombremsen.", identity],   
    "ISEG_ID": [],
    "ISR_KM_BIS": ["Kilometer (bis) [km + m]", "Angaben der Kilometrierung (metergenau) der Betriebsstellen (meist Mitte Empfangsgebäude) am Ende eines Streckenabschnitts.", identity],
    "ISR_KM_BIS_I": ["Kilometer (bis) - DB Codierung", "Angaben der Kilometrierung (metergenau) der Betriebsstellen (meist Mitte Empfangsgebäude) am Ende eines Streckenabschnitts (DB Codierung).", str_to_int],
    "ISR_KM_VON": ["Kilometer (von) [km + m]", "Angaben der Kilometrierung (metergenau) der Betriebsstellen (meist Mitte Empfangsgebäude) am Anfang eines Streckenabschnitts.", identity],
    "ISR_KM_VON_I": ["Kilometer (von) - DB Codierung", "Angaben der Kilometrierung (metergenau) der Betriebsstellen (meist Mitte Empfangsgebäude) am Anfang eines Streckenabschnitts (DB Codierung).", str_to_int],
    "ISR_STEL_ID_BIS": ["Identifikationsnummer der Betriebsstelle am Streckenabschnittsende", "Identifikationsnummer im Infrastrukturregister der Betriebsstelle am Streckenabschnittsende.", identity],
    "ISR_STEL_ID_VON": ["Identifikationsnummer der Betriebsstelle am Streckenabschnittsanfang", "Identifikationsnummer im Infrastrukturregister der Betriebsstelle am Streckenabschnittsanfang.", identity],
    "ISR_STRECKE_VON_BIS": ["Streckenabschnitt", "Eindeutige Bezeichnungen der Betriebsstellen am Anfang und am Ende eines Streckenabschnitts. Dabei kann ein Streckenabschnitt nicht in derselben Betriebsstelle enden wie er gestartet ist.", identity],
    "ISR_STRE_NR": ["Strecken-Nr.", "Bezeichnung und Identifizierung für Eisenbahnstrecken in Deutschland.", identity],
    "JAHR": ["Jahr", "Angabe des Jahres.", identity],
    "LADE_ID": ["Lade ID", "Lade Identifkationsnummer im Infrastrukturregister.", identity],
    "LST_ARTEN_ZUGORTUNG": ["Art der Zugortungsanlage/Gleisfreimeldeeinrichtung", "Angabe der Arten von installierten Zugortungsanlagen/Gleisfreimeldeeinrichtungen.", identity],
    "LST_BESONDERE_PRUEF": ["Gleisstromkreise oder Achszähler, die besondere Prüfungen erfordern", "Angabe der Arten von Zugortungsanlagen/Gleisfreimeldeeinrichtungen, die besondere Prüfungen erfordern.", identity],
    "LST_BESONDERE_PRUEF_DOK": ["Dokument zur besonderen Prüfung von Gleisstromkreisen und Achszählern", "Elektronisches Dokument, das vom Infrastrukturbetreiber in zwei EU-Sprachen zur Verfügung gestellt und von der ERA gespeichert wird, mit dem genauen Verfahren für die besondere Prüfung der angegebenen Zugortungsanlagen/Gleisfreimeldeeinrichtungen.", identity],    
    "LST_BETRIEBSBESCHR": ["Betriebsbeschränkungen oder -bedingungen vorhanden", "Angabe, ob Beschränkungen oder Bedingungen aufgrund einer Teilkonformität mit der TSI ZZS — Verordnung (EU) 2016/919 der Kommission (5) vorhanden sind.", identity],
    "LST_DETAIL_ROAMING": ["Einzelheiten zum Roaming in öffentlichen Netzen", "Sofern Roaming in öffentlichen Netzen konfiguriert ist, wird hier angegeben, für welche Netze/ für welche Nutzer/für welche Gebiete.", identity],
    "LST_EGPRUEF_DOK": ["EG-Prüfung TSI ZZS", "Eindeutige Nummer der EG-Erklärung gemäß den Formatvorgaben in 'Document about practical arrangements for transmitting interoperability'.", identity],
    "LST_EINH_RST_SHUNT": ["TSI-Konformität der Vorschriften über Kombinationen von RST-Merkmalen mit Einfluss auf die Kurzschlussimpedanz", "Angabe, ob die Vorschriften mit der TSI im Einklang stehen.", identity],     
    "LST_ETCS_INFILL_ZUGANG": ["ETCS-Infill-Funktion für Streckenzugang notwendig", "Angabe, ob Infill aus Sicherheitsgründen für den Zugang erforderlich ist.", identity],     
    "LST_ETCS_LEVEL_STOER": ["ETCS-Level für gestörten Betrieb", "ERTMS/ETCS-Level hinsichtlich der streckenseitigen Ausrüstung für eingeschränkten Betrieb.", identity],  
    "LST_ETCS_LEVEL_VERS": ["ETCS Level", "ERTMS/ETCS-Anwendungsstufe hinsichtlich der streckenseitigen Ausrüstung (Level1, Level2 oder ohne ETCS).", identity],  
    "LST_ETCS_NATIONAL": ["Paket 44 der nationalen ETCS-Anwendung implementiert", "Angabe, ob Daten für nationale Anwendungen zwischen Gleis und Zug übertragen werden.", identity],  
    "LST_ETCS_SOFTWARE_VERS": ["ETCS SRS Version", "Angabe der streckenseitig installierten ETCS-Baseline Version (2.3.0 d, 3.3.0, 3.4.0).", identity],  
    "LST_ETCS_STRECKE_INFILL": ["Streckenseitig installierte ETCS-Infill-Funktion", "Information zu installierter streckenseitiger Ausrüstung, die Infill-Informationen mittels einer Schleife oder GSM-R für Installationen des Level 1 übertragen kann.", identity],   
    "LST_FERRO_RADWERKSTOFF": ["Ferromagnetische Eigenschaften des Radwerkstoffs vorgeschrieben TSI-konform", "Angabe, ob die Vorschriften mit der TSI im Einklang stehen.", identity],
    "LST_FUNKSYS_KLASSE_B": ["Andere Funksysteme installiert", "Angabe, ob streckenseitig im Normalbetrieb andere Funksysteme installiert sind.", identity],
    "LST_GPRS": ["GPRS für ETCS", "Angabe, ob GPRS für ETCS verwendet werden kann.", identity],
    "LST_GPRS_ANWEND": ["GPRS-Anwendungsbereich", "Angabe des Bereichs, in dem GPRS für das ETCS verwendet werden kann", identity],
    "LST_GRUPPE_555": ["Verwendung der Gruppe 555", "Angabe, ob die Gruppe 555 verwendet wird.", identity],
    "LST_GSMR_VERSION": ["GSM-R Version", "Nummern der streckenseitig installierten FRS- und SRS-Versionen des GSM-R.", identity],
    "LST_KEIN_GSMR": ["Keine GSM-R-Abdeckung", "Angabe, ob eine GSM-R-Abdeckung besteht oder nicht.", identity],
    "LST_LZB": ["LZB", "Angabe, ob der Streckenabschnitt, mit dem Zugsicherungssystem LZB ausgerüstet ist und mit welcher Version.", identity],
    "LST_MAX_SAND": ["Maximaler Sandausstoß [g]", "Angabe des maximalen Wertes des auf dem Gleis akzeptierten Sandausstoßes für einen Zeitraum von 30s in Gramm (500g oder 800g).", str_to_float],
    "LST_MINDESTZAHL_GSMR": ["Mindestanzahl aktiver GSM-R-Modems an Bord für die Datenübertragung", "Für einen reibungslosen Zugbetrieb empfohlene Zahl der Modems für die ETCS-Datenübertragung. Dies betrifft Kommunikationssitzungen mit Hilfe der Streckenzentrale (RBC).", identity],
    "LST_MIN_BREMSLEIST": ["Maximal geforderter Bremsweg [m]", "Angabe des maximalen Bremswegs (in Metern) eines Zuges für die Streckenhöchstgeschwindigkeit.", str_to_float],
    "LST_M_VERSION": ["ETCS M_Version", "ETCS M_Version gemäß SRS 7.5.1.9", identity],
    "LST_NETZMERKMALE": ["Zusätzliche Angaben zu den Netzmerkmalen", "Zusätzliche Angaben zu den Netzmerkmalen oder entsprechendes Dokument, das beim Infrastrukturbetreiber erhältlich ist und von der ERA gespeichert wird, z.B.: Interferenzniveau, das zur Empfehlung einer zusätzlichen fahrzeugseitigen Sicherung führt.", identity],    
    "LST_OPTION_GSMR": ["Optionale GSM-R-Funktionen", "Einsatz optionaler GSM-R-Funktionen, die den Betrieb auf der Strecke verbessern können.", identity],
    "LST_PZB": ["PZB", "Angabe, ob der Streckenabschnitt, mit dem Zugsicherungssystem PZB ausgerüstet ist.", identity],
    "LST_RANGIER": [],
    "LST_ROAMING_NETZ": ["Roaming in öffentlichen Netzen vorhanden", "Roaming in öffentlichen Netzen vorhanden.", identity],
    "LST_ROAMING_VEREINB": ["GSM-R-Netze, für die eine Roaming-Vereinbarung vorliegt", "Liste der GSM-R-Netze, für die eine Roaming-Vereinbarung vorliegt.", identity],
    "LST_SAND_CHAR": ["Vorschriften zur Sand Charakteristik sind TSI-konform", "Angabe, ob die Vorschriften mit der TSI im Einklang stehen.", identity], 
    "LST_SPURKRANZ": ["Existenz von Vorschriften zur fahrzeugseitigen Spurkranzschmierung", "Angabe, ob Vorschriften für die Aktivierung oder Deaktivierung der Spurkranzschmierung vorhanden sind.", identity], 
    "LST_SYSTEMKOMP": ["ETCS-Systemkompatibilität", "ETCS-Anforderungen zum Nachweis der technischen Kompatibilität.", identity],
    "LST_TSI_KONF_ABST": ["TSI-konformer Höchstabstand zwischen zwei aufeinanderfolgenden Achsen", "Angabe, ob der erforderliche Abstand mit der TSI im Einklang steht.", identity],
    "LST_TSI_KONF_IMP": ["TSI-konforme Höchstimpedanz zwischen gegenüberliegenden Rädern eines Radsatzes", "Angabe, ob die Vorschriften mit der TSI im Einklang stehen.", identity],
    "LST_UEBERG_FUNKSYS": ["Übergänge zwischen verschiedenen Funksystemen vorhanden", "Angabe, ob zwischen verschiedenen Systemen während der Fahrt umgeschaltet werden kann", identity],
    "LST_UEBERG_ZUGSICH": ["Übergänge zwischen verschiedenen Zugsicherungs-, Zugsteuerungs- und Warnsystem vorhanden", "Angabe, ob während der Fahrt zwischen verschiedenen Funksystemen umgeschaltet und das Kommunikationssystem ausgeschaltet werden kann.", identity],
    "LST_UNTERDR_SAND": ["Unterdrücken des Sandens durch den Triebfahrzeugführer vorgeschrieben", "Angabe, ob der Triebfahrzeugführer nach den Anweisungen des Infrastrukturbetreibers über die Möglichkeit verfügen muss, die Sandstreuanlagen zu aktivieren und zu deaktivieren.", identity],
    "LST_VERBUND_BREMS": ["Einhaltung der TSI bei Vorschriften zur Nutzung von Verbundstoffbremsklötzen", "Angabe, ob die Vorschriften mit der TSI im Einklang stehen.", identity],
    "LST_VOR_ELE_MAG": ["Vorschriften für die von Fahrzeugen ausgesendeten Magnetfelder vorhanden und TSI konform", "Angabe, ob Vorschriften vorhanden sind und mit der TSI im Einklang stehen.", identity],
    "LST_VOR_METALL_FREI": ["Vorschriften zu metallfreiem Raum in der Radumgebung TSI-konform", "Angabe, ob die Vorschriften mit der TSI im Einklang stehen.", identity],
    "LST_VOR_METALL_MASSE": ["Vorschriften für Metallmasse von Fahrzeugen TSI-konform", "Angabe, ob die Vorschriften mit der TSI im Einklang stehen.", identity],
    "LST_VOR_STROMRUECK": ["Vorschriften für Grenzen der Oberschwingungen des Traktionsstroms vorhanden und TSI-konform", "Angabe, ob Vorschriften vorhanden sind und mit der TSI im Einklang stehen.", identity],
    "LST_ZHOE_ABST_FOLG_ACHS": ["Zulässiger Höchstabstand zwischen zwei aufeinanderfolgenden Achsen falls nicht TSI konform [mm]", "Angabe des zulässigen Höchstabstands zwischen zwei aufeinanderfolgenden Achsen in Millimetern, falls nicht TSI-konform.", str_to_float],
    "LST_ZHOE_IMPEDANZ": ["Zulässige Höchstimpedanz zwischen gegenüberliegenden Rädern eines Radsatzes falls nicht TSI-konform [Ohm]", "Wert der zulässigen Höchstimpedanz in Ohm, falls nicht TSI-konform.", str_to_float],
    "LST_ZHOE_LAENG_BUG": ["Zulässiger Höchstabstand zwischen Fahrzeugende und erster Achse [mm]", "Angabe des Höchstabstands zwischen Fahrzeugende und erster Achse in Millimetern für beide Enden (vorderes und hinteres Ende) eines Fahrzeuges oder Zuges.", str_to_float],
    "LST_ZMAX_HOEHE_RADKR": ["Maximal zulässige Höhe des Spurkranzes [mm]", "Angabe der maximal zulässigen Höhe des Radkranzes in Millimetern.", str_to_float],
    "LST_ZMIN_ACHSLAST": ["Zulässige Mindestachslast [t]", "Angabe der zulässigen Mindestachslast in Tonnen.", str_to_float],
    "LST_ZMIN_ACHSLAST_FAHRZ": ["Zulässige Mindestradsatzlast je Fahrzeugklasse [t]", "Angabe der zulässigen Mindestachslast in Tonnen je nach Fahrzeugklasse.", identity],
    "LST_ZMI_ABST_E_L_ACHS": ["Zulässiger Mindestabstand zwischen erster und letzter Achse [mm]", "Angabe des zulässigen Mindestabstands zwischen erster und letzter Achse in Millimetern.", str_to_float],
    "LST_ZMI_ABST_FOLG_ACHS": ["Zulässiger Mindestabstand zwischen zwei aufeinanderfolgenden Achsen [mm]", "Angabe des zulässigen Mindestabstands zwischen zwei aufeinanderfolgenden Achsen in Millimetern.", str_to_float],
    "LST_ZMI_BREITE_RADKR": ["Zulässige Mindestbreite des Radkranzes [mm]", "Angabe der zulässigen Mindestbreite des Radkranzes in Millimetern.", str_to_float],
    "LST_ZMI_DICK_RADKR": ["Zulässige Mindestdicke des Spurkranzes [mm]", "Angabe der zulässigen Mindestdicke des Radkranzes in Millimetern.", str_to_float],
    "LST_ZMI_DURCH_RAD": ["Zulässiger Mindestdurchmesser des Rades [mm]", "Angabe des zulässigen Mindestraddurchmessers des Rades in Millimetern.", str_to_float],
    "LST_ZMI_HOEHE_RADKR": ["Zulässige Mindesthöhe des Spurkranzes [mm]", "Angabe der zulässigen Mindesthöhe des Radkranzes in Millimetern.", str_to_float],
    "LST_ZUGFUNK_DATEN": ["Kompatibilität des Zugfunksystems (Daten)", "Funkanforderungen zum Nachweis der technischen Kompatibilität (Daten).", identity],
    "LST_ZUGFUNK_SPRACHE": ["Kompatibilität des Zugfunksystems (Sprache)", "Funkanforderungen zum Nachweis der technischen Kompatibilität (Sprache).", identity],
    "LST_ZUGINTEGRITAET": ["Fahrzeugseitige Bestätigung der Zugintegrität für Streckenzugang notwendig", "Angabe, ob eine fahrzeugseitige Bestätigung der Zugintegrität aus Sicherheitsgründen für den Zugang zur Strecke erforderlich ist.", identity],
    "LST_ZUGORTUNG": ["TSI-konforme Zugortungsanlagen/Gleisfreimeldeeinrichtungen vorhanden", "Angabe, ob eine vollständig mit der TSI ZZS konforme Zugortungsanlage/Gleisfreimeldeeinrichtung installiert ist.", identity],
    "LST_ZUSATZ_IM": ["Zusätzliche Angaben beim Infrastrukturbetreiber erhältlich", "Angabe, ob zusätzliche Angaben gemäß Nummer 4.2.2.6.2 Unternummer 2 des Anhangs der Durchführungsverordnung (EU) 2019/773 beim Infrastrukturbetreiber erhältlich sind.", identity],
    "LST_ZUSATZ_IM_DOK": ["Dokument des Infrastrukturbetreibers zur Bremsleistung", "Elektronisches Dokument, das vom Infrastrukturbetreiber zur Verfügung gestellt und von der ERA gespeichert wird, mit zusätzlichen Angaben gemäß Nummer 4.2.2.6.2 Unternummer 2 des Anhangs der Durchführungsverordnung (EU) 2019/773 die beim Infrastrukturbetreiber erhältlich sind.", identity],
    "LST_ZZS_CLASSB_STOER": ["Andere Zugsicherungs-, Zugsteuerungs- und Warnsysteme für gestörten Betrieb", "Angabe, ob andere Systeme als ETCS für eingeschränkten Betrieb vorhanden sind.", identity],
    "SEG_ID": [],
}   


### BETRIEBSSTELLEN

ISR_PROPERTIES_OPERATIONAL_POINT = {
    "ALG_BAHNSTEIGE_DET": [],
    "ALG_BAHNUEBERGAENGE_DET": [],
    "ALG_BRUECKE_DET": [],
    "ALG_BSTEIG_BEREICH_PLAN": [],
    "ALG_DBNETZ_STRECKE": [],
    "ALG_DETAILPLAN_DOK": [],
    "ALG_EG_PRUEF_TSI_ENE": [],
    "ALG_EG_PRUEF_TSI_INF": [],
    "ALG_EG_PRUEF_TSI_LST": [],
    "ALG_EG_PRUEF_UEBERBL": [],
    "ALG_GEO_LAGE": ["Geografische Lage der Betriebsstelle [WGS84 - EPSG:4326]", "Geografische Koordinaten in Dezimalgrad, normalerweise in Bezug auf einen Punkt in der Mitte des Empfangsgebäudes", str_to_lat_lon],
    "ALG_GLEISE_DET": [],
    "ALG_GSMR_RAFU": [],
    "ALG_MOBILIPLAN_DOK": [],
    "ALG_REGELBAHNST_HOEHEN": ["Bahnsteighöhen [mm]", "Die angegebenen Bahnsteighöhen sind Systemhöhen. Diese beinhalten auch Übergangsflächen zwischen verschiedenen Systemhöhen und beziehen sich immer auf die Soll-Gleislage. Die tatsächliche Bahnsteighöhe kann auf Grund der Ist-Gleislage und Instandhaltungstoleranzen von der Systemhöhe abweichen.", identity],
    "ALG_REISENDENAUFKOMM": ["Reisendenaufkommen", "Angabe des Reisendenaufkommens.", identity],
    "ALG_SERVICEEINRICHT": ["Serviceeinrichtung", "Übersicht der Serviceeinrichtungen in der Betriebsstelle.", identity],
    "ALG_SOEZ_DETAILS_STELLE": ["Streckenöffnungszeiten", "Link zur Anzeige der täglichen Streckenöffnungszeiten für das laufende Fahrplanjahr", identity],
    "ALG_STAAT": ["Staat", "Mitgliedstaat der europäischen Union (+UK +NO +CH).", identity],
    "ALG_STRECKE_DET": [],
    "ALG_TUNNEL_DET": [],
    "ALG_ZZS_BST": [],
    "BST_HS_DS_KZ": [],
    "BST_RL100": ["RL100", "Angabe der Abkürzung für Betriebsstellen nach Richtlinie 100.", identity],
    "BST_STELLENART": ["Betriebsstellenart", "Art der Einrichtung hinsichtlich der vorherrschenden betrieblichen Funktionen.", identity],
    "BST_STELLE_NAME": ["Betriebsstellen Name", "In der Regel auf die betreffende Ansiedlung (Stadt/Dorf) oder auf verkehrsbetriebliche Zwecke bezogene Bezeichnung.", identity],
    "BST_TAF_TAP_PC": ["TAF/TAP primary Code", "Für TAF/TAP entwickelter Primärcode (siehe auch https://crd.tsi-cc.eu/CRD/Login.action).", identity],
    "DET_GLEISNUTZLAENGEN": [],
    "DET_GLEISZUORDNUNG": [],
    "HAS_BSZ": [],
    "HAUPTLAGE": ["Hauptlage", "Teil der Hauptlage.", identity],
    "ID": ["Identifikatinsnummer", "Identifkitationsnummer im Infrastrukturregister.", identity],
    "JAHR": ["Jahr", "Angabe des Jahres.", identity],
    "LADE_ID": ["Lade ID", "Lade Identifkationsnummer im Infrastrukturregister.", identity],
    "LAGE_KM_I": ["Streckenlage (DB codiert)", "Lage der Betriebsstelle auf der zugeordneten Strecke als Kilometerierung.", str_to_int],
    "LAGE_KM_V": ["Streckenlage [km]", "Lage der Betriebsstelle auf der zugeordneten Strecke als Kilometerierung.", db_km_to_km],
    "STEL_ID": ["Stellen ID", "Stellen Identifkationsnummer im Infrastrukturregister.", identity],
    "STRNR": ["Strecken-Nr.", "Bezeichnung und Identifizierung für Eisenbahnstrecken in Deutschland.", identity],
}

""" Übersicht: Betriebsstellenarten
    Abzw
        Abzweigstelle
    Anst
        Anschlussstelle
    Awanst
        Ausweichanschlussstelle
    Bf
        Bahnhof
    Bft
        Bahnhofsteil
    Bk
        Blockstelle
    Bush
        Bushaltestelle
    Dkst
        Deckungsstelle
    Est
        Einsatzstelle für Zugpersonal
    Fwst
        Fernwirkstelle
    Gp
        Grenzpunkt
    Hp
        Haltepunkt
    LGr
        Landesgrenze
    LW
        Laufweg
    Museum
        Museumsbahnhof
    PDGr
        Produktionsdurchführungsgrenze
    RBGr
        Regionalbereichsgrenze
    Sbk
        Selbsttätige Blockstelle
    Schstr
        Schutzstrecke
    Slst
        Schiffslandestelle
    Sp
        Schaltposten
    Strw
        Streckenwechsel
    Stub
        Streckenübergang
    Tp
        Tarifpunkt
    Urw
        Umrichterwerk
    Uw
        Unterwerk
    Üst
        Überleitstelle
    Zes
        Zentralschaltstelle
    NE-*
        Nichtbundeseigene Eisenbahn
    vp-*
        verpachtet
"""


### STRECKENÜBERGÄNGE

ISR_PROPERTIES_JUNCTION = {
    "ALG_DBNETZ_STRECKE": [],
    "BST_STELLENART": ["Betriebsstellenart", "Art der Einrichtung hinsichtlich der vorherrschenden betrieblichen Funktionen.", identity],
    "BST_STELLE_NAME": ["Betriebsstellen Name", "In der Regel auf die betreffende Ansiedlung (Stadt/Dorf) oder auf verkehrsbetriebliche Zwecke bezogene Bezeichnung.", identity],
    "BST_TAF_TAP_PC": ["TAF/TAP primary Code", "Für TAF/TAP entwickelter Primärcode (siehe auch https://crd.tsi-cc.eu/CRD/Login.action).", identity],
    "ID": ["Identifikatinsnummer", "Identifkitationsnummer im Infrastrukturregister.", identity],
    "JAHR": ["Jahr", "Angabe des Jahres.", identity],
    "LADE_ID": ["Lade ID", "Lade Identifkationsnummer im Infrastrukturregister.", identity],
    "REF_RL100": ["Referenzierte RL100", "Angabe der Abkürzung der dem Streckenübergang zugeordneten Betriebsstelle nach Richtlinie 100.", identity],
    "STEL_ID": ["Stellen ID", "Stellen Identifkationsnummer im Infrastrukturregister.", identity],
    "STRECKE1": ["Strecken-Nr. 1", "Die erste Streckennummer, die dem Streckenübergang zugeordnet ist.", identity],
    "STRECKE2": ["Strecken-Nr. 2", "Die zweite Streckennummer, die dem Streckenübergang zugeordnet ist.", identity],
}


### TUNNEL

ISR_PROPERTIES_TUNNEL = {
    "ALG_BESCHR_DOC": ["Tunneldetails", "Dokument mit Details zum Tunnel.", identity],
    "ALG_DBNETZ_STRECKE": [],
    "ALG_DIESEL_ERL": ["Diesel- oder andere Verbrennungsantriebe zulässig", "Angabe, ob der Einsatz von Diesel- oder anderen Verbrennungsantrieben im Tunnel erlaubt ist.", identity],
    "ALG_EG_PRUEF_TUNN": ["EG-Prüferklärung für Tunnel (SRT)", "Eindeutige Nummer der EG-Erklärung gemäß den Formatvorgaben in ?Document about practical arrangements for transmitting interoperability documents'.", identity],
    "ALG_ERF_BRANDKAT_FZG": ["Erforderliche Brandkategorie von Fahrzeugen", "Kategorisierung, wie ein Reisezug bei einem Brand im Zug für einen definierten Zeitraum weiter betrieben werden kann.", identity],
    "ALG_ERF_BRANDKAT_NAT": ["Erforderliche nationale Brandkategorie", "Kategorisierung, wie ein Reisezug bei einem Brand im Zug für einen definierten Zeitraum gemäß etwaigen nationalen Vorschriften weiter betrieben werden kann.", identity],
    "ALG_IM_CODE": ["Infrastrukturbetreiber Code", "Numerische Codierung des Infrastrukturbetreibers gemäß UIC-Liste (verfügbar unter http://www.uic.org -> Company Codes) z. B. 0080 für die DB Netz AG.", identity],
    "ALG_LICHT_QUERSCHN": ["Lichter Querschnitt [m^2]", "Kleinster tatsächlicher Querschnitt des Tunnels in Quadratmeter.", str_to_float],
    "ALG_NOTFALLPLAN_VORH": ["Notfallplan vorhanden", "Angabe, ob eine Notfallplan vorhanden ist.", identity],
    "ALG_TSI_KONF": ["Konformität des Tunnels mit der TSI INF", "Konformität des Tunnels mit der TSI INF bei zulässiger Höchstgeschwindigkeit.", identity],
    "ALG_TUNNELANFANG": ["Tunnelanfang", "Geografische Koordinaten in Dezimalgrad am Beginn eines Tunnels.", str_to_lat_lon],
    "ALG_TUNNELART": ["Tunnelart", "Angabe, ob der Tunnel ein- oder mehrgleisig ist.", identity],
    "ALG_TUNNELENDE": ["Tunnelende", "Geografische Koordinaten in Dezimalgrad am Ende eines Tunnels.", str_to_lat_lon],
    "ALG_TUNNELLAENGE": ["Tunnellänge [m]", "Länge des Tunnels in Metern von der Tunneleinfahrt bis zur Tunnelausfahrt, (siehe auch Anlage 3 Längenabhängige Darstellung der Tunnel unter http://fahrweg.dbnetze.com/fahrweg-de/nutzungsbedingungen/infrastrukturregister/grundsaetze.html).", str_to_float],
    "ALG_TUNNELNAME": ["Name des Tunnels", "Angabe des Tunnelnamens.", identity],
    "ALG_TUNN_DETAILS": ["Tunneldetails", "Dokument mit Details zum Tunnel.", identity],
    "ALG_TUNN_NOTAUS_KZ": ["Kennzeichnung von Notausgängen im Tunnel", "Dokument zur Beschreibung der Notausgänge in Tunneln.", identity],
    "BAUWERKSID": ["Bauwerksidentifikationsnummer", "Identifikationsnummer des Bauwerks.", identity],
    "DET_STR_NR": [],
    "ID": ["Identifikatinsnummer", "Identifkitationsnummer im Infrastrukturregister.", identity],
    "JAHR": ["Jahr", "Angabe des Jahres.", identity],
    "KMBIS_I": ["Kilometer (Tunnelende) - DB Codierung", "Angaben der Kilometrierung (metergenau) des Tunnelendes (DB Codierung).", db_km_alt_to_km],
    "KMVON_I": ["Kilometer (Tunnelanfang) - DB Codierung", "Angaben der Kilometrierung (metergenau) des Tunnelanfangs (DB Codierung).", db_km_alt_to_km],
    "LADE_ID": ["Lade ID", "Lade Identifkationsnummer im Infrastrukturregister.", identity],
    "STEL_ID": ["Stellen ID", "Stellen Identifkationsnummer im Infrastrukturregister.", identity],
    "STRNR": ["Strecken-Nr.", "Bezeichnung und Identifizierung für die Strecke, die dem Tunnel zugeordnet ist.", identity],
    "TUNN_ID": ["Tunnelidentifikationsnummer", "Identifikationsnummer des Tunnels.", identity],
}


##### OSM - OpenStreetMap


# fmt: on
