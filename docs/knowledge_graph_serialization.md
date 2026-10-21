# Zápis znalostního grafu: syntaxe, sémantika, serializace a validace

> **Diplomová práce:** Extrakce faktů a znalostních grafů z dokumentů  
> **Účel:** Rešeršní podklad pro výběr **správného zápisu extrahovaných znalostí**, nikoli pouze tvaru grafu.  
> **Stav:** Pracovní analýza a návrhy k ověření; ukázkové `ex:` termíny **nejsou existující schválenou ontologií**.  
> **Příklad:** Fiktivní listina „Jan Novák prodal roku 1542 Petrovi Malému mlýn v Brně.“

## 1. Co přesně znamená „správně zapsat knowledge graph“

Znalostní graf není jedno konkrétní textové schéma ani synonymum databáze. Při studiu je potřeba oddělit:

| Úroveň | Řešená otázka | Příklady |
|---|---|---|
| **Konceptuální model** | Jaké existují věci, události a tvrzení? | Osoba, mlýn, prodej, tvrzení listiny |
| **Logický/datový model** | Jak jsou propojeny? | RDF trojice, Property Graph uzly/hrany |
| **Slovník/ontologie** | Co znamenají jednotlivé typy a predikáty? | `Person`, `SaleEvent`, `seller`, CIDOC CRM |
| **Serializace** | Jak přesně vypadají uložené bajty/text? | Turtle, TriG, N-Triples, JSON-LD, vlastní JSON |
| **Ukládání/dotazování** | Jak graf načítáme a prohledáváme? | RDF triplestore/SPARQL, Neo4j/Cypher, SQL |
| **Validace** | Splňuje zápis a struktura požadavky? | RDF parser, SHACL, JSON Schema, omezení DB |
| **Správa znalostí** | Odkud informace pochází a jak se opravuje? | Zdroj, citace, verze OCR, nejistota, revize |

**„Správný“ zápis má minimálně čtyři složky:**
1. **Syntaktickou správnost:** parser data načte podle daného formátu.
2. **Strukturální správnost:** typy entit, vztahů, datové typy a počty hodnot odpovídají schématu.
3. **Sémantickou správnost:** vztah znamená přesně to, co chceme vyjádřit, a nenese nechtěný závěr.
4. **Věcnou a provenienční správnost:** tvrzení odpovídá zdrojové pasáži a lze ho dohledat; to **neznamená**, že historický zdroj musí mít pravdu.

Například graf, který obsahuje `Jan Novák -> OWNED -> Mlýn`, může být syntakticky správný, ale věcně zavádějící, pokud zdroj říká pouze, že jej prodal v určitém roce.

## 2. Vrstvy syntaxe a jejich význam

| Formát | Jaký model obvykle zapisuje | Charakter |
|---|---|---|
| **Turtle (`.ttl`)** | RDF | Čitelný textový zápis RDF trojic; prefixy, literály a datové typy. |
| **N-Triples (`.nt`)** | RDF | Jedna trojice na řádek; jednodušší pro výměnu či testování. |
| **TriG (`.trig`)** | RDF dataset | Rozšiřuje možnost zápisu o pojmenované grafy. |
| **N-Quads (`.nq`)** | RDF dataset | Čtyřice s identifikátorem grafu pro datasety. |
| **JSON-LD (`.jsonld`)** | Linked Data / RDF | Zápis pomocí JSON syntaxe; `@context` propojuje názvy s IRI. |
| **Vlastní JSON (`.json`)** | Libovolný model určený aplikací | Nemá automaticky RDF/ontologickou sémantiku. |
| **Cypher skript (`.cypher`)** | Property Graph v kompatibilním enginu | Příkazy pro vytvoření či dotazování; **není obecně standardní serializací grafu**. |
| **Export property grafu** | Property Graph | Např. vlastní JSON/CSV nebo formát konkrétního systému; pravidla je nutné popsat. |

Výběr syntaxe závisí na **cílovém datovém modelu a požadavcích na interoperabilitu**. Nelze férově porovnat „RDF versus JSON“ jako dvě alternativy na téže vrstvě: RDF je model, JSON syntaktický formát; RDF lze serializovat do JSON-LD.

