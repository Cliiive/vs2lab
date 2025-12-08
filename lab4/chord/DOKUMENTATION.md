# Labor 4 - Chord DHT: Rekursive Namensauflösung

**Implementierung der rekursiven LOOKUP-Operation im Chord Peer-to-Peer System**

---

## Übersicht

Diese Implementierung erweitert das grundlegende Chord DHT-System um eine **rekursive Namensauflösung**. Anstatt dass ein Client iterativ LOOKUP-Anfragen an mehrere Knoten senden muss, leiten die Knoten die Anfrage nun automatisch rekursiv weiter, bis der zuständige Knoten gefunden wird. Dieser sendet das Ergebnis dann direkt an den ursprünglichen Client zurück.

## Systemarchitektur

### Chord Ring
- Knoten sind in einem Ring angeordnet (zirkularer Adressraum)
- Jeder Knoten verwaltet eine **Finger-Tabelle** mit Zeigern zu anderen Knoten in exponentiellen Abständen
- Die Finger-Tabelle ermöglicht effizientes Routing von LOOKUP-Anfragen in O(log N) Zeit

### Kommunikation
- Alle Kommunikation erfolgt über **lab_channel** (Redis-basierte Nachrichtenwarteschlange)
- Nachrichten werden als Tupel mit Nachrichtentypen aus `constChord.py` gesendet:
  - `LOOKUP_REQ = '1'`: Lookup-Anfrage für einen Schlüssel
  - `LOOKUP_REP = '2'`: Lookup-Antwort mit zuständigem Knoten
  - `JOIN = '3'`: Knoten tritt dem Ring bei
  - `LEAVE = '4'`: Knoten verlässt den Ring
  - `STOP = '6'`: Shutdown-Signal

## Implementierungsdetails

### 1. Rekursives LOOKUP in ChordNode

**Datei:** `chordnode.py`, Zeilen 149-174

Wenn ein Knoten eine `LOOKUP_REQ` für einen Schlüssel empfängt:

```python
if request[0] == constChord.LOOKUP_REQ:
    key = int(request[1])
    # Original-Sender extrahieren (für rekursive Weiterleitung)
    original_sender = str(request[2]) if len(request) > 2 else sender
    
    # Nächsten Hop mittels lokaler Finger-Tabelle finden
    next_id = self.local_successor_node(key)
    
    if next_id == self.node_id:
        # BASISFALL: Dieser Knoten ist zuständig
        # Sende Ergebnis direkt an den ursprünglichen Sender
        self.channel.send_to([original_sender], (constChord.LOOKUP_REP, self.node_id))
    else:
        # REKURSIVER FALL: Weiterleitung an den nächsten Hop
        # Original-Sender wird mitgeführt, damit der finale Knoten weiß,
        # wohin die Antwort gesendet werden soll
        self.channel.send_to([str(next_id)], (constChord.LOOKUP_REQ, key, original_sender))
```

**Kernpunkte:**

1. **Basisfall**: Wenn dieser Knoten zuständig ist (`next_id == self.node_id`), wird das Ergebnis direkt an den ursprünglichen Sender zurückgesendet
2. **Rekursiver Fall**: Die Anfrage wird an den nächsten Hop weitergeleitet, wobei die ID des ursprünglichen Senders übergeben wird
3. **Tracking des Original-Senders**: Das dritte Element des LOOKUP_REQ-Tupels (`original_sender`) verfolgt den ursprünglichen Anfragenden über mehrere Hops hinweg

### Funktionsweise

**Beispiel: 4-Knoten-Ring (Knoten 1, 5, 10, 15), Suche nach Schlüssel 8**

1. **Client → Knoten 1:** LOOKUP(8)
2. **Logik von Knoten 1:** 
   - `local_successor_node(8)` liefert Knoten 5 (nächster Hop in Finger-Tabelle)
   - Knoten 5 ≠ Knoten 1, daher rekursive Weiterleitung
   - Sende `LOOKUP_REQ(8, client)` an Knoten 5
3. **Logik von Knoten 5:**
   - `local_successor_node(8)` liefert Knoten 10 (nächster Hop)
   - Knoten 10 ≠ Knoten 5, daher rekursive Weiterleitung
   - Sende `LOOKUP_REQ(8, client)` an Knoten 10
