# Návrh prototypu znalostního grafu pro historické dokumenty

> **Diplomová práce:** Extrakce faktů a znalostních grafů z dokumentů  
> **Stav:** Návrh architektury a demonstrační příklad (nikoli hotová implementace)  
> **Navazuje na:** `knowledge_graphs_analysis.md`

## 1. Cíl

Navrhnout první implementovatelný systém, který z historického dokumentu extrahuje **entity, události, vztahy a zdrojové důkazy** a ukládá je do znalostního grafu. Graf má umožnit propojovat informace z více dokumentů, dotazovat se na historické vztahy, vizualizovat události a později sloužit jako podklad pro GraphRAG.

Pro první prototyp se doporučuje **událostně orientovaný Property Graph**, jehož vybrané typy uzlů a hran jsou **mapovány na ontologii CIDOC CRM**. Nejde automaticky o plně kompatibilní implementaci celého CIDOC CRM; rozsah mapování a případné odchylky je nutné dokumentovat.

## 2. Doporučené technologie a jejich role

| Technologie / nástroj | Úloha v řešení | Poznámka |
|---|---|---|
| **Python** | Orchestrace extrakce, normalizace a importu | Hlavní implementační jazyk |
| **LLM se strukturovaným výstupem** | Extrakce osob, míst, vztahů, událostí a důkazů | Konkrétní model je vhodné experimentálně porovnat |
| **JSON** | Přenosový a archivní formát výstupu extrakce | JSON není sám o sobě znalostním grafem ani ontologií |
| **JSON Schema / Pydantic** | Kontrola struktury a datových typů | Sémantické chyby je nutné validovat zvlášť |
| **CIDOC CRM (vybraná podmnožina)** | Slovník a význam tříd a vztahů historických událostí | Pro začátek použít stabilní oficiální verzi 7.1.3 |
| **Property Graph** | Reprezentace uzlů, hran a atributů | Datový model, nikoli konkrétní databáze |
| **Neo4j** | Perzistence, dotazování a vizualizace grafu | Nativně ukládá Property Graph, ne vstupní JSON jako graf |
| **Cypher** | Grafové dotazy | Včetně víceúrovňového procházení vztahů |
| **Neo4j Python driver (`neo4j`)** | Bezpečný parametrizovaný import z Pythonu | Preferovat oproti přímému generování Cypheru pomocí LLM |
| **Docker Compose** | Lokální provoz databáze a pipeline | Pro reprodukovatelné experimenty |
| **RDF / JSON-LD, `rdflib`** | Volitelný budoucí export a interoperabilita | Není potřeba v první iteraci |

### Proč tato kombinace?

- **JSON** usnadňuje získání a validaci výstupu LLM.
- **CIDOC CRM** poskytuje doménově smysluplné pojmy, zejména pro události a čas.
- **Property Graph + Neo4j** umožňuje pohodlně ukládat a procházet konkrétní vztahy.
- **Oddělení vrstev** umožní nahradit LLM, ontologické mapování nebo úložiště bez přepisování celé extrakce.

### Celková architektura

```text
Historický dokument (text / OCR)
              |
              v
      Předzpracování textu
              |
              v
       LLM: extrakce faktů
              |
              v
       JSON: entities/events
              |
              v
      Pydantic / JSON Schema
              |
              v
   Normalizace + Entity Resolution
              |
              v
     Mapování na CIDOC CRM
              |
              v
    Property Graph -> Neo4j
              |
       +------+------+
       |             |
       v             v
     Cypher      Vizualizace
       |             |
       +------v------+
         GraphRAG (později)
```

> **Praktické pravidlo:** LLM generuje **data**, nikoli databázové příkazy. Kontrolu, mapování a zápis do Neo4j obstarává aplikace.

---

## 3. Ukázkový historický dokument

Pro demonstrační příklad použijeme **vymyšlený** historický zápis:

> „Roku 1521 koupil Matěj Kovář dům v Brně od Václava Svobody.“

Cílem je reprezentovat nejen informaci o kupujícím, ale také prodávajícího, převáděný objekt, čas a původ tvrzení.

### 3.1 Co lze extrahovat?

| Typ | Hodnota |
|---|---|
| Osoba – kupující | Matěj Kovář |
| Osoba – prodávající | Václav Svoboda |
| Fyzický objekt | Dům v Brně (v tuto chvíli pouze nejednoznačný popis) |
| Událost | Převod vlastnického práva / koupě |
| Čas | Rok 1521 (bez znalosti dne a měsíce) |
| Evidence | Přesná citovaná věta |
| Dokument | Identifikátor vstupního dokumentu |

