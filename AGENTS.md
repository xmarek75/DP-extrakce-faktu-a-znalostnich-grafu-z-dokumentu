# AGENTS.md — Pokyny pro Codex

## Kontext projektu

Tento repozitář slouží k diplomové práci **„Extrakce faktů a znalostních grafů z dokumentů“** (FIT VUT). Cílem je navrhnout, implementovat a experimentálně vyhodnotit systém, který z dokumentů získává strukturované informace a vytváří znalostní graf umožňující dotazování i propojení informací mezi dokumenty.

Zaměření:
- historické dokumenty, zejména 15.–16. století, a novější tištěné dokumenty;
- vstupní texty mohou pocházet z OCR/HTR a obsahovat chyby;
- extrakce pojmenovaných entit, vztahů, událostí, rolí, času a souvisejících faktů;
- správnost, dohledatelnost důkazů, sjednocování identit mezi dokumenty;
- reprodukovatelná evaluace extrakce a využitelnosti výsledného grafu.

**Důležité:** Velká část aktuálního repozitáře obsahuje *analýzy a návrhy*, nikoli již hotovou aplikaci. Nezaměňuj návrhový příklad za implementovanou funkcionalitu.

## Závazné podklady v repozitáři

Před návrhem nových modulů nebo změnou datového modelu přečti relevantní soubory:

1. `knowledge_graph_prototype_design.md` — výchozí architektura, ukázka událostně orientovaného Property Graphu, mapování na CIDOC CRM a plán implementace.
2. `knowledge_graph_information_scope.md` — rozsah extrakce, granularita grafu, kandidátní vs. přijaté informace, provenience a nejistota.
3. `docs/knowledge_graph_serialization.md` — rozdíly mezi konceptuálním modelem, RDF, JSON/JSON-LD, Property Graphem a serializací.
4. `knowledge_graphs_analysis.md` — širší porovnání reprezentací znalostí.
5. `whyKnowgledgeGraphs.md` — motivace a scénáře využití grafů.
6. `idea.txt` — orientační schéma zamýšlené pipeline.

Při rozporu mezi dokumenty nevytvářej vlastní „definitivní“ rozhodnutí bez vysvětlení. V implementaci uveď zvolené zjednodušení a jeho důvod. Konkrétní zadání uživatele má přednost před návrhovými doporučeními v tomto souboru.

## Výchozí architektura (pracovní hypotéza)

```text
Dokumenty (text / OCR)
    -> načtení a předzpracování
    -> extrakce faktů (LLM / baseline)
    -> vlastní strukturovaný JSON
    -> validace schématu i odkazů a důkazů
    -> normalizace a entity resolution
    -> mapování vybraných pojmů na CIDOC CRM
    -> Property Graph uložený v Neo4j
    -> Cypher dotazy, vizualizace, později GraphRAG
```

Preferované technologie pro první prototyp:
- **Python 3** pro aplikační logiku;
- **Pydantic nebo JSON Schema** pro validaci extrakčního meziformátu;
- **LLM se strukturovaným výstupem**, ale s vyměnitelným poskytovatelem a modelem;
- **Neo4j + oficiální Python driver + parametrizovaný Cypher** pro uložení grafu;
- **Docker Compose** pro lokální Neo4j;
- **pytest** pro automatizované testy.

Nezaváděj jinou databázi, orchestrace agentů, vektorový index ani GraphRAG jen proto, že by se mohly někdy hodit. Tyto části jsou pro první MVP mimo rozsah, pokud je uživatel výslovně nezadá.

**Nezaměňuj pojmy:** CIDOC CRM = ontologie; Property Graph = datový model; Neo4j = databáze; JSON = meziformát. Vlastní JSON ani Neo4j graf nejsou automaticky standardně kompatibilní RDF/CIDOC CRM implementací.

## První implementační milník (MVP)

Cílem je **skutečně spustitelný, malý, ověřitelný prototyp**, ne jen generování dokumentace.

Implementuj postupně:

1. Připrav **malou syntetickou testovací sadu** (např. 3–5 krátkých českých historicky stylizovaných dokumentů), u které jsou ručně známé entity a události. Jasně ji označ jako fiktivní.
2. Definuj verzované schéma meziformátu pro dokumenty, entity, události a důkazy. Každá lokální reference na entitu musí být validována.
3. Nejdříve vytvoř **deterministický import referenčního JSON do Neo4j**. Ověř, že graf správně reprezentuje více dokumentů a lze jej procházet pomocí Cypheru.
4. Přidej ukázkové Cypher dotazy: účastníci události, čas, převáděný objekt, původ tvrzení a propojení mezi dokumenty.
5. Následně přidej **LLM -> JSON** extrakci jako samostatnou vyměnitelnou komponentu. Ukládej syrový kandidátní výstup pro audit a srovnání.
6. Doplň základní normalizaci a konzervativní entity resolution; nejednoznačné případy ponech nesloučené.
7. Přidej testy a stručný návod, jak demo spustit a jak ověřit očekávané výsledky.

Nejdříve zajisti průchod malou ukázkou *end-to-end*. Teprve poté rozšiřuj rozsah entit a událostí, podporu OCR/HTR, pokročilé ontologické mapování a evaluační experimenty.

Pokud v repozitáři již existuje kód k danému kroku, **navazuj na něj**, nevytvářej zbytečně paralelní implementaci.

## Modelování znalostí

### Základní pravidla

- Preferuj **událostně orientovaný graf** pro převody majetku a další víceúčastnické nebo časově vymezené děje.
- Pro první příklad používej zejména `Person`, `PhysicalThing`, `Acquisition`, `TimeSpan`, `Document` a `Evidence`. `Place`, `Group` a další třídy přidávej podle dat a úkolu.
- Vybrané mapování na CIDOC CRM: `E21 Person`, `E18 Physical Thing`, `E8 Acquisition`, `E52 Time-Span`; `P22 transferred title to` (nabyvatel), `P23 transferred title from` (převodce), `P24 transferred title of` (předmět), `P4 has time-span` (čas).
- U Neo4j hran používej čitelné názvy (např. `TRANSFERRED_TITLE_TO`, `TRANSFERRED_TITLE_FROM`, `TRANSFERRED_TITLE_OF`, `HAS_TIME_SPAN`) a **dokumentuj jejich mapování** na CIDOC CRM.
- Aplikační vztahy typu `SUPPORTED_BY` nebo `FOUND_IN` označ jako **vlastní**, nikoli jako oficiální vlastnosti CIDOC CRM.
- Používej stabilní ID; lidsky čitelný název nebo jméno osoby není primární identifikátor.
- Lokální ID vytvořená při extrakci nesmí být bez dalšího považována za globální identity.
- Vlastnosti a vztahy měj typované; neumožňuj LLM vymýšlet libovolné názvy hran bez validační vrstvy.
- Zajisti idempotentní import (opakované spuštění nesmí vytvářet duplicitní graf).

### Historická přesnost a nejistota

- Nikdy nevymýšlej historická fakta, osoby, roky, vztahy ani identifikátory reálných pramenů. Syntetická data musí být explicitně označena.
- Rozlišuj **tvrzení uvedené v dokumentu** od **ověřeného historického faktu**.
- Nevytvářej vztahy, které nejsou doloženy vstupem. Pouhá společná zmínka dvou osob neznamená jejich příbuznost ani spolupráci.
- Uchovávej originální textový důkaz, ID dokumentu a pokud je to možné také ověřené umístění v textu. Textové offsety neber bez kontroly přímo z LLM.
- Respektuj negace, citace, podmíněnost, údajnost a rozpory mezi dokumenty.
- Nepřeváděj formulace jako „kolem roku 1520“ na přesné datum. Uchovávej původní formulaci a informaci o granularitě/nejistotě.
- **Entity resolution musí být konzervativní:** shodné nebo podobné jméno neprokazuje totožnost. U nejasných identit ponech oddělené uzly nebo kandidátní propojení určené k revizi.
- Při rozdílných tvrzeních různých zdrojů je neodstraňuj přepsáním jediné hodnoty.

### Kandidátní a hlavní vrstva

- Uchovávej kandidátní výstup extrakce odděleně od importovaného grafu, aby šlo zpětně sledovat chyby a testovat modely.
- Rozlišuj stavy `accepted`, `requires_review`, `unsupported_type`, `rejected` (pokud konkrétní schéma vyžaduje jiný zápis, zdokumentuj jej).
- Samotná validace Pydantic/JSON Schema **nepotvrzuje správnost faktu**.
- Do hlavního grafu nepřeváděj nejasné nebo nedoložené kandidáty jako nezpochybněná fakta.