4. **Logik von Knoten 10:**
   - `local_successor_node(8)` liefert Knoten 10 (sich selbst)
   - Basisfall erreicht! Schlüssel 8 gehört zu Knoten 10
   - Sende `LOOKUP_REP(10)` direkt an Client
5. **Client empfängt:** LOOKUP_REP mit Knoten 10 als zuständigem Knoten

### 2. DummyChordClient Implementierung

**Datei:** `doit.py`, Zeilen 20-67

Der Client führt nun tatsächliche Lookups durch, anstatt nur einen Platzhalter auszugeben:

```python
def run(self):
    nodes_list = sorted([int(n) for n in nodes])
    
    # Führe 5 Lookups durch
    for lookup_count in range(5):
        # Zufälliger Schlüssel im gültigen Bereich
        key = random.randint(0, self.channel.MAXPROC - 1)
        
        # Zufälliger Startknoten
        start_node = random.choice(nodes_list)
        
        # Sende LOOKUP-Anfrage
        self.channel.send_to([str(start_node)], (constChord.LOOKUP_REQ, key))
        
        # Warte auf Antwort
        message = self.channel.receive_from_any()
        if message[1][0] == constChord.LOOKUP_REP:
            responsible = message[1][1]
            print(f"Schlüssel {key:04n} → Knoten {responsible:04n}")
```

**Funktionen:**
- Führt 5 zufällige Lookups zur Demonstration durch
- Zeigt den Verlauf vom zufälligen Schlüssel zum zuständigen Knoten
- Die gesamte Komplexität der Traversierung mehrerer Knoten wird durch Rekursion verborgen

## Vorteile des rekursiven Ansatzes

| Aspekt | Iterativ | Rekursiv |
|--------|----------|----------|
| **Client-Code** | Komplex (verwaltet mehrere Anfragen) | Einfach (einzelne Anfrage) |
| **Latenz** | Gleich (gleiche Anzahl Hops) | Gleich (gleiche Anzahl Hops) |
| **Implementierung** | Fehleranfälliger | Klarere Logik |
| **Fehlerbehandlung** | Einfacher, fehlgeschlagene Hops zu wiederholen | Schwieriger, Fehler in der Kette zu behandeln |

## Nachrichtenfluss Beispiel

Für ein 3-Hop-Lookup:

```
Client              Knoten A            Knoten B            Knoten C
  |                     |                   |                   |
  +--LOOKUP_REQ(k)----> |                   |                   |
  |                     +--LOOKUP_REQ(k)---> |                   |
  |                     |                   +--LOOKUP_REQ(k)----> |
  |                     |                   |              (Gefunden!)
  |                     |                   |                   |
  | <-----------------LOOKUP_REP(C)----------------------------- +
  |                     |                   |                   |
```

**Hinweis:** Die rekursive Implementierung sendet die Antwort direkt vom zuständigen Knoten zum ursprünglichen Client (dargestellt durch den direkten Pfeil), nicht über Zwischenknoten.

## Ausgabe-Erklärung

### Beispiel-Ausgabe
```
[CLIENT] LOOKUP 0063 starting from node 0061
Node 0061 received LOOKUP 0063 from 0000.
Node 0061 forwarding LOOKUP 0063 to 0063.
Node 0063 is responsible for key 0063, replying to 0000.
[CLIENT] Key 0063 is handled by node 0063
```

**Bedeutung:**
- Client (ID 0000) sucht nach Schlüssel **63**
- Startet bei Knoten **61**
- Knoten 61 prüft Finger-Tabelle → leitet an Knoten **63** weiter
- Knoten 63 ist zuständig → antwortet **direkt an Client 0000**
- **Hops:** Client → 61 → 63 → Client (2 Hops)

### Finger-Tabellen

```
FT[0011]: ['0004', '0030', '0030', '0030', '0030', '0030', '0053']
```

**Bedeutung:**
- **Index 0**: Vorgänger = Knoten **4** (Knoten vor 11 im Ring)
- **Index 1-6**: Nachfolger in exponentiellen Abständen

