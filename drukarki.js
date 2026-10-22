// Obszary druku – wspólne dla konfiguratora (przeglądarka) i druk.py. Wartości z profili Bambu Studio
// (github.com/bambulab/BambuStudio, resources/profiles/BBL/machine/*.json) i danych producentów.
//   bed     = [szer., gł.] całego stołu (printable_area) – jego środek to punkt, na który slicer centruje import
//   area    = [x0, y0, x1, y1] – obszar, w którym układamy części (H2D/H2C: przyjęte 325×300 na środku stołu)
//   area_max = opcjonalny większy obszar (H2D/H2C: pełna głębokość stołu 320 mm) – tylko dla pojedynczej części,
//             która nie mieści się w area; dostaje własną płytę i ostrzeżenie zamiast „za duża”
//   h       = wysokość druku (mm)
//   exclude = strefy zakazane (bed_exclude_area) – nigdy nie kładziemy tam części
//   wrap    = strefy wykrywania owijania (wrapping_exclude_area) – omijane, gdy się da (błąd tylko przy włączonym wykrywaniu)
//   note    = podpowiedź wyświetlana w konfiguratorze i w plyty.txt
//   nozzle  = left/right: wariant jednej dyszy – w slicerze trzeba przypisać filament do tej dyszy
//
// Bambu Studio przy imporcie 3MF spoza Bambu przesuwa całą grupę tak, by środek jej bryły otaczającej wypadł
// na środku stołu (Plater.cpp: center_instances_around_point(bed_center)), więc druk.py zapisuje płyty już
// wyśrodkowane. H2D/H2C: przyjęty obszar układania 325×300 mm na środku stołu (zasięg jednej dyszy to 325 mm,
// 300 mm głębokości omija strefę przy tylnej krawędzi). Po imporcie część może wejść w pas jednej dyszy –
// wtedy wystarczy przesunąć grupę o kilkanaście mm w slicerze.
window.VAULT_PRINTERS = {
  "h2s":     { "name": "Bambu Lab H2S", "bed": [340, 320], "area": [0, 0, 340, 320], "h": 340, "exclude": [], "wrap": [[172.3, 302, 232.5, 322]] },
  "h2d":     { "note": "Obszar 325×300 to zasięg jednej dyszy – szeroka płyta może po imporcie zachodzić na pas jednej dyszy; wtedy przesuń całą grupę w bok o kilkanaście mm albo przypisz filament do odpowiedniej dyszy.", "name": "Bambu Lab H2D", "bed": [350, 320], "area": [12.5, 10, 337.5, 310], "area_max": [12.5, 0, 337.5, 320], "h": 320, "exclude": [], "wrap": [[145, 310, 256, 326]] },
  "h2c":     { "note": "Obszar 325×300 to zasięg jednej dyszy – szeroka płyta może po imporcie zachodzić na pas jednej dyszy; wtedy przesuń całą grupę w bok o kilkanaście mm albo przypisz filament do odpowiedniej dyszy.", "name": "Bambu Lab H2C", "bed": [330, 320], "area": [2.5, 10, 327.5, 310], "area_max": [2.5, 0, 327.5, 320], "h": 320, "exclude": [], "wrap": [[145, 310, 251, 326]] },
  "x2d":     { "name": "Bambu Lab X2D – obie dysze", "bed": [256, 256], "area": [20.5, 0, 256, 256], "h": 256, "exclude": [], "wrap": [] },
  "x2d_l":   { "nozzle": "left", "name": "Bambu Lab X2D – tylko lewa dysza", "bed": [256, 256], "area": [0, 0, 256, 256], "h": 261, "exclude": [], "wrap": [] },
  "x1":      { "name": "Bambu Lab X1 / P1", "bed": [256, 256], "area": [0, 0, 256, 256], "h": 250, "exclude": [[0, 0, 18, 28]], "wrap": [] },
  "p2s":     { "name": "Bambu Lab P2S", "bed": [256, 256], "area": [0, 0, 256, 256], "h": 256, "exclude": [], "wrap": [[153, 235, 216, 256]] },
  "a1":      { "name": "Bambu Lab A1", "bed": [256, 256], "area": [0, 0, 256, 256], "h": 256, "exclude": [], "wrap": [] },
  "a1mini":  { "name": "Bambu Lab A1 mini", "bed": [180, 180], "area": [0, 0, 180, 180], "h": 180, "exclude": [], "wrap": [] },
  "coreone": { "name": "Prusa Core One", "bed": [250, 220], "area": [0, 0, 250, 220], "h": 270, "exclude": [], "wrap": [] },
  "mk4":     { "name": "Prusa MK4", "bed": [250, 210], "area": [0, 0, 250, 210], "h": 220, "exclude": [], "wrap": [] }
};