### 2.1 Identifikátory, názvy a literály

- **IRI:** v RDF používat stabilní jednoznačné identifikátory. `https://example.org/dp/person_001` je pouze ilustrativní namespace, nikoliv již provozovaný endpoint.
- **Prefix:** `ex:person_001` je zkratka za celé IRI; prefix **není** názvem entity pro uživatele.
- **Label:** jméno „Jan Novák“ je hodnota, **nikoli unikátní identifikátor**.
- **Datové typy:** rok lze reprezentovat `"1542"^^xsd:gYear`, přesný den `"1542-03-10"^^xsd:date`. Nepřevádět neurčitá historická data na falešně přesné dny.
- **Jazyk:** český text lze označit `"Jan Novák"@cs`.
- **Blank nodes:** vhodné pro některé lokální struktury; pro trvalou identitu dokumentů, entit a tvrzení jsou výhodnější stabilní IRI.
- **Vlastní slovník:** explicitně definovat význam predikátů, doménu/range, směr hrany, kardinalitu, časovou platnost a případně existující ekvivalenty.

## 3. Stejný případ zapsaný různými způsoby

### 3.1 RDF v Turtle

Ukázka je **minimální syntakticky orientovaný příklad**. Fiktivní typy `ex:SaleEvent`, `ex:Claim` a predikáty `ex:...` představují pracovní doménové schéma. Zdroji není automaticky přisuzována pravdivost.

```turtle
@prefix ex:   <https://example.org/dp/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .

ex:person_001 a ex:Person ;
    ex:name "Jan Novák"@cs .
ex:person_002 a ex:Person ;
    ex:name "Petr Malý"@cs .
ex:mill_001 a ex:Building .
ex:brno a ex:Place .
ex:document_001 a ex:Document, prov:Entity .

ex:sale_001 a ex:SaleEvent ;
    ex:seller ex:person_001 ;
    ex:buyer ex:person_002 ;
    ex:transferredObject ex:mill_001 ;
    ex:place ex:brno .

ex:claim_001 a ex:Claim, prov:Entity ;
    ex:aboutEvent ex:sale_001 ;
    ex:assertedYear "1542"^^xsd:gYear ;
    ex:evidenceText "Jan Novák prodal roku 1542 Petrovi Malému mlýn v Brně."@cs ;
    prov:wasDerivedFrom ex:document_001 .
```

**Co zápis znamená:** existuje reprezentace události `sale_001` a **samostatné tvrzení zdroje** `claim_001` o jejím roce. Rozdělení umožňuje zachovat citaci a další zdrojový rok bez přepsání roku v uzlu události. Pokud mohou být sporní i účastníci, role se musí také evidovat jako zdrojově kvalifikovaná tvrzení, ne bezpodmínečné hrany.

### 3.2 RDF v JSON-LD

Stejná podstatná tvrzení lze zapsat pomocí JSON-LD. Názvy vlastností s prefixem `ex:` a odkazy pomocí `@id` jsou identifikátory RDF, nikoliv běžné textové popisky.

```json
{
  "@context": {
    "ex": "https://example.org/dp/",
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "@graph": [
    {
      "@id": "ex:person_001",
      "@type": "ex:Person",
      "ex:name": {"@value": "Jan Novák", "@language": "cs"}
    },
    {
      "@id": "ex:person_002",
      "@type": "ex:Person",
      "ex:name": {"@value": "Petr Malý", "@language": "cs"}
    },
    {"@id": "ex:mill_001", "@type": "ex:Building"},
    {"@id": "ex:brno", "@type": "ex:Place"},
    {"@id": "ex:document_001", "@type": ["ex:Document", "prov:Entity"]},
    {
      "@id": "ex:sale_001",
      "@type": "ex:SaleEvent",
      "ex:seller": {"@id": "ex:person_001"},
      "ex:buyer": {"@id": "ex:person_002"},
      "ex:transferredObject": {"@id": "ex:mill_001"},
      "ex:place": {"@id": "ex:brno"}
    },
    {
      "@id": "ex:claim_001",
      "@type": ["ex:Claim", "prov:Entity"],
      "ex:aboutEvent": {"@id": "ex:sale_001"},
      "ex:assertedYear": {"@value": "1542", "@type": "xsd:gYear"},
      "ex:evidenceText": {
        "@value": "Jan Novák prodal roku 1542 Petrovi Malému mlýn v Brně.",
        "@language": "cs"
      },
      "prov:wasDerivedFrom": {"@id": "ex:document_001"}
    }
  ]
}
```

