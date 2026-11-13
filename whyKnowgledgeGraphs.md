# Motivace pro využití znalostních grafů při zpracování dokumentů

## 1. Úvod

Při práci s rozsáhlými kolekcemi dokumentů vzniká potřeba nejen vyhledávat relevantní texty, ale také identifikovat konkrétní fakta, propojovat informace napříč dokumenty a odpovídat na komplexní otázky.

Příkladem může být systém podobný aplikaci semANT obsahující přibližně 60 000 historických dokumentů.

Jednou z možností vyhledávání nad takovou kolekcí je využití technologie **Retrieval-Augmented Generation (RAG)**, která kombinuje vyhledávání relevantních textových úseků s velkým jazykovým modelem (LLM).

Klasický RAG je vhodný především pro otázky, u kterých lze odpověď nalézt v jednom nebo několika relevantních úsecích textu.

Problémy však mohou nastat v situacích, kdy:

- Odpověď vyžaduje propojení informací z několika různých dokumentů.
- Je potřeba identifikovat všechny entity splňující určité podmínky.
- Stejná entita vystupuje v různých dokumentech pod odlišnými jmény.
- Uživatel opakovaně pokládá složité otázky vyžadující interpretaci stejných informací.
- Je potřeba dohledat původ jednotlivých faktů.
- Dotaz vyžaduje komplexní analýzu vztahů mezi osobami, místy, organizacemi a událostmi.

Jedním z možných řešení je **předběžná extrakce strukturovaných faktů a jejich uložení do znalostního grafu (Knowledge Graph, KG)**.

Znalostní graf umožňuje reprezentovat entity a jejich vzájemné vztahy ve strukturované podobě. Tím vzniká možnost dotazovat se přímo na konkrétní vztahy, nikoliv pouze vyhledávat textové úseky podobné zadané otázce.

> **Hlavní myšlenka:** Znalostní graf umožňuje přesunout část práce z okamžiku dotazování do fáze předzpracování dokumentů. Informace jsou extrahovány, normalizovány a propojeny předem, takže je lze opakovaně využívat při různých dotazech.

---

## 2. Omezení klasického RAG

### 2.1 Princip klasického RAG

Typický RAG systém funguje následovně:

```text
             60 000 dokumentů
                    |
                    v
            Rozdělení na chunky
                    |
                    v
             Výpočet embeddingů
                    |
                    v
             Vektorová databáze


                 Dotaz
                    |
                    v
             Vector Search
                    |
                    v
           Top-K relevantních
             textových úseků
                    |
                    v
                   LLM
                    |
                    v
                 Odpověď
```

Systém vyhledává textové úseky, které jsou sémanticky podobné uživatelskému dotazu.

Pro jednoduché otázky může být tento přístup velmi efektivní.

**Příklad:**

> Kdy se narodil Jan Novák?

Pokud některý dokument obsahuje informaci:

> Jan Novák se narodil roku 1520 v Brně.

RAG může tento dokument vyhledat a LLM z něj vytvoří správnou odpověď.

Situace je složitější, pokud požadovaná odpověď není přímo obsažena v jednom dokumentu.

### 2.2 Problém s vyhledáváním pomocí Top-K

Vektorové vyhledávání typicky vrací omezený počet nejrelevantnějších textových úseků.

Například:

```text
Dotaz
  |
  v
60 000 dokumentů
  |
  v
10 nejrelevantnějších chunků
  |
  v
LLM
```

Problém nastává, pokud některý důležitý dokument není dostatečně podobný původní otázce.

Takový dokument nemusí být vyhledán, přestože obsahuje informaci nezbytnou pro sestavení správné odpovědi.

**Důležité upřesnění:** Samotných 60 000 dokumentů nepředstavuje pro moderní RAG zásadní problém. Omezení se projevují zejména při komplexních dotazech vyžadujících propojení většího množství informací.

Pokročilé systémy využívající iterativní vyhledávání, hybridní retrieval nebo AI agenty mohou některá tato omezení překonat. Obvykle však vyžadují složitější zpracování dotazu.

