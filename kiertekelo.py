import cv2
import numpy as np
from typing import List, Tuple, Dict
import pytesseract
import json
import re
from datetime import datetime


class TesztlapKiertekelo:
    
    def __init__(self, kep_utvonal: str, tesseract_path: str = None):
        """Kép betöltése és OCR inicializálás."""
        self.kep_utvonal = kep_utvonal
        self.tesseract_path = tesseract_path
        self.kep = cv2.imread(kep_utvonal)
        if self.kep is None:
            raise ValueError(f"Nem sikerült betölteni a képet: {kep_utvonal}")
        
        self.szurke = cv2.cvtColor(self.kep, cv2.COLOR_BGR2GRAY)
        self.magassag, self.szelesseg = self.szurke.shape
        self.sarkok = []
        self.neptun_kod = None
        self.debug_checkboxok = []
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
    def sarkok_keresese(self) -> List[Tuple[int, int]]:
        """Sarokjelek felismerése a képen."""
        _, binarizalt = cv2.threshold(self.szurke, 127, 255, cv2.THRESH_BINARY_INV)
        konturok, _ = cv2.findContours(binarizalt, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        sarok_jelolok = []
        
        # Skálázási tényező a kép mérete alapján
        skala = self.szelesseg / 600  # 600 px = 72 DPI A4 szélesség
        min_terulet = int(500 * skala * skala)
        max_terulet = int(5000 * skala * skala)
        
        for kontur in konturok:
            terulet = cv2.contourArea(kontur)
            # Sarokjelölők mérete (skálázva)
            if min_terulet < terulet < max_terulet:
                x, y, w, h = cv2.boundingRect(kontur)
                # Ellenőrizzük, hogy négyzet alakú-e
                arany = float(w) / h if h > 0 else 0
                if 0.8 < arany < 1.2:
                    kozeppont = (x + w // 2, y + h // 2)
                    sarok_jelolok.append((kozeppont, terulet))
        
        # Rendezés terület szerint és a 4 legnagyobb kiválasztása
        sarok_jelolok.sort(key=lambda x: x[1], reverse=True)
        self.sarkok = [s[0] for s in sarok_jelolok[:4]]
        
        # Rendezés pozíció szerint: bal felső, jobb felső, bal alsó, jobb alsó
        if len(self.sarkok) == 4:
            self.sarkok.sort(key=lambda p: (p[1], p[0]))  # y majd x szerint
            felso = sorted(self.sarkok[:2], key=lambda p: p[0])  # felső kettő x szerint
            also = sorted(self.sarkok[2:], key=lambda p: p[0])   # alsó kettő x szerint
            self.sarkok = felso + also
        
        return self.sarkok
    
    def perspektiva_korrekcio(self):
        """Perspektíva javítás a sarokjelek alapján."""
        if len(self.sarkok) != 4:
            print("Figyelmeztetés: Nem található mind a 4 sarokjelölő!")
            return
        
        pts1 = np.float32(self.sarkok)
        pts2 = np.float32([
            [0, 0],
            [self.szelesseg, 0],
            [0, self.magassag],
            [self.szelesseg, self.magassag]
        ])
        
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        self.szurke = cv2.warpPerspective(self.szurke, matrix, (self.szelesseg, self.magassag))
        self.kep = cv2.warpPerspective(self.kep, matrix, (self.szelesseg, self.magassag))
    
    def negyzetek_keresese(self, regio: Tuple[int, int, int, int]) -> List[Tuple[int, int, int, int]]:
        """Jelölőnégyzetek felismerése megadott területen."""
        x, y, w, h = regio
        roi = self.szurke[y:y+h, x:x+w]
        
        _, binarizalt = cv2.threshold(roi, 127, 255, cv2.THRESH_BINARY_INV)
        konturok, _ = cv2.findContours(binarizalt, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        negyzetek = []
        
        skala = self.szelesseg / 600
        min_terulet = int(50 * skala * skala)
        max_terulet = int(500 * skala * skala)
        
        for kontur in konturok:
            terulet = cv2.contourArea(kontur)
            if min_terulet < terulet < max_terulet:
                bx, by, bw, bh = cv2.boundingRect(kontur)
                arany = float(bw) / bh if bh > 0 else 0
                if 0.7 < arany < 1.3:
                    negyzetek.append((x + bx, y + by, bw, bh))
        
        negyzetek.sort(key=lambda n: n[1])
        
        return negyzetek
    
    def negyzet_ki_van_e_jelolve(self, negyzet: Tuple[int, int, int, int], kuszob: float = 0.25, debug: bool = False) -> Tuple[bool, float]:
        """Ellenőrzi, hogy egy négyzet ki van-e jelölve."""
        x, y, w, h = negyzet
        # Nagyobb margó a négyzet széléről, hogy a keretet kihagyjuk
        margin = max(3, min(w, h) // 4)
        roi = self.szurke[y+margin:y+h-margin, x+margin:x+w-margin]
        
        if roi.size == 0:
            return False, 0.0
        
        # Adaptív binarizálás a jobb eredményért
        binarizalt = cv2.adaptiveThreshold(roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY_INV, 11, 2)
        
        # Fekete pixelek száma
        fekete_pixelek = cv2.countNonZero(binarizalt)
        osszes_pixel = roi.shape[0] * roi.shape[1]
        
        # Ha a fekete pixelek aránya meghaladja a küszöböt, bejelöltnek tekintjük
        arany = fekete_pixelek / osszes_pixel if osszes_pixel > 0 else 0
        
        if debug:
            print(f"      Négyzet ({x},{y},{w},{h}): fekete arány = {arany:.3f}, bejelölve = {arany > kuszob}")
        
        return arany > kuszob, arany
    
    def keretek_keresese(self, debug: bool = True) -> List[Tuple[int, int, int, int]]:
        """Kérdések kereteinek megkeresése."""
        elek = cv2.Canny(self.szurke, 50, 150)
        konturok, _ = cv2.findContours(elek, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        keretek = []
        
        skala = self.szelesseg / 600
        min_terulet = int(10000 * skala * skala)
        
        for kontur in konturok:
            terulet = cv2.contourArea(kontur)
            if terulet > min_terulet:
                x, y, w, h = cv2.boundingRect(kontur)
                arany = float(w) / h if h > 0 else 0
                if arany > 2:
                    keretek.append((x, y, w, h))
                    if debug:
                        print(f"      Keret talált: x={x}, y={y}, w={w}, h={h}, terület={terulet:.0f}, arány={arany:.2f}")
        
        keretek.sort(key=lambda k: k[1])
        
        print(f"   Talált keretek: {len(keretek)}")
        
        return keretek
    
    def kerdes_tipusanak_meghatarozasa(self, keret: Tuple[int, int, int, int]) -> str:
        """Kérdés típusának meghatározása a magasság alapján."""
        x, y, w, h = keret
        
        # Skálázási tényező
        skala = self.szelesseg / 600
        kuszob = int(80 * skala)
        
        # Magasság alapú döntés (skálázva)
        # Igaz/Hamis kérdések alacsonyabbak (~40-60 px 72 DPI-n, ~167-250 px 300 DPI-n)
        # Feleletválasztós kérdések magasabbak (~100+ px 72 DPI-n, ~417+ px 300 DPI-n)
        if h < kuszob:
            return "IH"
        else:
            return "FV"
    
    def igaz_hamis_kiertekeles(self, keretek: List[Tuple[int, int, int, int]], debug: bool = False) -> Dict[int, str]:
        """Igaz/Hamis kérdések kiértékelése."""
        eredmenyek = {}
        ih_sorszam = 1
        
        if debug:
            print("Igaz/Hamis kérdések kiértékelése...")
        
        for keret in keretek:
            if self.kerdes_tipusanak_meghatarozasa(keret) != "IH":
                continue
                
            x, y, w, h = keret
            
            if debug:
                print(f"   Kérdés {ih_sorszam} (keret y={y} h={h}):")
            
            regio = (x + int(w * 0.6), y, int(w * 0.4), h)
            
            negyzetek = self.negyzetek_keresese(regio)
            negyzetek.sort(key=lambda n: n[0])
            
            if len(negyzetek) >= 2:
                igaz_bejelolve, igaz_arany = self.negyzet_ki_van_e_jelolve(negyzetek[0], debug=debug)
                hamis_bejelolve, hamis_arany = self.negyzet_ki_van_e_jelolve(negyzetek[1], debug=debug)
                
                self.debug_checkboxok.append((*negyzetek[0], igaz_bejelolve, igaz_arany, "IH"))
                self.debug_checkboxok.append((*negyzetek[1], hamis_bejelolve, hamis_arany, "IH"))
                
                if debug:
                    print(f"      Igaz: {igaz_arany:.3f}, Hamis: {hamis_arany:.3f}")
                
                if igaz_bejelolve and not hamis_bejelolve:
                    eredmenyek[ih_sorszam] = "Igaz"
                elif hamis_bejelolve and not igaz_bejelolve:
                    eredmenyek[ih_sorszam] = "Hamis"
                elif igaz_bejelolve and hamis_bejelolve:
                    eredmenyek[ih_sorszam] = "Hibás (mindkettő bejelölve)"
                else:
                    eredmenyek[ih_sorszam] = "Nincs válasz"
            else:
                eredmenyek[ih_sorszam] = "Nem található négyzet"
            
            ih_sorszam += 1
        
        return eredmenyek
    
    def feleletvalasztos_kiertekeles(self, keretek: List[Tuple[int, int, int, int]], debug: bool = False) -> Dict[int, int]:
        """Feleletválasztós kérdések kiértékelése."""
        eredmenyek = {}
        fv_sorszam = 1
        
        if debug:
            print("Feleletválasztós kérdések kiértékelése...")
        
        for keret in keretek:
            # Ellenőrizzük, hogy ez feleletválasztós típusú kérdés-e
            if self.kerdes_tipusanak_meghatarozasa(keret) != "FV":
                continue
                
            x, y, w, h = keret
            
            if debug:
                print(f"   Kérdés {fv_sorszam} (keret y={y} h={h}):")
            
            # Bal oldali rész vizsgálata (ahol a válasz négyzetek vannak)
            # A kereten BELÜL keressük a checkboxokat
            regio = (x, y, int(w * 0.3), h)
            
            negyzetek = self.negyzetek_keresese(regio)
            
            # Szűrés: csak a 4 legalapvetőbb négyzetet tartjuk meg
            # (néha extra kis négyzetek is detektálódnak)
            if len(negyzetek) > 4:
                # Terület szerinti szűrés: csak a legnagyobb 4 négyzetet vesszük
                negyzetek_terulettel = [(n, n[2] * n[3]) for n in negyzetek]
                negyzetek_terulettel.sort(key=lambda x: x[1], reverse=True)
                negyzetek = [n[0] for n in negyzetek_terulettel[:4]]
                # Újra rendezés Y koordináta szerint
                negyzetek.sort(key=lambda n: n[1])
                
                if debug:
                    print(f"      {len(negyzetek)} négyzet a szűrés után")
            
            valasz_index = -1
            bejelolt_szam = 0
            valasz_aranyok = []
            
            for j, negyzet in enumerate(negyzetek[:4]):  # Maximum 4 válasz
                bejelolve, arany = self.negyzet_ki_van_e_jelolve(negyzet, debug=debug)
                valasz_aranyok.append(arany)
                
                # Checkbox adatok mentése debug képhez
                betu = chr(65 + j)  # A, B, C, D
                self.debug_checkboxok.append((*negyzet, bejelolve, arany, f"FV-{betu}"))
                
                if bejelolve:
                    valasz_index = j
                    bejelolt_szam += 1
            
            if debug and valasz_aranyok:
                print(f"      Arányok: {[f'{a:.3f}' for a in valasz_aranyok]}")
                print(f"      Bejelölt válasz: {valasz_index if bejelolt_szam == 1 else 'HIBA'}")
            
            if bejelolt_szam == 1:
                eredmenyek[fv_sorszam] = valasz_index
            elif bejelolt_szam > 1:
                eredmenyek[fv_sorszam] = -2  # Többszörös válasz
            else:
                eredmenyek[fv_sorszam] = -1  # Nincs válasz
            
            fv_sorszam += 1
        
        return eredmenyek
    
    def neptun_kod_kiolvasasa(self, debug: bool = False) -> str:
        """Neptun kód felismerése OCR-rel."""
        keretezett_terulet = self.neptun_keret_keresese(debug)
        
        if keretezett_terulet is not None:
            neptun_x, neptun_y, neptun_w, neptun_h = keretezett_terulet
            if debug:
                print(f"   Neptun keret detektálva: ({neptun_x}, {neptun_y}, {neptun_w}, {neptun_h})")
        else:
            if debug:
                print("   Neptun keret nem található, becsült koordináták használata")
            neptun_x = int(self.szelesseg * 0.65)
            neptun_y = int(self.magassag * 0.02)
            neptun_w = int(self.szelesseg * 0.30)
            neptun_h = int(self.magassag * 0.05)
        
        roi = self.szurke[neptun_y:neptun_y+neptun_h, neptun_x:neptun_x+neptun_w]
        
        if debug:
            print(f"   ROI terület: ({neptun_x}, {neptun_y}, {neptun_w}, {neptun_h})")
            print(f"   ROI méret: {roi.shape}")
        
        roi_nagyitott = cv2.resize(roi, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        
        _, binarizalt1 = cv2.threshold(roi_nagyitott, 140, 255, cv2.THRESH_BINARY)
        _, binarizalt2 = cv2.threshold(roi_nagyitott, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kontraszt = cv2.convertScaleAbs(roi_nagyitott, alpha=2.0, beta=-80)
        _, binarizalt3 = cv2.threshold(kontraszt, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kontraszt2 = cv2.convertScaleAbs(roi_nagyitott, alpha=2.8, beta=-120)
        _, binarizalt4 = cv2.threshold(kontraszt2, 130, 255, cv2.THRESH_BINARY)
        
        binarizalt5 = cv2.adaptiveThreshold(roi_nagyitott, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                            cv2.THRESH_BINARY, 15, 5)
        
        if debug:
            cv2.imwrite("debug/debug_neptun_bin1.png", binarizalt1)
            cv2.imwrite("debug/debug_neptun_bin2.png", binarizalt2)
            cv2.imwrite("debug/debug_neptun_bin3.png", binarizalt3)
            cv2.imwrite("debug/debug_neptun_bin4.png", binarizalt4)
            cv2.imwrite("debug/debug_neptun_bin5.png", binarizalt5)
        
        # OCR beállítások - Neptun kód specifikus
        config_variations = [
            r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            r'--oem 1 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            r'--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        ]
        
        kepek = [binarizalt1, binarizalt2, binarizalt3, binarizalt4, binarizalt5]
        legjobb_eredmeny = ""
        legjobb_hossz = 0
        
        try:
            import pytesseract
            # Ha van tesseract_cmd beállítva
            if self.tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            
            # Próbáljuk ki az összes kombinációt
            lehetseges_eredmenyek = {}  # Szótár: eredmény -> gyakoriság
            
            for i, kep in enumerate(kepek):
                for j, config in enumerate(config_variations):
                    try:
                        szoveg = pytesseract.image_to_string(kep, config=config)
                        szoveg = szoveg.strip().upper()
                        szoveg = re.sub(r'[^A-Z0-9]', '', szoveg)
                        
                        if debug:
                            print(f"   Kísérlet {i+1}-{j+1}: '{szoveg}' (hossz: {len(szoveg)})")
                        
                        if len(szoveg) == 6:
                            if szoveg in lehetseges_eredmenyek:
                                lehetseges_eredmenyek[szoveg] += 1
                            else:
                                lehetseges_eredmenyek[szoveg] = 1
                        
                        if len(szoveg) > 6:
                            szoveg_6 = szoveg[:6]
                            if szoveg_6 in lehetseges_eredmenyek:
                                lehetseges_eredmenyek[szoveg_6] += 1
                            else:
                                lehetseges_eredmenyek[szoveg_6] = 1
                        
                        if len(szoveg) > legjobb_hossz:
                            legjobb_eredmeny = szoveg
                            legjobb_hossz = len(szoveg)
                    
                    except Exception as e:
                        if debug:
                            print(f"   Kísérlet {i+1}-{j+1} sikertelen: {e}")
                        continue
            
            if lehetseges_eredmenyek:
                if debug:
                    print(f"\n   Lehetséges 6 karakteres eredmények:")
                    for eredmeny, gyakori in sorted(lehetseges_eredmenyek.items(), key=lambda x: -x[1]):
                        szamok_szama = sum(c.isdigit() for c in eredmeny)
                        print(f"      '{eredmeny}' - {gyakori}x (számok: {szamok_szama})")
                
                legjobb_pontszam = -1
                legjobb_eredmeny = None
                
                for eredmeny, gyakori in lehetseges_eredmenyek.items():
                    szamok_szama = sum(c.isdigit() for c in eredmeny)
                    pontszam = gyakori * 10 + szamok_szama * 15
                    
                    if pontszam > legjobb_pontszam:
                        legjobb_pontszam = pontszam
                        legjobb_eredmeny = eredmeny
                
                legjobb_hossz = 6
                if debug:
                    print(f"   Legjobb súlyozott eredmény: {legjobb_eredmeny}")
            elif legjobb_eredmeny:
                if len(legjobb_eredmeny) > 6:
                    legjobb_eredmeny = legjobb_eredmeny[:6]
                    legjobb_hossz = 6
            
            if legjobb_eredmeny:
                if len(legjobb_eredmeny) > 6:
                    legjobb_eredmeny = legjobb_eredmeny[:6]
                
                # Ha rövidebb mint 6, de van valami
                if len(legjobb_eredmeny) < 6 and len(legjobb_eredmeny) > 0:
                    if debug:
                        print(f"   Csak {len(legjobb_eredmeny)} karaktert sikerült felismerni: '{legjobb_eredmeny}'")
                    self.neptun_kod = "ISMERETLEN"
                else:
                    self.neptun_kod = legjobb_eredmeny if len(legjobb_eredmeny) == 6 else "ISMERETLEN"
            else:
                if debug:
                    print("   Nem sikerült karaktereket felismerni")
                self.neptun_kod = "ISMERETLEN"
            
            print(f"   Neptun kód: {self.neptun_kod}")
            
        except ImportError:
            print("   pytesseract nincs telepítve, Tesseract telepítése szükséges")
            print("   Tesseract telepítése: https://github.com/UB-Mannheim/tesseract/wiki")
            self.neptun_kod = "NOTESSERACT"
        except Exception as e:
            print(f"   Neptun kód felismerési hiba: {e}")
            self.neptun_kod = "HIBA"
        
        return self.neptun_kod
    
    def neptun_keret_keresese(self, debug: bool = False) -> tuple:
        """Neptun kód keretének megkeresése."""
        regio_y_start = 0
        regio_y_end = int(self.magassag * 0.20)
        regio_x_start = int(self.szelesseg * 0.50)
        regio_x_end = self.szelesseg
        
        roi = self.szurke[regio_y_start:regio_y_end, regio_x_start:regio_x_end]
        
        elek = cv2.Canny(roi, 50, 150)
        konturok, _ = cv2.findContours(elek, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        lehetseges_keretek = []
        
        skala = self.szelesseg / 600
        min_terulet = int(2000 * skala * skala)
        max_terulet = int(10000 * skala * skala)
        
        for kontur in konturok:
            terulet = cv2.contourArea(kontur)
            if min_terulet < terulet < max_terulet:
                x, y, w, h = cv2.boundingRect(kontur)
                arany = float(w) / h if h > 0 else 0
                if 1.5 < arany < 6:
                    abs_x = regio_x_start + x
                    abs_y = regio_y_start + y
                    lehetseges_keretek.append((abs_x, abs_y, w, h, terulet))
        
        if debug:
            print(f"   Lehetséges Neptun keretek: {len(lehetseges_keretek)}")
            for i, (x, y, w, h, t) in enumerate(lehetseges_keretek):
                print(f"      Keret {i+1}: ({x}, {y}, {w}, {h}), terület: {t}")
        
        if lehetseges_keretek:
            lehetseges_keretek.sort(key=lambda k: (k[1], -k[0]))
            x, y, w, h, _ = lehetseges_keretek[0]
            
            margin_x = 2
            margin_y = 2  # Csak kis margó
            return (x + margin_x, y + margin_y, w - 2*margin_x, h - 2*margin_y)
        
        return None
    
    def teljes_kiertekeles(self, debug: bool = False, perspektiva: bool = True) -> Dict:
        """Teljes tesztlap kiértékelése."""
        print("Sarokjelölők keresése...")
        self.sarkok_keresese()
        print(f"   Talált sarkok: {len(self.sarkok)}")
        
        if perspektiva and len(self.sarkok) == 4:
            print("Perspektíva korrekció...")
            self.perspektiva_korrekcio()
        
        print("Neptun kód felismerése...")
        self.neptun_kod_kiolvasasa(debug=debug)
        
        print("Kérdések kereteinek keresése...")
        keretek = self.keretek_keresese(debug=debug)
        print(f"   Talált keretek: {len(keretek)}")
        
        print("Igaz/Hamis kérdések kiértékelése...")
        igaz_hamis = self.igaz_hamis_kiertekeles(keretek, debug=debug)
        
        print("Feleletválasztós kérdések kiértékelése...")
        feleletvalasztos = self.feleletvalasztos_kiertekeles(keretek, debug=debug)
        
        eredmeny = {
            "neptun_kod": self.neptun_kod,
            "kiertekeles_idopont": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "igaz_hamis": igaz_hamis,
            "feleletvalasztos": feleletvalasztos
        }
        
        return eredmeny
        
        print("✅ Igaz/Hamis kérdések kiértékelése...")
        igaz_hamis = self.igaz_hamis_kiertekeles(keretek)
        
        print("📝 Feleletválasztós kérdések kiértékelése...")
        feleletvalasztos = self.feleletvalasztos_kiertekeles(keretek)
        
        eredmeny = {
            "neptun_kod": self.neptun_kod,
            "kep_fajl": self.kep_utvonal,
            "kiertekeles_idopontja": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "igaz_hamis": igaz_hamis,
            "feleletvalasztos": feleletvalasztos
        }
        
        return eredmeny
    
    def eredmeny_megjelenitese(self, eredmeny: Dict):
        """Eredmények kiírása."""
        print("\n" + "="*50)
        print("KIÉRTÉKELÉSI EREDMÉNYEK")
        print("="*50)
        
        print(f"\nNeptun kód: {eredmeny.get('neptun_kod', 'N/A')}")
        print(f"Kiértékelés időpontja: {eredmeny.get('kiertekeles_idopontja', 'N/A')}")
        
        print("\nIgaz/Hamis kérdések:")
        for kerdes_szam, valasz in eredmeny["igaz_hamis"].items():
            print(f"   {kerdes_szam}. kérdés: {valasz}")
        
        print("\nFeleletválasztós kérdések:")
        for kerdes_szam, valasz_index in eredmeny["feleletvalasztos"].items():
            if valasz_index >= 0:
                print(f"   {kerdes_szam}. kérdés: {valasz_index}. válasz (A-D: {chr(65 + valasz_index)})")
            elif valasz_index == -1:
                print(f"   {kerdes_szam}. kérdés: Nincs válasz")
            elif valasz_index == -2:
                print(f"   {kerdes_szam}. kérdés: Hibás (több válasz bejelölve)")
        
        print("\n" + "="*50)
    
    def debug_kep_mentese(self, kimeneti_utvonal: str = "debug_output.png"):
        """Debug kép mentése detektált elemekkel."""
        debug_kep = cv2.cvtColor(self.szurke, cv2.COLOR_GRAY2BGR)
        
        neptun_keret = self.neptun_keret_keresese(debug=False)
        if neptun_keret:
            x, y, w, h = neptun_keret
            cv2.rectangle(debug_kep, (x, y), (x+w, y+h), (0, 255, 255), 5)
            cv2.putText(debug_kep, "NEPTUN", (x+5, y+h+20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        
        keretek = self.keretek_keresese(debug=False)
        kerdes_szam = 1
        for i, (x, y, w, h) in enumerate(keretek):
            tipus = self.kerdes_tipusanak_meghatarozasa((x, y, w, h))
            cv2.rectangle(debug_kep, (x, y), (x+w, y+h), (255, 0, 0), 5)
            cv2.putText(debug_kep, f"#{kerdes_szam}", (x+10, y-15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 0, 0), 6)
            kerdes_szam += 1
        
        ih_count = 0
        fv_count = 0
        
        for checkbox in self.debug_checkboxok:
            nx, ny, nw, nh, ki_van_jelolve, arany, tipus = checkbox
            
            if tipus == "IH":
                ih_count += 1
            elif tipus.startswith("FV"):
                fv_count += 1
            
            if ki_van_jelolve:
                cv2.rectangle(debug_kep, (nx, ny), (nx+nw, ny+nh), (0, 255, 0), 4)
            else:
                cv2.rectangle(debug_kep, (nx, ny), (nx+nw, ny+nh), (0, 0, 255), 4)
        
        print(f"   Igaz/Hamis checkboxok rajzolva: {ih_count}")
        print(f"   Feleletválasztós checkboxok rajzolva: {fv_count}")
        
        cv2.imwrite(kimeneti_utvonal, debug_kep)
        print(f"Debug kép mentve: {kimeneti_utvonal}")
    
    def eredmeny_mentese(self, eredmeny: Dict, kimeneti_mappa: str = "eredmenyek"):
        """Eredmények mentése JSON fájlba."""
        import os
        
        if not os.path.exists(kimeneti_mappa):
            os.makedirs(kimeneti_mappa)
        
        neptun_kod = eredmeny.get('neptun_kod', 'ISMERETLEN')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fajlnev = f"{neptun_kod}_{timestamp}.json"
        fajl_utvonal = os.path.join(kimeneti_mappa, fajlnev)
        
        with open(fajl_utvonal, 'w', encoding='utf-8') as f:
            json.dump(eredmeny, f, ensure_ascii=False, indent=4)
        
        print(f"[+] Eredmény mentve: {fajl_utvonal}")
        
        return fajl_utvonal


def main():
    """Tesztlap kiértékelő program."""
    
    kep_utvonal = "random_tesztlap5_utf8.png"
    perspektiva_korrekcio = True
    debug = True
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    try:
        print(f"[*] Tesztlap betöltése: {kep_utvonal}")
        kiertekelo = TesztlapKiertekelo(kep_utvonal, tesseract_path)
        
        eredmeny = kiertekelo.teljes_kiertekeles(debug=debug, perspektiva=perspektiva_korrekcio)
        
        kiertekelo.eredmeny_megjelenitese(eredmeny)
        kiertekelo.eredmeny_mentese(eredmeny)
        kiertekelo.debug_kep_mentese()
        
        if debug:
            print(f"\n[*] Debug mód aktív - részletes információk megjelenítve")
        else:
            print(f"\n[*] Tipp: Állítsd a 'debug = True' értékre a main() függvényben részletes információkért")
        
    except Exception as e:
        print(f"[!] Hiba történt: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