**Kontrolní úkol:** parsovat Turtle a JSON-LD do RDF a ověřit, že reprezentují **ekvivalentní množinu trojic** (po zohlednění blank nodes a případných kontextů). Pouhá vizuální podobnost JSONu nestačí.

### 3.3 Property Graph / Cypher (Neo4j jako příklad)

V Property Graphu zachováme identifikátory uzlů, typy hran a atributy. V Cypheru vytváříme data příkazy (nikoliv vendor-neutrální serializací).

```cypher
CREATE CONSTRAINT person_id IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

MERGE (jan:Person {id: 'person_001'})
SET jan.name = 'Jan Novák';

MERGE (petr:Person {id: 'person_002'})
SET petr.name = 'Petr Malý';

MERGE (mill:Building {id: 'mill_001'});
MERGE (brno:Place {id: 'brno'});
MERGE (doc:Document {id: 'document_001'});

MERGE (sale:SaleEvent {id: 'sale_001'});
MERGE (claim:Claim {id: 'claim_001'})
SET claim.assertedYear = '1542',
    claim.yearPrecision = 'year',
    claim.evidenceText = 'Jan Novák prodal roku 1542 Petrovi Malému mlýn v Brně.';

MERGE (sale)-[:SELLER]->(jan);
MERGE (sale)-[:BUYER]->(petr);
MERGE (sale)-[:TRANSFERRED_OBJECT]->(mill);
MERGE (sale)-[:PLACE]->(brno);
MERGE (claim)-[:ABOUT_EVENT]->(sale);
MERGE (claim)-[:DERIVED_FROM]->(doc);
```

V ukázce je rok uložen jako řetězec a přesnost je explicitní atribut; **není to automaticky ekvivalent RDF literálu `xsd:gYear`**. Konkrétní výběr datových typů a omezení pro Property Graph je součástí návrhu. Pro ostatní typy uzlů by byly vhodné další unikátní `id` constraints.

### 3.4 Proč nestačí jen přímé hrany

Zápis `(Jan)-[:PRODAL]->(Mlýn)` je čitelný, ale může ztratit důležité informace: **komu, kdy, kde, na základě kterého tvrzení, s jakou mírou jistoty**. Hrana s vlastnostmi může stačit pro jednoduchý fakt, ale má omezení při více zdrojích a odlišných tvrzeních. Pro n-ární události lze použít **uzel události**, pro doložitelnost a konflikty **uzel tvrzení**.

U historických dat také nezaměňovat `PRODAL` za trvalý vztah `VLASTNÍ`: převod vlastnictví v jednom roce neříká, že vlastnictví trvalo libovolně dlouho.

## 4. Metadata, čas, důkaz a konflikty

| Prvek | Co ověřit při zápisu |
|---|---|
| **Dokument** | Stabilní ID, bibliografický popis, verze/OCR, dostupnost skenu |
| **Evidence** | Konkrétní citace, stránka a offset nebo souřadnice; verze textu |
| **Extrakce** | Identifikátor modelu, verze promptu, běh, čas a stav lidské revize |
| **Čas** | Rozlišení času události, časové platnosti, data listiny a systémového času |
| **Nejistota** | Nejistota OCR ≠ nejistota entity linking ≠ nepravdivost historického tvrzení |
| **Identita** | Textová zmínka ≠ osoba; identity mohou být nejisté a opravitelné |
| **Konfliktní údaje** | Uchovat dvě samostatná tvrzení, jejich zdroje a jejich stav |
| **Opravy** | Audit historie, nové verze tvrzení a možnost přepočtu projekce |

### Příklad konfliktu

Pokud `document_001` uvádí rok **1542** a `document_002` rok **1547**, pro tentýž hypotetický `sale_001` můžeme uchovat dvě tvrzení:

```turtle
ex:document_002 a ex:Document, prov:Entity .

ex:claim_002 a ex:Claim, prov:Entity ;
    ex:aboutEvent ex:sale_001 ;
    ex:assertedYear "1547"^^xsd:gYear ;
    prov:wasDerivedFrom ex:document_002 .
```

Jde o další část **předchozího Turtle grafu**; prefixy a `sale_001` jsou definované výše. Model **neříká**, že oba letopočty jsou pravdivé. Samotné předpokládané sjednocení dvou popisů do `sale_001` musí být rovněž ověřeno: mohou označovat i dvě různé události.

### Named graphs, PROV-O a novější RDF

- **Named graphs** umožňují seskupovat RDF trojice v kontextu datasetu; pojmenování grafu samo o sobě automaticky nedokazuje pravdivost ani autorství každé trojice.
- **PROV-O** nabízí základní pojmy pro původ informací. V ukázce je zdrojem **tvrzení**, nikoliv automaticky historická událost samotná.
- **RDF 1.2** přináší možnosti pro termíny obsahující trojice a nové modelování metadat. V době tvorby tohoto podkladu ověřit aktuální status jednotlivých specifikací i dostupnost implementací; do pilotu je rozumné mít kompatibilní základ RDF 1.1.
- **CIDOC CRM** je kandidát pro odbornější koncepty historických událostí; nejprve porovnat potřebné třídy a vlastnosti, nikoliv převzít plnou ontologii bez zdůvodnění.

## 5. Validace: parser nestačí

Překlad do korektního RDF, JSON-LD nebo Cypheru nezaručuje vhodné schéma ani věcnou správnost.

**RDF/SHACL – ilustrativní kontrola tvrzení:**

```turtle
@prefix ex:   <https://example.org/dp/> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .

ex:SaleClaimShape a sh:NodeShape ;
    sh:targetClass ex:Claim ;
    sh:property [
        sh:path ex:aboutEvent ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:class ex:SaleEvent
    ] ;
    sh:property [
        sh:path ex:assertedYear ;
        sh:maxCount 1 ;
        sh:datatype xsd:gYear
    ] ;
    sh:property [
        sh:path prov:wasDerivedFrom ;
        sh:minCount 1 ;
        sh:class ex:Document
    ] .
```

Tohle kontroluje **vybrané strukturální podmínky**. Neověřuje, že rok 1542 opravdu stojí v listině nebo že nejde o chybu OCR. U dokumentově odvozených faktů je nutná také **kontrola důkazů proti vstupnímu textu**.

Další kontroly:
1. **RDF parser:** validní Turtle/JSON-LD, bez chybných IRI a literálů.
2. **RDF ekvivalence:** stejné výroky nezávisle na zvolené serializaci.
3. **SHACL:** požadované role, typy, kardinality a zdroj tvrzení.
4. **Neo4j constraints:** unikátní ID a základní konzistence při opakovaném importu.
5. **JSON Schema:** kontrola přenosového a extrakčního meziformátu.
6. **Doménové testy:** proč tato relace, zda jde o tvrzení nebo skutečnost, zda data podporuje citace.
7. **Round-trip:** export → import → opakované dotazy bez ztráty ID, rolí, času a evidence.

## 6. Typické chyby, které v diplomce cíleně zkoumat

| Chyba zápisu | Proč je problém | Doporučená kontrola |
|---|---|---|
| Použití jména osoby jako ID | Dvě osoby mohou mít stejné jméno | Stabilní ID, oddělení `Mention` a `Entity` |
| Vložení všech dat do textových řetězců | Ztráta typu, rozlišení času, obtížné dotazy | Datové typy a přesnost hodnot |
| Přímá hrana bez zdrojového tvrzení | Nelze dohledat původ a rozpory | Claim/evidence model |
| Vynucení přesného data z neúplného roku | Vymyšlená přesnost | Rok, interval, neurčitost |
| Zaměnění události za vztah vlastníka | Falešný závěr o délce vlastnictví | Event-centric model |
| Nekonzistentní směr relace | Dotaz vrací odlišný význam | Doménový slovník a testy |
| Automatické sloučení zmínek stejného jména | Falešná identita napříč dokumenty | Entity resolution s možností revize |
| Vlastní JSON nazvaný „RDF“ | Chybí RDF identifikátory a sémantika | JSON-LD kontext / validace |
| Zápis pouze pomocí `CREATE` bez opatrnosti | Opakovaný import může duplikovat data | Unikátní constraints a idempotentní import |
| „Prošlo SHACL“ = „historicky pravdivé“ | Validace testuje strukturu, ne prameny | Ověření evidence a kvalitativní evaluace |