---

# 3. Výhoda č. 1: Propojování faktů napříč dokumenty (Multi-hop Reasoning)

Jednou z nejvýznamnějších výhod znalostních grafů je možnost odpovídat na otázky, které vyžadují propojení několika nezávislých faktů.

## 3.1 Praktický příklad

Představme si archiv obsahující 60 000 historických dokumentů.

V různých částech archivu se nacházejí následující záznamy.

**Dokument A – Majetková evidence z roku 1521**

> Matěj Kovář vlastnil v roce 1521 dům na brněnském náměstí.

**Dokument B – Rodinný záznam z roku 1525**

> Matěj Kovář, měšťan brněnský, jest otcem Anny Kovářové.

**Dokument C – Oddací zápis z roku 1528**

> Anna Kovářová uzavřela manželství s Václavem Novotným.

Uživatel položí otázku:

**„Kdo byl zetěm osob, které v roce 1521 vlastnily dům v Brně?“**

Správná odpověď:

> Václav Novotný byl zetěm Matěje Kováře.

### Problém klasického RAG

Žádný z uvedených dokumentů samostatně neobsahuje úplnou odpověď.

K získání odpovědi je nutné provést několik kroků:

1. Najít vlastníky domů v Brně v roce 1521.
2. Identifikovat jejich děti.
3. Dohledat manželské vztahy těchto dětí.
4. Odvodit, kdo byl zetěm původního vlastníka.

Vektorové vyhledávání může snadno najít dokument A, protože odpovídá části otázky týkající se vlastnictví domu.

Dokument C však nemusí být vyhledán, protože pojednává o manželství a nemusí obsahovat výrazy související s vlastnictvím nemovitostí.

Pokud dokument C nebude součástí kontextu předaného LLM, nebude mít systém dostatek informací k vytvoření odpovědi.

### Řešení pomocí znalostního grafu

Při předběžném zpracování dokumentů vzniknou následující fakta:

```text
Dokument A:
Matěj Kovář --OWNED--> Dům v Brně
                         rok: 1521

Dokument B:
Matěj Kovář --FATHER_OF--> Anna Kovářová

Dokument C:
Anna Kovářová --SPOUSE_OF--> Václav Novotný
```

Po propojení entit vznikne znalostní graf:

```text
                  Matěj Kovář
                  /         \
                 /           \
              OWNED        FATHER_OF
             (1521)            |
               |               v
               v          Anna Kovářová
          Dům v Brně           |
                               |
                           SPOUSE_OF
                               |
                               v
                        Václav Novotný
```

Odpověď lze získat procházením vztahů:

```text
Vlastník domu
      |
      v
Jeho dcera
      |
      v
Manžel dcery
      |
      v
    Zeť
```

Znalostní graf umožňuje tento postup realizovat pomocí strukturovaného grafového dotazu.

**Výhoda:** Není nutné při každém dotazu znovu vyhledávat a interpretovat všechny původní dokumenty. Potřebné vztahy jsou již uložené ve strukturované podobě.

### Kdy je tato výhoda nejdůležitější?

- Genealogický výzkum.
- Rekonstrukce historických vztahů.
- Propojování majetkových a rodinných záznamů.
- Vyhledávání nepřímých vztahů mezi osobami.
- Analýza organizačních a společenských vazeb.

---

# 4. Výhoda č. 2: Systematické vyhledávání všech odpovídajících faktů

Klasický RAG je často optimalizován na nalezení několika nejrelevantnějších textových úseků.

To nemusí být dostatečné, pokud uživatel požaduje kompletní množinu výsledků.

## 4.1 Praktický příklad

Uživatel položí otázku:

**„Najdi všechny osoby, které vlastnily nemovitost v Brně mezi lety 1500 a 1550 a zároveň zastávaly nějaký veřejný úřad.“**

Předpokládejme, že v archivu existuje 150 dokumentů obsahujících relevantní informace.

### Klasický RAG

