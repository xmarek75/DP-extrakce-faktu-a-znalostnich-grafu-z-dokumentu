2.6 Evidence Attribution – odkud daný vztah pochází?
Tohle považuji za jeden z nejdůležitějších konceptů celé práce.

Každý extrahovaný vztah by měl mít přiřazený důkaz z původního dokumentu.

Představ si, že v grafu existuje:
Jan Novák --SERVED_IN--> Rakousko-uherská armáda

Bez dalších informací nevíš, proč tento vztah existuje.

Autoři proto uchovávají také úsek původního textu.

Například takto:
{
  "source": "person_123",
  "target": "organization_456",
  "relation": "SERVED_IN",
  "evidence": "Jan Novák nastoupil v roce 1914 do rakousko-uherské armády."
}

Jde o ilustrační JSON, nikoliv přesný exportní formát autorů.

Výhody tohoto přístupu jsou zásadní.

Pokud historik otevře graf a uvidí podezřelý vztah, může dohledat původní tvrzení a ověřit jeho správnost.

Tím vzniká systém, který umožňuje nejen automaticky extrahovat informace, ale také kontrolovat jejich původ a důvěryhodnost.

Autoři tento přístup označují za důležitou součást human-in-the-loop validace.

Pro tvoji práci bych doporučil tuto myšlenku rozšířit ještě o identifikátor dokumentu a pozici v textu:

  "subject": "person_123",
  "predicate": "SERVED_IN",
  "object": "organization_456",
  "source_document": "document_001",
  "evidence": "Jan Novák nastoupil v roce 1914 do rakousko-uherské armády.",
  "start_offset": 1450,
  "end_offset": 1509



Jakou roli by mohl mít AI agent?
Agent by mohl podle typu otázky rozhodovat, jaké zdroje a nástroje použije.

Například uživatel zadá:
Najdi všechny dokumenty, které spojují Jana Nováka s Karlem Svobodou.

Agent může nejdříve vyhledat obě entity ve znalostním grafu.

Poté zjistí, jestli mezi nimi existuje přímý vztah nebo spojení přes další entity.

Následně načte dokumenty obsahující důkazy jednotlivých vztahů.

Nakonec pomocí LLM sestaví odpověď s odkazy na zdroje.

Tohle je návrh možného využití výsledného grafu, nikoliv funkce, kterou autoři studie implementovali.