![Hypershade Prism Tools — Project List Extension](assets/header-01.svg)

# Prism Project List Extension

[English](README.md) · **Magyar**

Egy kis Prism-plugin, amely több helyet ad a projektlistának: átméretezhető ablak, állítható kártyarács és az aktuális projekt jól látható adatai.


[Telepítés](#telepítés) · [Használat](#használat) · [Beállítások](#beállítások) · [Kompatibilitás](#kompatibilitás)

<br>

| Eredeti Prism-projektlista | Project List Extension |
|---|---|
| ![Eredeti Prism-projektlista három oszloppal és vágott előnézetekkel](assets/project_list_view_0000_before.png) | ![Kibővített Prism-projektlista, váltakozva négy és két kártyával soronként](assets/project_list_view_after.gif) |
| Fix Három oszlop, vágott thumbnailek, fix ablak méret. | Átméretezhető ablak, állítható rács és teljes előnézetek. |

## Mit változtat meg?

| Funkció | Mit csinál? |
|---|---|
| Átméretezhető ablak | A projektlista méretét és pozícióját szabadon állíthatod; az ablak megjegyzi őket. |
| Állítható kártyarács | **Soronként 1–20 kártya** választható; a kártyák együtt méreteződnek az ablakkal. |
| Teljes előnézet | A thumbnail megtartja az arányait, és levágás nélkül látszik. |
| Aktuális projekt | A lista felett megjelenik az aktív projekt neve és útvonala. |
| Listaösszegzés | Látható a találatok száma és az aktuális keresési szöveg. |
| Scrollbar szélessége | Egy egyszerű JSON-beállítással szélesebb függőleges görgetősávot használhatsz. |

A plugin a **Project Browserből megnyitható projektlistát** egészíti ki, nem a Scenefiles, Products vagy Media nézetet. A keresést, kijelölést, kedvenceket, projektlétrehozást és megnyitást továbbra is a Prism kezeli. A telepített Prism-forrásfájlokat nem módosítja.

## Telepítés

1. Töltsd le vagy klónozd ezt a repositoryt.
2. Másold a belső **`hs_prism_project_list_ext_plugin`** mappát oda, ahol az egyedi Prism-pluginjeidet tartod.
3. Nyisd meg a **Prism Settings → User → Plugins** oldalt, kattints az **Add existing plugin…** gombra (mappaikon), és válaszd ki ezt a mappát. Ha indításkor is szeretnéd betölteni, maradjon bekapcsolva az **Auto Load** ennél a pluginnél.
4. Indítsd újra a Prismet és a Prismet betöltő DCC-alkalmazásokat, majd nyisd meg a projektlistát a Project Browserből.

A kiválasztott mappának tartalmaznia kell a `Scripts/Prism_hs_prism_project_list_ext_plugin_init.py` fájlt. A belső pluginmappát válaszd, ne a repository gyökerét vagy a `Scripts` almappát.

## Használat

- A Project Browser aktuális projektet mutató gombjával nyisd meg a projektlistát.
- Méretezd át az ablakot, és a projektszám mellett állítsd a **Cards per row** értékét: **1–20** választható, az alapérték **3**.
- A megszokott módon keress és nyiss meg projekteket. Bezárás és újranyitás után visszaáll az ablak mérete és pozíciója.

**Példa: két kártya soronként**

![Ugyanazok a demóprojektek, soronként két kártyával és nagyobb előnézetekkel](assets/project_list_view_0002_after2.png)

## Beállítások

A plugin a **Prism felhasználói beállításmappájának `ProjectBrowserExt` almappájában** tárolja a beállításait, a telepítési helyétől függetlenül.

| Fájl | Tartalma |
|---|---|
| `project_list_window.json` | Ablakméret és pozíció; automatikusan mentődik. |
| `project_card_grid.json` | Soronkénti kártyaszám; az érték módosításakor mentődik. |
| `appearance.json` | Kézzel szerkeszthető scrollbar-szélesség. |

Az első projektlista-megnyitás létrehozza az `appearance.json` fájlt ezzel az alapértékkel:

```json
{
  "scrollbar_width": 18
}
```

**10 és 40 közötti egész számot** adhatsz meg; `null` esetén a Prism eredeti témaszélessége érvényesül. Mentés után zárd be és nyisd újra a projektlistát. Hibás értéknél a plugin 18-at használ, a fájlodat pedig nem írja felül.

## Kompatibilitás

| Környezet | Ellenőrzés |
|---|---|
| Windows · Prism **2.1.3** · PySide6 **6.11.1** | Sikeres automata és izolált Prism/Qt-próbák. |
| DCC, többmonitoros környezet és DPI | Különböző felbontásokkal és DPI-beállításokkal tesztelve. |
| Linux | A kód alapján várhatóan kompatibilis; még nem tesztelt. |
| Más Prism-verzió, Qt-binding és operációs rendszer | Még nincs ellenőrizve. |

**Wayland:** Linuxon, a Qt natív Wayland-megjelenítésével a mentett ablakpozíció visszaállítása nem feltétlenül működik, mert az ablak elhelyezését általában az ablakkezelő szabályozza. Részletek a [Qt dokumentációjában](https://doc.qt.io/qt-6/application-windows.html).

Nem kell külön Python-csomagokat telepíteni a Prismhez. A plugin a Python standard library-t és a Prism/Qt környezetét használja.

## Hibakeresés

Ha nem jelenik meg a kiegészítés, ellenőrizd, hogy az új plugin neve szerepel-e a betöltött pluginok között, a megfelelő mappát választottad-e, és újraindítottad-e a Prismet/DCC-t a telepítés vagy frissítés után.

A figyelmeztetések és hibák a `ProjectBrowserExt/pbe_debug.log` fájlba kerülnek. Részletes diagnosztikához kapcsold be a Prism debugmódját és a DEBUG üzeneteket engedő naplózási szintet. Részletek a [telepített plugin útmutatójában](hs_prism_project_list_ext_plugin/README.hu.md).

Hibajelentéshez add meg a Prism verzióját, a DCC nevét/verzióját, az operációs rendszert, az előidézés lépéseit és egy képernyőképet vagy releváns naplórészletet.

## Fejlesztés

A telepíthető plugin önálló. A modulok felépítése és a diagnosztikai naplózás az [angol fejlesztői útmutatóban](development.md) található.

## Licenc

[GNU GPL kizárólag 3-as verzió, kiegészítő Prism/DCC-összekapcsolási engedéllyel](LICENSE).