Pokud systém vyhledá pouze 10 nejrelevantnějších textových úseků, může získat jen malou část všech požadovaných informací.

LLM následně vytvoří odpověď na základě neúplného kontextu.

Výsledkem může být seznam několika správných osob, který však nebude úplný.

**Problém:** RAG může vrátit správné jednotlivé výsledky, ale nezaručuje, že nalezl všechny odpovídající případy.

### Knowledge Graph

Pokud byly při předzpracování dokumentů extrahovány všechny relevantní entity a vztahy, lze provést strukturovaný dotaz.

Například:

```cypher
MATCH (p:Person)-[r:OWNED]->(b:Building)
MATCH (p)-[:HELD_POSITION]->(position:Position)
WHERE b.city = 'Brno'
  AND r.year >= 1500
  AND r.year <= 1550
RETURN DISTINCT p.name, position.name
```

Znalostní graf umožňuje systematicky vyhledat všechny uzly splňující požadované podmínky.

**Výhoda:** Dotaz není omezen pouze na určitý počet sémanticky nejpodobnějších dokumentů.

**Omezení:** Úplnost výsledků je podmíněna úplností a správností znalostního grafu. Pokud některé vztahy nebyly extrahovány, systém je nemůže vrátit.

---

# 5. Výhoda č. 3: Sjednocování entit napříč dokumenty (Entity Resolution)

Historické dokumenty často označují stejnou osobu různými způsoby.

Příklad:

```text
Dokument A:
"Jan Novák"

Dokument B:
"J. Novák"

Dokument C:
"Johannes Nowak"

Dokument D:
"Jan, měšťan brněnský"
```

Všechna tato označení mohou představovat jednu historickou osobu.

Současně ale může existovat více různých osob se stejným jménem.

## 5.1 Problém klasického RAG

Vektorové vyhledávání může rozpoznat významovou podobnost textů, ale samo o sobě nezaručuje správné určení identity.

Pokud uživatel položí otázku:

**„Jaký majetek vlastnil Jan Novák během svého života?“**

Systém musí najít všechny dokumenty týkající se konkrétní osoby.

Pokud je osoba v různých dokumentech označena odlišně, mohou být některé záznamy vynechány.

Naopak může dojít k chybnému propojení dvou odlišných osob.

## 5.2 Řešení pomocí znalostního grafu

Při konstrukci grafu se provádí sjednocování identit.

Například:

```text
                Person_123
                    |
           +--------+--------+
           |        |        |
           v        v        v
       Jan Novák  J. Novák  Johannes Nowak
```

Všechna označení jsou propojena s jednou kanonickou entitou.

Následné dotazy mohou využívat její jednoznačný identifikátor.

**Výhoda:** Sjednocení identit se provede předem a může být opakovaně využíváno při všech budoucích dotazech.

### Důležité upozornění

Entity Resolution není automatickou vlastností grafové databáze.

Musí být implementováno jako součást procesu extrakce a propojování entit.

Znalostní graf však poskytuje vhodnou strukturu pro uchovávání sjednocených identit a jejich vztahů.

---

# 6. Výhoda č. 4: Nižší náklady na opakované komplexní dotazy

Jednou z potenciálních ekonomických výhod znalostních grafů je možnost snížit náklady na opakované dotazování.

Princip spočívá v tom, že složitější interpretace dokumentů proběhne již při vytváření znalostního grafu.

## 6.1 Klasický RAG

Představme si otázku:

**„Kteří obchodníci z Brna byli příbuzní osob zastávajících veřejné úřady v 16. století?“**

Pokročilý agentní RAG může potřebovat:

1. Najít obchodníky z Brna.
2. Najít osoby zastávající veřejné úřady.
3. Dohledat jejich rodinné vztahy.
4. Propojit získané informace.
5. Vytvořit odpověď.

Tento postup může vyžadovat několik vyhledávání a opakovaná volání LLM.

Při dalším podobném dotazu může systém znovu zpracovávat informace, které již jednou interpretoval.

## 6.2 Knowledge Graph

Ve znalostním grafu jsou vztahy již připravené:

