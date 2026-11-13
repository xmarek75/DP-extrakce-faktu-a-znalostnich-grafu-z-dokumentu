# Poznámky k reprezentaci faktů a znalostních grafů

> **Kontext diplomové práce:** Extrakce faktů a znalostních grafů z dokumentů  
> **Účel dokumentu:** Průběžné poznámky k možnostem reprezentace extrahovaných informací, zejména z historických dokumentů. Nejde zatím o konečný návrh řešení.

## 1. Proč uvažovat o znalostním grafu?

Při extrakci informací z dokumentů nestačí vždy získat izolovaný seznam osob, míst, dat a vztahů. Cílem může být také **sjednocení informací z více dokumentů** a následné dotazování na jejich vzájemné souvislosti.

### 1.1 Potenciální výhody

- **Propojení informací napříč dokumenty:** různé zmínky mohou odkazovat na tutéž osobu, místo nebo událost.
- **Explicitní vztahy:** lze zaznamenat nejen entity, ale také význam jejich vzájemných vazeb.
- **Dotazování přes více hran:** lze vyhledávat přímé i nepřímé souvislosti mezi osobami, objekty a událostmi.
- **Flexibilita modelování:** grafové modely mohou přirozeně zachycovat různorodé druhy entit a vztahů.
- **Provenience a kvalifikátory:** při vhodném návrhu lze evidovat zdroj, časovou platnost, míru jistoty či další okolnosti tvrzení.
- **Sémantická interoperabilita:** zejména RDF v kombinaci s ontologiemi umožňuje používat standardizované pojmy a externí identifikátory.
- **Odvozování a kontrola:** při použití odpovídajících pravidel, ontologií nebo validačních mechanismů lze některé vztahy odvozovat a kontrolovat.
- **Vizualizace souvislostí:** grafové zobrazení může usnadnit průzkum a interpretaci extrahovaných znalostí.

### 1.2 Potenciální nevýhody

- **Složitější návrh modelu:** je třeba promyslet typy entit, vztahy, identifikátory a případná pravidla.
- **Entity resolution:** bez sjednocování zmínek o stejných entitách mohou vznikat duplicitní nebo izolované uzly.
- **Šíření chyb extrakce:** chybně rozpoznaná entita nebo vztah může ovlivnit další propojení a dotazy.
- **Nejisté a konfliktní informace:** neúplná, rozporná nebo pouze předpokládaná tvrzení vyžadují promyšlenou reprezentaci.
- **Provozní náklady:** grafové úložiště může přinést další infrastrukturu, indexování, správu a integraci do extrakční pipeline.
- **Možná zbytečná složitost:** pro jednoduché tabulkové výpisy faktů mohou být JSON nebo SQL dostačující.
- **Vizualizace nezaručuje správnost:** přehledně vykreslený graf může stále obsahovat chybná fakta.
- **Výkon závisí na úloze:** specializovaná grafová databáze nemusí být rychlejší pro všechny druhy dotazů.

**Hlavní rozhodovací otázka:** Potřebujeme informace z dokumentů **propojovat, sjednocovat a dotazovat se na souvislosti**, nebo stačí získat samostatnou strukturovanou sadu faktů pro každý dokument?

## 2. Property Graph

**Property Graph** je grafový datový model, ve kterém se informace reprezentují pomocí **uzlů**, **hran** a **vlastností**. Uzly obvykle představují entity, hrany jejich vztahy; uzly i hrany mohou obsahovat další atributy. V běžných implementacích, například v Neo4j, mají vztahy také vlastní typ.

Příklad jednoduchého modelu:

```text
(Person {name: "Pavel"})
    └──[:BORN_IN]──> (Place {name: "Praha"})
```

Property Graph je vhodný zejména pro přímou práci s propojenými daty a dotazování na jejich strukturu. **Sám o sobě ale nedefinuje význam** typů uzlů a hran: názvy jako `Person` nebo `BORN_IN` je třeba navrhnout a dokumentovat.