### 3.2 Příklad výstupu LLM jako JSON

Toto je **vlastní meziformát aplikace**, nikoli přímo RDF, JSON-LD ani formální serializace CIDOC CRM.

```json
{
  "document_id": "doc_001",
  "entities": [
    {"local_id": "ent_1", "type": "Person", "label": "Matěj Kovář"},
    {"local_id": "ent_2", "type": "Person", "label": "Václav Svoboda"},
    {"local_id": "ent_3", "type": "PhysicalThing", "label": "dům v Brně"}
  ],
  "events": [
    {
      "local_id": "event_1",
      "type": "Acquisition",
      "acquirer": "ent_1",
      "former_owner": "ent_2",
      "transferred_object": "ent_3",
      "time": {"original_text": "Roku 1521", "year": 1521, "precision": "year"},
      "evidence": {
        "text": "Roku 1521 koupil Matěj Kovář dům v Brně od Václava Svobody."
      }
    }
  ]
}
```

Poznámky:

- `local_id` platí jen **uvnitř jednoho zpracování**. Není to identifikátor osoby napříč archivem.
- Identifikátor domu **nesmí být automaticky sjednocen** s jinými záznamy typu „dům v Brně“; k tomu chybí dostatek údajů.
- `year: 1521` neznačí přesné datum. Výstup zachovává i původní formulaci.
- Skutečné textové offsety doplnit až po ověření proti uloženému vstupu (nepřijímat nekontrolované offsety vymyšlené LLM).

---

## 4. Mapování na CIDOC CRM

Základní mapování historické koupě lze postavit na těchto třídách a vlastnostech:

| Informace | CIDOC CRM | Význam |
|---|---|---|
| Matěj Kovář | **E21 Person** | Konkrétní osoba, zároveň podtyp E39 Actor |
| Václav Svoboda | **E21 Person** | Konkrétní osoba |
| Dům | **E18 Physical Thing** | Fyzický objekt; detailnější klasifikace až dle potřeby |
| Převod vlastnictví | **E8 Acquisition** | Událost převodu vlastnického práva |
| Příjemce práva | **P22 transferred title to** | Událost → nabyvatel |
| Původní vlastník | **P23 transferred title from** | Událost → převodce |
| Převáděná věc | **P24 transferred title of** | Událost → fyzická věc |
| Časové vymezení | **P4 has time-span** → **E52 Time-Span** | Čas události |

**Význam směru vztahů:** `E8 Acquisition -[P22]-> kupující`, nikoli opačně. `P23` směřuje od události k prodávajícímu a `P24` od události k převáděnému objektu.

```text
                         [E8 Acquisition]
                         Koupě domu, 1521
                         /     |      |      \
                        /      |      |       \
                      P22     P23    P24      P4
                       |       |      |        |
                       v       v      v        v
                   Matěj    Václav   Dům    [E52 Time-Span]
                   Kovář    Svoboda  v Brně   rok 1521
                  [E21]     [E21]    [E18]
```

**Provenance:** Na událost navíc navážeme vlastní aplikační uzly `Evidence` a `Document` (například `SUPPORTED_BY` a `FOUND_IN`). Tyto názvy **nejsou vlastnosti CIDOC CRM**; jde o záměrně oddělenou aplikační vrstvu. V budoucnu je lze mapovat na standardizovanější model původu tvrzení.

### Proč je uzel události lepší než jediná hrana?

Zápis `Matěj --BOUGHT--> Dům` neobsahuje informaci o prodávajícím, čase a dalších účastnících. Samostatný uzel události umožňuje více účastníků, čas, místo i několik různých zdrojových tvrzení. Pro historické dokumenty je proto vhodným výchozím modelem.

---

## 5. Jak bude graf vypadat v Neo4j?

Použijeme vlastní, čitelné názvy Neo4j labelů a hran a explicitně zaznamenáme jejich mapování na CIDOC CRM.

```text
(:Person {id, name, crmClass: "E21_Person"})
(:PhysicalThing {id, label, crmClass: "E18_Physical_Thing"})
(:Acquisition {id, crmClass: "E8_Acquisition"})
(:TimeSpan {id, year, precision, originalText, crmClass: "E52_Time-Span"})
(:Document {id})
(:Evidence {id, text})

(:Acquisition)-[:TRANSFERRED_TITLE_TO]->(:Person)       // CIDOC CRM P22
(:Acquisition)-[:TRANSFERRED_TITLE_FROM]->(:Person)     // CIDOC CRM P23
(:Acquisition)-[:TRANSFERRED_TITLE_OF]->(:PhysicalThing) // CIDOC CRM P24
(:Acquisition)-[:HAS_TIME_SPAN]->(:TimeSpan)             // CIDOC CRM P4
(:Acquisition)-[:SUPPORTED_BY]->(:Evidence)             // vlastní aplikace
(:Evidence)-[:FOUND_IN]->(:Document)                    // vlastní aplikace
```