```text
Person_123 --LIVES_IN--> Brno

Person_123 --OCCUPATION--> Obchodník

Person_123 --RELATED_TO--> Person_456

Person_456 --HELD_POSITION--> Purkmistr
```

Systém může požadované informace získat pomocí grafového dotazu.

Pokud je dotaz předem známý a správně formulovaný, není nutné používat LLM vůbec.

Pokud uživatel zadává otázky přirozeným jazykem, může LLM sloužit pouze k převodu otázky na grafový dotaz a případně k formulaci odpovědi.

Není tedy nutné opakovaně interpretovat celé původní dokumenty.

## 6.3 Porovnání nákladů

| Vlastnost | Klasický RAG | Knowledge Graph |
|---|---|---|
| Počáteční zpracování | Chunking, embeddings | Extrakce entit, vztahů a jejich sjednocení |
| Počáteční náklady | Obvykle nižší | Obvykle vyšší |
| Cena složitého dotazu | Může vyžadovat více volání LLM | Může stačit databázový dotaz |
| Opakované dotazy | Mohou opakovat interpretaci textů | Opakované využití uložených faktů |
| Vyhledávání vztahů | Vyžaduje retrieval a interpretaci | Přímé procházení grafu |
| Aktualizace dokumentů | Aktualizace vyhledávacího indexu | Aktualizace entit a vztahů |

### Ekonomická návratnost

Celkové náklady lze zjednodušeně vyjádřit:

**Klasický RAG:**

```text
C_RAG = C_preprocessing + N × C_query_RAG
```

**Knowledge Graph:**

```text
C_KG = C_construction + N × C_query_KG
```

Kde:

- `C_preprocessing` – náklady na přípravu klasického RAG.
- `C_construction` – náklady na vytvoření znalostního grafu.
- `N` – počet uživatelských dotazů.
- `C_query_RAG` – průměrné náklady na jeden RAG dotaz.
- `C_query_KG` – průměrné náklady na jeden dotaz využívající KG.

Za předpokladu, že jsou náklady na jednotlivý KG dotaz nižší, může při dostatečně velkém počtu dotazů dojít k návratnosti vyšší počáteční investice.

**Výhoda:** Při častém opakovaném dotazování může být využití znalostního grafu ekonomicky výhodnější.

Nejedná se však o univerzální pravidlo. Záleží na složitosti otázek, kvalitě extrakce, použitém LLM, nákladech na infrastrukturu a četnosti aktualizací dokumentů.

### 6.4 Opakované využití jednou extrahovaného faktu

Představme si, že systém získá informaci:

```text
Jan Novák --FATHER_OF--> Anna Nováková
```

Tento vztah může být využit při mnoha různých otázkách:

- Kdo byl otcem Anny Novákové?
- Kdo byli potomci Jana Nováka?
- Jaké rodinné vztahy existovaly mezi měšťany v Brně?
- Které rodiny byly propojeny prostřednictvím manželství?
- Jak se majetek předával mezi příbuznými?

Informace je extrahována jednou, ale může být využita při velkém množství různých dotazů.

Tento princip lze označit jako **předběžnou materializaci strukturovaných znalostí**.

Podobný princip lze realizovat také v relačních databázích. Výhodou znalostního grafu je především přirozená reprezentace a procházení vzájemně propojených entit.

---

# 7. Výhoda č. 5: Analýza rozsáhlé kolekce dokumentů jako celku

Dalším problémem klasického RAG jsou otázky, které vyžadují analýzu témat nebo vztahů v celé kolekci.

## 7.1 Praktický příklad

Uživatel položí otázku:

**„Jaké byly hlavní příčiny majetkových sporů mezi měšťany v Brně během 16. století?“**

Na rozdíl od předchozích příkladů zde nehledáme jeden konkrétní fakt.

Potřebujeme analyzovat velké množství historických záznamů a identifikovat opakující se vzorce.

### Klasický RAG

Klasický RAG může vyhledat několik dokumentů pojednávajících o majetkových sporech.