## Pravidla pro implementaci

- Preferuj malé, modulární funkce s typovými anotacemi; odděl načítání dokumentů, extrakci, validaci, normalizaci, entity resolution a persistenci.
- **LLM vrací data, nikoli Cypher nebo jiné příkazy k vykonání.** Cypher sestavuje aplikace, používej parametry.
- Neukládej tokeny, přístupové údaje ani hesla do repozitáře. Konfiguraci čti z proměnných prostředí; do verzování patří pouze neobsahující tajemství `.env.example`.
- Neposílej reálné nebo citlivé dokumenty externím LLM bez explicitního zadání a odpovídající konfigurace.
- Pro testy upřednostňuj lokální data a mocky; nespoléhej na placené API ani běžící Neo4j v jednotkových testech. Databázové integrační testy odděl a popiš požadavky.
- Závislosti pinuj nebo alespoň rozumně omezuj; používej standardní nástroje Pythonu (`pyproject.toml`, `pytest` apod.), pokud úkol neurčuje jinak.
- Nevytvářej složitý framework pro jedinou ukázku. Návrh nejprve drž jednoduchý a rozšiřitelný.
- V logování chyb nikdy netiskni tajné údaje; ukládej smysluplnou diagnostiku nevalidních extrakcí.
- Zachovej stávající analytické dokumenty a pomocné skripty, pokud změna není nutná pro zadaný úkol.

## Doporučená struktura (až při vzniku implementace)

Následující rozložení je **návrh, ne popis již existujících souborů**. Respektuj skutečný stav repozitáře:

```text
src/kg_pipeline/
    ingestion/
    extraction/
    schemas/
    normalization/
    resolution/
    graph/
tests/
    fixtures/
examples/
docker-compose.yml
pyproject.toml
.env.example
```

Přidávej adresáře, až budou potřebné; nevytvářej prázdnou strukturu jen kvůli tomuto příkladu.

## Testování a definice hotového kroku

Pro každou implementovanou část ověř:

1. Validní extrakční JSON se přijme; nevalidní reference, typy a chybějící důkazy se rozpoznají.
2. Opakovaný import stejného vstupu nevytváří duplicity.
3. Neo4j dotaz vrátí správné účastníky, předmět a čas události.
4. Ze zobrazeného tvrzení lze dohledat zdrojový dokument a přesný použitý textový důkaz.
5. Dvě zmínky se neslučují bez dostatečných dokladů totožnosti.
6. Neznámá nebo přibližná datace nezíská uměle vyšší přesnost.

Při dokončení úkolu:
- spusť relevantní testy (např. `python -m pytest`, pokud je projekt již nakonfigurován);
- sděl, které testy skutečně proběhly a které nebylo možné spustit;
- aktualizuj návod k použití, pokud měníš způsob spuštění nebo konfiguraci;
- shrň změněné soubory, důležitá rozhodnutí, známá omezení a logický další krok.

## Spolupráce a styl

- S uživatelem komunikuj **česky**; názvy proměnných, funkcí, tříd a modulů piš zpravidla **anglicky**.
- Odborné texty a projektovou dokumentaci piš česky, pokud uživatel neurčí jinak.
- Neprezentuj návrhové volby jako experimentálně ověřená fakta. Výslovně uváděj předpoklady a omezení.
- Před rozsáhlejším refaktoringem nebo změnou grafového schématu stručně vysvětli dopad na pipeline a evaluaci.
- Neprováděj destruktivní databázové operace ani nepřepisuj data uživatele bez výslovného zadání.
- Snaž se dodávat malé, přehledné a testovatelné změny vhodné pro samostatné commity.
- Průběžně udržuj **reprodukovatelnost experimentů**: verze datasetu, verze schématu, nastavení modelu/promptu, náklady, metriky a popis běhového prostředí.

**Priorita:** nejprve funkční a ověřitelný graf z několika dokumentů, potom spolehlivější extrakce, propojování identit, širší ontologické mapování a teprve následně GraphRAG.