### 5.1 Jednorázové vytvoření testovacího grafu (Cypher)

Následující příklad je **spustitelná ukázka pro jeden dokument**. Pro skutečný import je nutná správa stabilních ID, deduplikace a transakční zpracování.

```cypher
MERGE (buyer:Person {id: 'person_001'})
SET buyer.name = 'Matěj Kovář', buyer.crmClass = 'E21_Person'
MERGE (seller:Person {id: 'person_002'})
SET seller.name = 'Václav Svoboda', seller.crmClass = 'E21_Person'
MERGE (house:PhysicalThing {id: 'thing_001'})
SET house.label = 'dům v Brně', house.crmClass = 'E18_Physical_Thing'
MERGE (event:Acquisition {id: 'event_001'})
SET event.crmClass = 'E8_Acquisition'
MERGE (time:TimeSpan {id: 'time_001'})
SET time.year = 1521, time.precision = 'year', time.originalText = 'Roku 1521', time.crmClass = 'E52_Time-Span'
MERGE (doc:Document {id: 'doc_001'})
MERGE (evidence:Evidence {id: 'evidence_001'})
SET evidence.text = 'Roku 1521 koupil Matěj Kovář dům v Brně od Václava Svobody.'
MERGE (event)-[:TRANSFERRED_TITLE_TO]->(buyer)
MERGE (event)-[:TRANSFERRED_TITLE_FROM]->(seller)
MERGE (event)-[:TRANSFERRED_TITLE_OF]->(house)
MERGE (event)-[:HAS_TIME_SPAN]->(time)
MERGE (event)-[:SUPPORTED_BY]->(evidence)
MERGE (evidence)-[:FOUND_IN]->(doc);
```

Pro reálná data doporučeno zavést unikátní omezení na stabilní `id` pro každý typ uzlu a provádět import parametrizovanými dotazy přes Python driver.

### 5.2 Příklad dotazu

**„Jaký objekt získal Matěj Kovář v roce 1521 a ze kterého dokumentu to víme?“**

```cypher
MATCH (buyer:Person {id: 'person_001'})<-[:TRANSFERRED_TITLE_TO]-(event:Acquisition)
MATCH (event)-[:TRANSFERRED_TITLE_OF]->(object:PhysicalThing)
MATCH (event)-[:HAS_TIME_SPAN]->(time:TimeSpan)
MATCH (event)-[:SUPPORTED_BY]->(evidence:Evidence)-[:FOUND_IN]->(doc:Document)
WHERE time.year = 1521
RETURN buyer.name AS kupec, object.label AS predmet,
       doc.id AS dokument, evidence.text AS dukaz;
```

Očekávaný výsledek:

| kupec | predmet | dokument | dukaz |
|---|---|---|---|
| Matěj Kovář | dům v Brně | doc_001 | Roku 1521 koupil Matěj Kovář dům v Brně od Václava Svobody. |

---

## 6. Co se nesmí podcenit

### 6.1 Entity Resolution

`Matěj Kovář`, `Matěj K.`, `Matthias Kowar` mohou být označení téže osoby, ale **nesmějí být sloučena jen proto, že se podobají**. Je třeba vyhodnocovat kontext, dobu, místo a další důkazy. Lokální ID od LLM je nutné převést na stabilní ID v databázi; nejasné případy ponechat oddělené či označené k revizi.

### 6.2 Zdroj každého tvrzení

Jeden fakt může být podpořen více dokumenty a dokumenty si mohou odporovat. Neuchovávat jen „co graf tvrdí“, ale také **kdo/co to tvrdí, na základě jaké textové pasáže a zda byl údaj ověřen**. Později lze přejít od vazby `event -> Evidence` k samostatným uzlům tvrzení s nezávislými důkazy.

### 6.3 Čas a nejistota

„Roku 1521“ není konkrétní den a „kolem roku 1521“ není přesně rok 1521. Zachovávat originální textové vyjádření, časovou přesnost a případný interval. Pokud dokument nespecifikuje datum ukončení vlastnictví, neodvozovat ho bez důkazu.