Problém je v tom, že tyto dokumenty nemusí reprezentovat celou kolekci.

LLM následně vytvoří shrnutí pouze na základě vybraných textů.

Výsledkem může být zkreslený obraz nejčastějších příčin sporů.

### Knowledge Graph / GraphRAG

Pokud má systém vytvořený znalostní graf obsahující osoby, majetek, události a jejich vzájemné vztahy, lze analyzovat rozsáhlejší struktury.

Například:

```text
                 Majetkové spory
                       |
          +------------+------------+
          |            |            |
          v            v            v
       Dědictví     Dluhy       Vlastnictví
          |            |            |
          v            v            v
       Rodiny      Obchodníci     Nemovitosti
```

Graf může umožnit vyhledávání opakujících se vztahů nebo struktur.

Pokročilé metody, například Microsoft GraphRAG, navíc využívají identifikaci komunit v grafu a jejich souhrny pro zodpovídání globálních otázek nad rozsáhlými dokumentovými kolekcemi.

**Výhoda:** Znalostní graf může pomoci při analýze informací, které jsou rozptýlené napříč celým korpusem a nelze je spolehlivě shrnout pouze z několika nejrelevantnějších dokumentů.

---

# 8. Výhoda č. 6: Dohledatelnost původu faktů (Provenance)

Při práci s historickými dokumenty je důležité nejen získat odpověď, ale také vědět, odkud konkrétní informace pochází.

Příklad:

```text
Jan Novák --SERVED_IN--> Rakousko-uherská armáda
```

Samotný vztah neříká, na základě jakého dokumentu byl vytvořen.

Znalostní graf však může uchovávat doplňující metadata.

Například:

```json
{
  "subject": "person_123",
  "predicate": "SERVED_IN",
  "object": "organization_456",
  "source_document": "document_187",
  "evidence": "Jan Novák nastoupil do rakousko-uherské armády.",
  "confidence": 0.95
}
```

Uvedená hodnota `confidence` je pouze ilustrativní. Aby měla praktický význam, musí být její způsob výpočtu a interpretace definován.

### Výhody uchovávání původu

- Možnost ověřit extrahované tvrzení v původním dokumentu.
- Identifikace chybných vztahů.
- Porovnávání informací z různých dokumentů.
- Podpora manuální validace historiky.
- Možnost dohledat protichůdná tvrzení.

Například dva dokumenty mohou uvádět odlišná data narození stejné osoby.

Místo automatického výběru jedné hodnoty může systém uchovat obě tvrzení spolu s jejich zdroji.

**Důležité:** Provenance není výhradní vlastností znalostních grafů. Lze ji uchovávat také v klasickém RAG nebo relační databázi. Znalostní graf však umožňuje propojit metadata přímo se strukturovanými tvrzeními.

---

# 9. Srovnání klasického RAG, agentního RAG a znalostního grafu

| Kritérium | Klasický RAG | Agentní RAG | KG + RAG |
|---|---|---|---|
| Jednoduché faktografické dotazy | Velmi vhodný | Vhodný | Vhodný |
| Multi-hop reasoning | Omezený jedním retrieval krokem | Vícekrokové vyhledávání | Procházení uložených vztahů |
| Propojení dokumentů | Přes získané texty | Iterativně | Předem propojené entity |
| Kompletní výčet faktů | Top-K může vynechat výsledky | Možnost postupného dohledávání | Systematické dotazy nad grafem |
| Entity Resolution | Není automaticky zajištěno | Lze řešit při dotazování | Lze vyřešit při konstrukci grafu |
| Opakované složité dotazy | Mohou být nákladné | Mohou být ještě nákladnější | Potenciálně levnější |
| Počáteční náklady | Relativně nízké | Relativně nízké | Vyšší |
| Provenance | Možná | Možná | Možná |
| Grafová analýza vztahů | Není přímou součástí | Vyžaduje další nástroje | Přirozeně podporována |
| Aktualizace znalostí | Aktualizace indexu | Aktualizace indexu | Aktualizace grafu |