## 7. Povinné otázky do rešerše

- Které grafové informace musí být **identifikovatelné** napříč více dokumenty a reimporty?
- Jaké predikáty potřebujeme, jaký mají **význam, orientaci, doménu/range a kardinalitu**?
- Jak volit mezi **přímými hranami, event-centric a claim-centric zápisem**?
- Je RDF + JSON-LD výhodnější pro interoperabilitu než jednoduchý vlastní formát? Za jakou cenu?
- Kdy použít **RDF 1.1**, kdy případně novější **RDF 1.2** a jaká je podpora nástrojů?
- Jak modelovat **citace, více verzí OCR, konfliktní fakta a dočasnou platnost**?
- Jak přesně mapovat mezi **JSON meziformátem, RDF a Property Graphem bez ztrát významu**?
- Co je **syntaktická validace**, co **strukturální**, co **sémantická** a co **historická verifikace**?
- Lze vytvořit malý společný základ ontologie, nebo se vyplatí adaptovat **CIDOC CRM**?

## 8. Konkrétní další úkoly (P0/P1)

- [ ] **P0:** Zvolit 2–3 příklady z dokumentů včetně komplikované události a dvou rozporných zdrojů.
- [ ] **P0:** Definovat první verzi slovníku tříd, hran, atributů, směrů a identifikátorů.
- [ ] **P0:** Zapsat stejná tvrzení do `.ttl`, `.jsonld` a jako Property Graph (včetně importu).
- [ ] **P0:** Automaticky validovat RDF syntax, JSON-LD rozbalení a SHACL shapes.
- [ ] **P0:** U každého příkladu zpětně rekonstruovat původní tvrzení a důkaz.
- [ ] **P0:** Ověřit zachování znalostí při převodu JSON → RDF / Property Graph → JSON.
- [ ] **P1:** Srovnat kvalifikaci tvrzení: uzly tvrzení, named graphs, RDF 1.2 triple terms a metadata hran v Property Graphu.
- [ ] **P1:** Porovnat použitelné podmnožiny CIDOC CRM a vlastní jednoduché schéma.
- [ ] **P1:** Změřit složitost zápisu, dotazování a oprav chyb, nikoliv pouze počet trojic/uzlů.

**Předběžné doporučení k experimentu (ne závěr):** použít **kanonický, verzovaný meziformát tvrzení** jako vstup do několika stejně sémanticky úplných reprezentací. Tím lze oddělit kvalitu extrakce od vhodnosti konkrétního zápisu.

## 9. Normativní a referenční zdroje

- [W3C RDF 1.1 Turtle](https://www.w3.org/TR/turtle/) — syntaxe RDF trojic.
- [W3C JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) — `@context`, `@id`, mapování na RDF.
- [W3C SHACL](https://www.w3.org/TR/shacl/) — validace RDF grafů.
- [W3C RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/) — novější RDF model, u implementace ověřit aktuální status.
- [W3C SHACL 1.2 Core](https://www.w3.org/TR/shacl-core/) — nové specifikace, u implementace ověřit status (pracovní návrh k říjnu 2026).
- [W3C PROV-O](https://www.w3.org/TR/prov-o/) — původ a odvození informace.
- [Neo4j Cypher CREATE](https://neo4j.com/docs/cypher-manual/current/clauses/create/) — syntaxe uzlů a hran a rozdíl `CREATE`/`MERGE`.

**Poznámka k ověření:** zde uvedené modely a ukázky jsou rešeršní demonstrace. Před jejich použitím jako součásti finální implementace je nutné spustit parsery, validace a ekvivalentní dotazy na skutečných datech.