### 6.4 Validace

JSON Schema/Pydantic ověří například existenci požadovaných polí, **nikoli pravdivost historického tvrzení**. Dále je třeba kontrolovat odkazy na entity, dovolené typy vztahů, směr hran, existenci důkazu v textu a případné rozpory s jinými zdroji.

### 6.5 CIDOC CRM versus vlastní model

Prototyp nemusí implementovat celou ontologii. Připravit tabulku mapování `aplikační typ -> CIDOC CRM URI`, seznam zjednodušení a testovací příklady. Přímé použití CIDOC CRM v Neo4j nedává automaticky RDF inferenci, OWL validaci ani standardizovaný export.

---

## 7. Etapy implementace

| Pořadí | Úkol | Ověřitelný výstup |
|---:|---|---|
| 1 | Připravit 5–10 krátkých testovacích dokumentů a ručně označit fakta | Malý referenční dataset |
| 2 | Definovat meziformát JSON a validační model Pydantic | Validní a nevalidní testovací příklady |
| 3 | Implementovat baseline LLM → JSON | První extrahované entity a události |
| 4 | Vytvořit import do Neo4j a základní Cypher dotazy | Zobrazení jednoho propojeného grafu |
| 5 | Doplnit provenance a čas | Každý testovací fakt lze ověřit ve zdroji |
| 6 | Zavést základní Entity Resolution | Identita napříč více dokumenty |
| 7 | Mapovat vybrané koncepty CIDOC CRM | Dokumentované mapování tříd a vztahů |
| 8 | Porovnat přímé vztahy a událostní model | Vyhodnocení výhod a složitosti |
| 9 | Měřit precision / recall / F1 a chyby spojování | Reprodukovatelná evaluace |
| 10 | Otestovat grafové dotazy, případně GraphRAG | Ukázkové scénáře nad více dokumenty |

**Doporučení:** Nezačínat všemi třídami CIDOC CRM. Pro první funkční ukázku stačí `Person`, `PhysicalThing`, `Acquisition`, `TimeSpan`, `Document`, `Evidence` a několik typů vztahů.

## 8. Otevřené návrhové otázky

1. Budou základní jednotkou grafu **události**, **tvrzení**, nebo obojí?
2. Jak oddělit *zmínku v dokumentu* od *skutečné historické entity*?
3. Jak modelovat více zdrojů pro jeden fakt a vzájemně rozporná tvrzení?
4. Jak ukládat nejistá data a přibližné datování?
5. Bude potřeba standardní RDF/JSON-LD export, nebo pro experiment stačí Cypher?
6. Jak vyhodnotit přínos složitějšího modelu oproti jednoduchému `Person -[BOUGHT]-> Thing`?

## 9. Shrnutí rozhodnutí

**První prototyp:**

```text
Python + LLM -> JSON -> Pydantic -> Entity Resolution
                                   |
                                   v
                    CIDOC CRM (vybraná podmnožina)
                                   |
                                   v
                        Property Graph (Neo4j)
                                   |
                                   v
                     Cypher / vizualizace / později RAG
```

**Proč:** Dobře odděluje extrakci od modelování a ukládání, umožňuje postupné zpřesňování historické sémantiky a poskytuje prostor pro porovnání jednodušších i bohatších reprezentací. JSON slouží jako **meziformát**; při importu se jeho objekty převádějí na **uzly, hrany a vlastnosti** Neo4j.

Tento návrh je **výchozí hypotéza architektury**, nikoli zatím experimentálně ověřená nejlepší volba. Výběr RDF vs. Property Graph a rozsah CIDOC CRM je vhodné potvrdit podle požadavků na interoperabilitu, dotazování, provenance a výsledků pilotních experimentů.

---

## 10. Reference a dokumentace

- [CIDOC CRM – oficiální přehled verzí](https://cidoc-crm.org/versions-of-the-cidoc-crm) – status verzí; 7.1.3 je oficiální verze, 7.4 (2026) návrh.
- [CIDOC CRM 7.1.3 – třídy a vlastnosti](https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html) – konkrétní definice E8, E21, E18, E52, P4 a P22–P24.
- [Neo4j Python Driver Manual](https://neo4j.com/docs/python-manual/current/) – připojení a parametrizované zápisy.
- [Neo4j – Cypher](https://neo4j.com/docs/cypher-manual/current/) – grafové dotazování.
- [JSON Schema](https://json-schema.org/) a [Pydantic](https://docs.pydantic.dev/latest/) – validace meziformátu.
- [W3C JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) – případný budoucí Linked Data export.