Tabulka představuje obecné charakteristiky uvedených přístupů. Konkrétní výsledky závisí na jejich implementaci.

---

# 10. Kdy se znalostní graf nevyplatí?

Přestože znalostní grafy poskytují řadu potenciálních výhod, není jejich konstrukce vhodná pro všechny typy aplikací.

## 10.1 Jednoduché vyhledávání v dokumentech

Pokud uživatelé pokládají převážně jednoduché otázky, jejichž odpovědi jsou přímo obsaženy v dokumentech, může být klasický RAG dostatečný.

Například:

> „Co je uvedeno v dokumentu č. 157?“

> „Kdy byl vydán tento dokument?“

Pro takové dotazy nemusí konstrukce znalostního grafu přinášet významnou výhodu.

## 10.2 Vysoké náklady na konstrukci

Extrakce entit a vztahů z rozsáhlé kolekce dokumentů může být výpočetně náročná.

Je potřeba řešit:

- Rozpoznávání entit.
- Extrakci vztahů a událostí.
- Sjednocování identit.
- Validaci extrahovaných faktů.
- Aktualizaci znalostního grafu.
- Správu chyb a konfliktních informací.

U nekvalitních historických dokumentů navíc mohou být výsledky ovlivněny chybami OCR.

## 10.3 Ztráta informací při extrakci

Při převodu dokumentů do znalostního grafu může dojít ke ztrátě části původního kontextu.

Například věta:

> „Podle svědectví měšťana Jana Nováka měl Václav Svoboda vlastnit několik domů v Brně.“

Nesmí být bez dalšího převedena na jednoznačné tvrzení:

```text
Václav Svoboda --OWNED--> Domy v Brně
```

Původní text totiž obsahuje informaci, že se jedná o svědectví a nejisté tvrzení.

Proto by měl znalostní graf umožňovat uchovávání původu, nejistoty a kontextu extrahovaných informací.

---

# 11. Návrh experimentálního ověření v diplomové práci

Jednou z možností, jak prokázat přínos znalostních grafů, je experimentální porovnání několika metod vyhledávání nad stejnou kolekcí historických dokumentů.

## 11.1 Porovnávané přístupy

### A. Klasický RAG

```text
Dokumenty
    |
    v
Chunking
    |
    v
Embeddings
    |
    v
Vector Database
    |
    v
Top-K Retrieval
    |
    v
LLM
    |
    v
Odpověď
```

### B. Agentní RAG

```text
Dotaz
    |
    v
LLM Agent
    |
    v
Rozklad otázky
    |
    v
Opakované vyhledávání
    |
    v
Propojování informací
    |
    v
LLM
    |
    v
Odpověď
```

### C. Knowledge Graph + RAG

```text
Dokumenty
    |
    v
Extrakce entit a vztahů
    |
    v
Entity Resolution
    |
    v
Knowledge Graph
    |
    v
Grafové vyhledávání
    |
    v
Zdrojové dokumenty
    |
    v
LLM
    |
    v
Odpověď
```

## 11.2 Typy testovacích otázek

| Kategorie | Příklad |
|---|---|
| Jednoduchý fakt | Kdy se narodil Jan Novák? |
| Multi-hop | Kdo byl zetěm vlastníka domu v Brně? |
| Propojení dokumentů | Které osoby vystupují ve více majetkových záznamech? |
| Entity Resolution | Jaký majetek vlastnil Jan Novák uváděný pod různými jmény? |
| Kompletní výčet | Které osoby vlastnily domy v Brně v roce 1521? |
| Globální analýza | Jaké typy majetkových sporů se v dokumentech opakují? |

## 11.3 Vyhodnocované metriky

**Kvalita odpovědí:**
- Správnost získaných faktů.
- Úplnost odpovědí.
- Precision, Recall a F1 při vyhledávání strukturovaných faktů.
- Správnost uvedených zdrojů.