**Zdroj:** [DATAVERSITY – What Is a Property Graph?](https://www.dataversity.net/data-concepts/what-is-a-property-graph/)

### 2.1 Property Graph není totéž co ontologie

Je vhodné rozlišovat několik úrovní:

| Úroveň | Příklady | Co řeší |
|---|---|---|
| Sémantický model / ontologie | vlastní ontologie, CIDOC CRM | Jaké typy entit a vztahů existují a co znamenají |
| Model reprezentace dat | Property Graph, RDF | Jak se data zapisují a propojují |
| Úložiště | Neo4j, RDF databáze | Jak se data uchovávají a jak se nad nimi dotazuje |

**Property Graph lze kombinovat s ontologií CIDOC CRM.** Neznamená to však automaticky plnou podporu formální sémantiky CIDOC CRM: potřebná pravidla, omezení, odvozování či interoperabilitu je nutné zajistit samostatně nebo vhodnými nástroji.

## 3. Reprezentace neúplných informací

V historických dokumentech často chybí některé údaje. Například víme, že se Pavel narodil, ale neznáme datum ani místo narození.

### 3.1 Property Graph: narození jako událost

Pro rozšiřitelnou reprezentaci může být vhodné vytvořit **samostatný uzel události**:

```text
(Person {name: "Pavel"})
    └──[:WAS_BORN_IN_EVENT]──> (BirthEvent {id: "birth-001"})
```

Pokud později zjistíme místo či datum, lze je doplnit:

```text
(Person {name: "Pavel"})
    └──[:WAS_BORN_IN_EVENT]──> (BirthEvent {id: "birth-001"})
                                      ├──[:TOOK_PLACE_AT]──> (Place {name: "Praha"})
                                      └── year: 1520
```

Výhodou samostatného uzlu je možnost připojit další účastníky, zdroje i nejistotu. **Není to však univerzálně nejlepší postup pro každý graf**; záleží na požadavcích a očekávaných dotazech.

### 3.2 Property Graph: narození jako vlastnost

Pokud stačí pouze jednoduchá informace, lze ji uložit přímo u osoby:

```text
(Person {name: "Pavel", birthKnown: true})
```

Toto řešení je jednodušší, ale méně vhodné pro podrobné popisování událostí a jejich zdrojů.

### 3.3 Co znamená „neúplná trojice“ v RDF?

RDF tvrzení (trojice) má vždy **subjekt, predikát a objekt**. Trojici s chybějícím objektem tedy nelze zapsat jako platné RDF tvrzení. **Neúplná znalost ale nevadí:** zapíšeme pouze ta tvrzení, která známe, a ostatní zatím vynecháme.

Například můžeme zaznamenat, že existuje událost narození spojená s Pavlem, aniž bychom uvedli místo a čas:

```text
birth-001  rdf:type                  crm:E67_Birth
birth-001  crm:P98_brought_into_life  pavel
```

Později lze přidat další trojice. **Nepřítomnost informace v grafu sama o sobě neznamená, že je nepravdivá.**

**Související zdroj:** [CIDOC CRM – specifikace tříd a vlastností](https://cidoc-crm.org/html/cidoc_crm_v7.3.2.html#E1)

## 4. Metody extrakce faktů z dokumentů

Výběr extrakční metody závisí na povaze dokumentů, dostupných anotacích, nákladech a požadované přesnosti. Žádná metoda není univerzálně nejlepší.

| Přístup | Silné stránky | Omezení |
|---|---|---|
| Pravidla a vzory | Předvídatelnost; dobré pro stabilní formát a opakující se struktury | Hůře pokrývají jazykové varianty a nečekané formulace |
| Klasické modely ML / NER / RE | Mohou být účinné na známé doméně a při dostupných anotovaných datech | Obvykle potřebují trénovací či anotovaná data; náročnější přizpůsobení doméně |
| LLM | Flexibilita při různorodém textu; možnost strukturovaného výstupu bez vlastního rozsáhlého trénování | Náklady na inferenci, proměnlivost výstupů, riziko halucinací a nutnost validace |
| Hybridní pipeline | Kombinuje robustnost více přístupů, například pravidla a LLM | Vyšší komplexita návrhu, ladění a vyhodnocování |

U historických nebo OCR dokumentů je potřeba navíc zohlednit kvalitu vstupního textu, starší jazyk, pravopisné varianty a nejednoznačnosti.

### 4.1 Příklad možné pipeline

```text
Dokument / OCR text
        ↓
Předzpracování a rozdělení na části
        ↓
Extrakce entit, vztahů a událostí
        ↓
Validace a normalizace hodnot
        ↓
Entity resolution a propojování mezi dokumenty
        ↓
Převod do zvoleného sémantického modelu
        ↓
Uložení faktů a jejich provenience
        ↓
Dotazování a vyhodnocení
```

Jako jeden z nástrojů pro předzpracování složitých PDF a dalších dokumentů je v materiálech LlamaIndex zmiňován **LlamaParse**. Jde o možnou technologii k posouzení, nikoli nutnou součást řešení.

**Zdroj:** [LlamaIndex – Knowledge Graph Extraction](https://www.llamaindex.ai/glossary/knowledge-graph-extraction)

> **Poznámka ke zdroji:** Stránka LlamaIndex popisuje také vlastní nástroje. Její doporučení je vhodné porovnat s nezávislými zdroji a ověřit experimentálně; například tvrzení o obecné převaze Property Graphu nad RDF triple store nelze bez dalšího zobecnit.

## 5. CIDOC CRM: ontologie pro kulturní dědictví

**CIDOC CRM (Conceptual Reference Model)** je mezinárodně standardizovaná ontologie určená pro popis a integraci informací o kulturním dědictví. Poskytuje společný významový rámec pro osoby, objekty, místa, události, časové intervaly a další pojmy relevantní pro historické prameny.

CIDOC CRM je **výrazně orientovaný na události (*event-centric*)**, ale neomezuje se pouze na ně. Události umožňují zachytit *co se stalo, komu, kde a kdy* a doplnit další související informace.

### 5.1 Příklady tříd a vlastností

| Kód | Název | Význam |
|---|---|---|
| `E21` | `Person` | Osoba |
| `E67` | `Birth` | Událost narození |
| `E53` | `Place` | Místo |
| `E52` | `Time-Span` | Časové vymezení |
| `P98` | `brought into life` | Vztah události narození k narozené osobě |
| `P7` | `took place at` | Vztah události k místu |
| `P4` | `has time-span` | Vztah události k časovému intervalu |

**Zdroj:** [CIDOC CRM – oficiální specifikace](https://cidoc-crm.org/html/cidoc_crm_v7.3.2.html#E1)

### 5.2 Příklad event-centric modelování

Věta: *„Jan Novák se narodil roku 1520 v Brně.“*

```text
                 (E67 Birth: narození Jana Nováka)
                      /       |       \
                    P98      P7       P4
                    /         |         \
       (E21 Person: Jan)  (E53 Place: Brno)  (E52 Time-Span: 1520)
```

Oproti přímému vztahu `Jan Novák → narodil_se_v → Brno` vystupuje **narození jako samostatná událost**. To usnadňuje její další popis a případné propojení s prameny.

### 5.3 Výhody a limity pro diplomovou práci

**Možné výhody:**

- Standardizované pojmy pro historická data.
- Přirozené modelování událostí a jejich souvislostí.
- Potenciál pro integraci dat z archivů, knihoven a dalších zdrojů.
- Možnost převzít jen relevantní část již existujícího modelu.

**Možná omezení:**

- Poměrně vysoká složitost celé ontologie.
- Jednoduchý fakt může vyžadovat více propojených entit.
- Převod volného textu nebo výstupu LLM na její třídy a vlastnosti vyžaduje mapování a validaci.
- Sama o sobě neřeší extrakci faktů, entity resolution ani automaticky všechny otázky nejistoty a provenience.

**Zdroj:** [CIDOC CRM – oficiální specifikace](https://cidoc-crm.org/html/cidoc_crm_v7.3.2.html#E1)

## 6. Směr k ověření: vlastní ontologie inspirovaná CIDOC CRM + Property Graph

Jako **pracovní hypotéza**, nikoli definitivní rozhodnutí, se nabízí:

1. Navrhnout **jednoduchý vlastní sémantický model** pro osoby, místa, organizace, dokumenty, vztahy a události.
2. Při jeho návrhu vycházet z principů a vybraných pojmů **CIDOC CRM**, především z event-centric modelování.
3. Data reprezentovat jako **Property Graph**, například v Neo4j.
4. U každého faktu evidovat **zdrojový dokument**, ideálně i konkrétní pasáž, a podle potřeby míru jistoty nebo odlišné interpretace.
5. Navrhnout mapování vlastního modelu na relevantní třídy a vlastnosti CIDOC CRM a zjistit, kde je převod jednoduchý a kde ztrátový.

Schematicky:

```text
Historické dokumenty
        ↓
   OCR / extrakce textu
        ↓
   LLM a další metody extrakce
        ↓
   Strukturovaná fakta + odkazy na zdroje
        ↓
   Validace, normalizace, entity resolution
        ↓
   Vlastní ontologie inspirovaná CIDOC CRM
        ↓
   Property Graph / grafová databáze
```

**Důležité rozlišení:** CIDOC CRM a Property Graph nejsou přímí konkurenti. CIDOC CRM definuje **význam** entit a vztahů, zatímco Property Graph určuje **způsob jejich grafové reprezentace**. Alternativou k Property Graphu na úrovni datového modelu je například RDF.

### 6.1 Co je potřeba porovnat před rozhodnutím?

- **Pokrytí faktů:** dokáže model vyjádřit typické informace z vybraných historických dokumentů?
- **Úroveň detailu:** je potřeba reprezentovat samostatné události, nebo v některých případech stačí jednoduché vztahy?
- **Neúplnost a rozpory:** jak se zachovají neznámé hodnoty a více zdrojů s různými tvrzeními?
- **Provenience:** lze dohledat dokument a pasáž, ze které fakt pochází?
- **Propojování identit:** jak obtížné je sjednocování entit napříč dokumenty?
- **Dotazování:** jak snadno lze zodpovědět požadované výzkumné otázky?
- **Interoperabilita:** jak snadný je export/import do standardizovaných formátů a návaznost na jiné zdroje?
- **Implementační složitost a výkon:** kolik práce stojí model, validace a úložiště a jak fungují na reálných dotazech?

## 7. Průběžný závěr

Znalostní graf má největší potenciál tam, kde je cílem **propojovat fakta z více dokumentů a dotazovat se na jejich vztahy**. Volba grafové reprezentace však sama neřeší správnost extrakce ani sjednocování identit.

Pro další práci se jeví jako rozumné **prototypovat jednodušší event-centric Property Graph** a porovnat jeho možnosti s modelem založeným na vybraných částech CIDOC CRM. Konečné rozhodnutí by mělo vycházet z reálného vzorku dokumentů, typických dotazů a experimentálního vyhodnocení.


Omluva z dnešní konzultace