**Finger-Tabellen-Formel:**
Für Knoten `n` zeigt Finger `i` auf den ersten Knoten ≥ `(n + 2^(i-1)) mod MAXPROC`

**Beispiel für Knoten 11 (bei 6-Bit Adressraum = 64 Adressen):**
- Finger[1]: Nachfolger von (11 + 2^0) = 12 → **30**
- Finger[2]: Nachfolger von (11 + 2^1) = 13 → **30**
- Finger[3]: Nachfolger von (11 + 2^2) = 15 → **30**
- Finger[4]: Nachfolger von (11 + 2^3) = 19 → **30**
- Finger[5]: Nachfolger von (11 + 2^4) = 27 → **30**
- Finger[6]: Nachfolger von (11 + 2^5) = 43 → **53**

## Ausführung

### Voraussetzungen

**Redis-Server starten:**
```bash
redis-server --daemonize yes
```

### Chord-System ausführen

**Standard-Ausführung (6 Bit Adressraum, 8 Knoten):**
```bash
cd /workspaces/vs2lab/lab4/chord
pipenv run python doit.py
```

**Benutzerdefinierte Konfiguration:**
```bash
pipenv run python doit.py <m> <n>
```
- `m` = Anzahl der Bits für Adressraum (Ringgröße = 2^m)
- `n` = Anzahl der Knoten im Ring

**Beispiele:**
```bash
# Kleiner Ring: 4 Bits (0-15 Adressen), 4 Knoten
pipenv run python doit.py 4 4

# Mittlerer Ring: 5 Bits (0-31 Adressen), 6 Knoten  
pipenv run python doit.py 5 6

# Großer Ring: 8 Bits (0-255 Adressen), 16 Knoten
pipenv run python doit.py 8 16
```

### Erwartete Ausgabe

Die Ausgabe zeigt:
1. Knoten treten bei und werden bereit
2. Client führt 5 zufällige Lookups durch mit:
   - Welcher Schlüssel gesucht wird
   - Welcher Knoten zuerst angefragt wird
   - Multi-Hop-Weiterleitung durch den Ring
   - Finaler zuständiger Knoten für jeden Schlüssel
3. Finger-Tabellen werden am Ende ausgegeben

## Behandelte Sonderfälle

1. **Ring mit einem Knoten:** Schlüssel geht sofort an diesen Knoten
2. **Schlüssel umläuft Ring:** `in_between()` behandelt zirkulare Arithmetik
3. **Tote Knoten:** Sanity-Check entfernt tote Knoten aus bekannter Liste
4. **Finger-Tabellen-Lücken:** Fällt zurück auf letzten bekannten Finger-Tabellen-Eintrag

## Testergebnisse

✅ **4-Knoten-Ring (4 Bits):** Alle Lookups sofort abgeschlossen  
✅ **8-Knoten-Ring (6 Bits):** Multi-Hop-Ketten (bis zu 4 Hops) korrekt aufgelöst  
✅ **Rekursive Weiterleitung:** Funktioniert einwandfrei  
✅ **Keine Synchronisationsprobleme** oder Nachrichtenverlust

## Konzepte aus der Vorlesung

| Konzept | Implementierung |
|---------|-----------------|
| **DHT (Distributed Hash Table)** | Chord-Ring mit verteilter Schlüsselverwaltung |
| **Konsistentes Hashing** | Schlüssel und Knoten im gleichen Adressraum |
| **Finger-Tabellen** | Logarithmisches Routing O(log N) |
| **Rekursive Namensauflösung** | Knoten leiten Anfragen automatisch weiter |
| **Ringtopologie** | Zirkulare Anordnung der Knoten |
| **Prozess-Migration** | Multiprocessing mit Spawn für Plattformunabhängigkeit |

## Referenzen

- Stoica et al., "Chord: A Scalable Peer-to-peer Lookup Service for Internet Applications" (2003)
- Das ursprüngliche Paper verwendet iteratives Lookup; diese Implementierung nutzt rekursives Lookup für mehr Einfachheit
- Labor 4 README: `/workspaces/vs2lab/lab4/README.md`