**Výpočetní náročnost:**
- Počet volání LLM.
- Počet spotřebovaných tokenů.
- Průměrná cena dotazu.
- Čas potřebný k vytvoření odpovědi.
- Počáteční náklady na přípravu systému.

**Škálovatelnost:**
- Chování při rostoucím počtu dokumentů.
- Náklady při opakovaném dotazování.
- Náročnost aktualizace uložených znalostí.

Důležité je použít stejný referenční dataset a vytvořit testovací otázky se známými správnými odpověďmi.

---

# 12. Je skutečně nezbytné použít znalostní graf?

Je potřeba rozlišovat dva samostatné problémy:

**1. Proč extrahovat strukturované informace z dokumentů?**

Strukturovaná reprezentace umožňuje opakované využívání faktů, jejich propojování, validaci a efektivní dotazování.

**2. Proč pro strukturované informace zvolit právě znalostní graf?**

Znalostní graf poskytuje přirozenou reprezentaci entit a jejich vzájemných vztahů.

Výhodný může být zejména v situacích, kdy:

- Počet a typy vztahů mezi entitami jsou proměnlivé.
- Dotazy vyžadují procházení víceúrovňových vazeb.
- Je potřeba propojovat informace z heterogenních dokumentů.
- Uživatelé potřebují zkoumat vztahy mezi entitami.
- Struktura znalostí se postupně rozšiřuje.

Samotná potřeba strukturovaných faktů však neznamená, že je nutné použít grafovou databázi.

Alternativou mohou být relační databáze, dokumentové databáze nebo jiné strukturované reprezentace.

Výběr vhodného datového modelu by proto měl vycházet z charakteru extrahovaných informací a požadovaných dotazů.

---

# 13. Shrnutí hlavních přínosů

| Výhoda | Přínos |
|---|---|
| **Multi-hop reasoning** | Propojování informací z různých dokumentů |
| **Systematické dotazování** | Vyhledávání všech uložených faktů splňujících podmínky |
| **Entity Resolution** | Sjednocování různých označení stejných entit |
| **Nižší náklady na opakované dotazy** | Opakované využívání již extrahovaných znalostí |
| **Globální analýza** | Identifikace souvislostí a vzorců napříč kolekcí |
| **Provenance** | Dohledatelnost původu a možnost validace faktů |
| **Grafová analýza** | Zkoumání nepřímých vztahů mezi entitami |
| **Strukturovaná reprezentace** | Přímé dotazování nad entitami a vztahy, uzivatel by mohl hledat veci primo pres graf o kterych ani predem nevi ze by chtel vedet  |
| **Doporucovani vysledku** | aplikace by mohla automaticky doporucovat relevantni dokuemnty |
| **objevovani skrytych souvislosti** | pro zkoumani a zjistovani novych hypotez |

## Závěr

Znalostní grafy představují vhodný přístup pro reprezentaci informací extrahovaných z rozsáhlých kolekcí historických dokumentů, zejména pokud je cílem nejen vyhledávání textů, ale také zkoumání vzájemných vztahů mezi entitami.

Jejich hlavní potenciální výhodou oproti jednoduchému vektorovému RAG je možnost předem extrahovat a propojit fakta, která jsou rozptýlená mezi různými dokumenty.

To umožňuje systematické zpracování komplexních dotazů, opakované využívání extrahovaných znalostí a potenciální snížení nákladů na dotazování.

Současně je nutné zohlednit náklady na konstrukci znalostního grafu, správnost extrahovaných informací a možnost ztráty původního kontextu.

Klasický RAG je primárně zaměřen na získávání informací relevantních k uživatelskému dotazu. Znalostní graf oproti tomu umožňuje nejen vyhledávat konkrétní fakta, ale také systematicky analyzovat vztahy mezi entitami a objevovat souvislosti, které uživatel předem nezná, a proto by na ně nemusel formulovat konkrétní dotaz.

V případě rozsáhlých historických archivů může znalostní graf sloužit jako nástroj pro explorativní analýzu, například při zkoumání historických sociálních sítí, obchodních vztahů, rodinných vazeb nebo vývoje událostí.
