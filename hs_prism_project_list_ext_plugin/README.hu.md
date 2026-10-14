# Prism Project List Extension

[English](README.md) · **Magyar**

Egy kis Prism-plugin, ami több teret ad a projektlistának: átméretezhető ablak, állítható kártyarács, teljes előnézetek és az aktuális projekt jól látható adatai.

[Telepítés](#telepítés) · [Használat](#használat) · [Beállítások](#beállítások) · [Kompatibilitás](#kompatibilitás)

## Telepítés

1. Tartsd ezt az önálló **`hs_prism_project_list_ext_plugin`** mappát az egyedi Prism-pluginjeid között.
2. A **Prism Settings → User → Plugins** alatt kattints az **Add existing plugin…** gombra (mappaikon), és ezt a mappát válaszd ki. Ha indításkor is szeretnéd betölteni, maradjon bekapcsolva az **Auto Load**.
3. Telepítés vagy frissítés után indítsd újra a Prismet és az azt betöltő DCC-alkalmazásokat.

A kiválasztott mappának tartalmaznia kell a `Scripts/Prism_hs_prism_project_list_ext_plugin_init.py` fájlt. A pluginmappát válaszd, ne a `Scripts` almappát.

## Használat

- A Project Browser aktuális projektet mutató gombjával nyisd meg a projektlistát.
- Méretezd át az ablakot, és a projektszám mellett állítsd a **Cards per row** értékét: **1–20** választható, az alapérték **3**.
- A megszokott módon keress és nyiss meg projekteket. Bezárás és újranyitás után visszaáll az ablak mérete és pozíciója.

A plugin a projektlistát egészíti ki, nem a Scenefiles, Products vagy Media nézetet. A keresést, kijelölést, kedvenceket, projektlétrehozást és megnyitást továbbra is a Prism kezeli. A telepített Prism-forrásfájlokat nem módosítja.

## Beállítások

A plugin a **Prism felhasználói beállításmappájának `ProjectBrowserExt` almappájában** tárolja a beállításait, a telepítési helyétől függetlenül.

| Fájl | Tartalma |
|---|---|
| `project_list_window.json` | Ablakméret és pozíció; automatikusan mentődik. |
| `project_card_grid.json` | Soronkénti kártyaszám; az érték módosításakor mentődik. |
| `appearance.json` | Kézzel szerkeszthető scrollbar-szélesség. |

Az első listamegnyitás létrehozza az `appearance.json` fájlt `{"scrollbar_width": 18}` tartalommal. **10–40 közötti egész szám**, vagy az eredeti Prism-témaszélességhez `null` használható. Mentés után zárd be és nyisd újra a listát. Hibás értéknél a plugin 18-at használ, a fájlodat pedig nem írja felül.

## Kompatibilitás

| Környezet | Ellenőrzés |
|---|---|
| Windows · Prism **2.1.3** · PySide6 **6.11.1** | Sikeres automata és izolált Prism/Qt-próbák. |
| DCC, többmonitoros környezet és DPI | Különböző felbontásokkal és DPI-beállításokkal tesztelve. |
| Linux | A kód alapján várhatóan kompatibilis; még nem tesztelt. |
| Más Prism-verzió, Qt-binding és operációs rendszer | Még nincs ellenőrizve. |

**Wayland:** Linuxon, a Qt natív Wayland-megjelenítésével a mentett ablakpozíció visszaállítása nem feltétlenül működik, mert az ablak elhelyezését általában az ablakkezelő szabályozza. Részletek a [Qt dokumentációjában](https://doc.qt.io/qt-6/application-windows.html).

Nem kell külön Python-csomagokat telepíteni a Prismhez. A plugin saját moduljait, a Python standard library-t és a Prism/Qt környezetét használja.

## Hibakeresés

Ha nem jelenik meg a kiegészítés, ellenőrizd, hogy a plugin be van-e töltve, a megfelelő mappát választottad-e, és újraindítottad-e a Prismet/DCC-t a telepítés vagy frissítés után.

A figyelmeztetések és hibák a `ProjectBrowserExt/pbe_debug.log` fájlba kerülnek. Részletes diagnosztikához kapcsold be a Prism debugmódját és a DEBUG üzeneteket engedő naplózási szintet.

Hibajelentéshez add meg a Prism verzióját, a DCC nevét/verzióját, az operációs rendszert, az előidézés lépéseit és egy képernyőképet vagy releváns naplórészletet.

## Licenc

[GNU GPL kizárólag 3-as verzió, kiegészítő Prism/DCC-összekapcsolási engedéllyel](LICENSE).
