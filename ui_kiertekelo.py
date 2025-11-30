import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import cv2
import os
import json
from kiertekelo import TesztlapKiertekelo

class TesztlapKiertekeloUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tesztlap Kiértékelő")
        self.root.geometry("1400x1000")

        self.kep_utvonal = None
        self.megoldolap_utvonal = None
        self.eredmeny = None
        self.javitokulcs_eredmeny = None
        self.kiertekelo = None

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)

        settings_frame = ttk.LabelFrame(main_frame, text="Beállítások", padding="10")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))


        ttk.Label(settings_frame, text="Tesztlap kép:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.kep_path_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.kep_path_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(settings_frame, text="Tallózás...", command=self.valassz_kepet).grid(row=0, column=2, pady=5)


        ttk.Label(settings_frame, text="Tesseract útvonal:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tesseract_path_var = tk.StringVar(value=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        ttk.Entry(settings_frame, textvariable=self.tesseract_path_var, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(settings_frame, text="Tallózás...", command=self.valassz_tesseract).grid(row=1, column=2, pady=5)


        ttk.Label(settings_frame, text="Megoldólap kép:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.megoldolap_path_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.megoldolap_path_var, width=50).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(settings_frame, text="Tallózás...", command=self.valassz_megoldolap).grid(row=2, column=2, pady=5)


        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=10)
        self.debug_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Debug mód", variable=self.debug_var).pack(side=tk.LEFT, padx=10)
        self.perspektiva_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Perspektíva korrekció", variable=self.perspektiva_var).pack(side=tk.LEFT, padx=10)
        self.zajszures_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Zajszűrés", variable=self.zajszures_var).pack(side=tk.LEFT, padx=10)


        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        self.run_button = ttk.Button(button_frame, text="Kiértékelés indítása", command=self.run_kiertekeles)
        self.run_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(button_frame, text="Eredmény mentése", command=self.mentes_eredmeny, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Debug kép megnyitása", command=self.megnyit_debug_kepet).pack(side=tk.LEFT, padx=5)


        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)


        left_frame = ttk.LabelFrame(content_frame, text="Eredmények", padding="10")
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        self.eredmeny_text = scrolledtext.ScrolledText(left_frame, width=50, height=30, wrap=tk.WORD)
        self.eredmeny_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))


        right_frame = ttk.LabelFrame(content_frame, text="Debug kép előnézet", padding="10")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        canvas_frame = ttk.Frame(right_frame)
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_frame, bg='gray')
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)


        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        self.status_var = tk.StringVar(value="Kész")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)


    def valassz_kepet(self):
        filename = filedialog.askopenfilename(filetypes=[("Képfájlok","*.png *.jpg *.jpeg *.bmp *.tiff")])
        if filename:
            self.kep_path_var.set(filename)
            self.kep_utvonal = filename

    def valassz_tesseract(self):
        filename = filedialog.askopenfilename(filetypes=[("Végrehajtható fájlok","*.exe")])
        if filename:
            self.tesseract_path_var.set(filename)

    def valassz_megoldolap(self):
        filename = filedialog.askopenfilename(filetypes=[("Képfájlok","*.png *.jpg *.jpeg *.bmp *.tiff")])
        if filename:
            self.megoldolap_path_var.set(filename)
            self.megoldolap_utvonal = filename


    def run_kiertekeles(self):
        if not self.kep_utvonal:
            messagebox.showerror("Hiba","Válassz ki egy tesztlapot!")
            return

        try:
            self.status_var.set("Kiértékelés folyamatban...")
            self.root.update()

            self.eredmeny_text.delete(1.0, tk.END)
            self.eredmeny_text.insert(tk.END, "Feldolgozás folyamatban...\n\n")
            self.root.update()


            self.kiertekelo = TesztlapKiertekelo(self.kep_utvonal, self.tesseract_path_var.get(), zajszures=self.zajszures_var.get())
            self.eredmeny = self.kiertekelo.teljes_kiertekeles(debug=self.debug_var.get(), perspektiva=self.perspektiva_var.get())
            self.kiertekelo.debug_kep_mentese("debug_output.png")


            if self.megoldolap_utvonal:
                kiertekelo_j = TesztlapKiertekelo(self.megoldolap_utvonal, self.tesseract_path_var.get(), zajszures=self.zajszures_var.get())
                self.javitokulcs_eredmeny = kiertekelo_j.teljes_kiertekeles(debug=False, perspektiva=self.perspektiva_var.get())
            else:
                self.javitokulcs_eredmeny = None


            self.megjelenitni_eredmeny()

            self.betolt_debug_kepet("debug_output.png")
            self.save_button.config(state=tk.NORMAL)
            self.status_var.set("Kiértékelés befejezve")

        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba történt: {str(e)}")
            self.status_var.set("Hiba történt")
            import traceback
            traceback.print_exc()


    def megjelenitni_eredmeny(self):
        self.eredmeny_text.delete(1.0, tk.END)

        self.eredmeny_text.insert(tk.END,"="*60+"\nKIÉRTÉKELÉSI EREDMÉNYEK\n"+"="*60+"\n\n")
        self.eredmeny_text.insert(tk.END,f"Neptun kód: {self.eredmeny.get('neptun_kod','N/A')}\n")
        self.eredmeny_text.insert(tk.END,f"Kiértékelés időpontja: {self.eredmeny.get('kiertekeles_idopont','N/A')}\n\n")


        self.eredmeny_text.insert(tk.END,"Igaz/Hamis kérdések:\n"+"-"*60+"\n")
        for k,v in sorted(self.eredmeny["igaz_hamis"].items()):
            helyes = None
            if self.javitokulcs_eredmeny:
                helyes_v = self.javitokulcs_eredmeny["igaz_hamis"].get(k)
                helyes = "✔" if v == helyes_v else f"✖ (helyes: {helyes_v})"
            self.eredmeny_text.insert(tk.END,f"{k}. kérdés: {v} {helyes if helyes else ''}\n")


        self.eredmeny_text.insert(tk.END,"\nFeleletválasztós kérdések:\n"+"-"*60+"\n")
        for k,v in sorted(self.eredmeny["feleletvalasztos"].items()):
            helyes = None
            if self.javitokulcs_eredmeny:
                helyes_v = self.javitokulcs_eredmeny["feleletvalasztos"].get(k)
                helyes = "✔" if v == helyes_v else f"✖ (helyes: {helyes_v})"
            if v >= 0:
                self.eredmeny_text.insert(tk.END,f"{k}. kérdés: {v} ({chr(65+v)}) {helyes if helyes else ''}\n")
            elif v==-1:
                self.eredmeny_text.insert(tk.END,f"{k}. kérdés: Nincs válasz\n")
            elif v==-2:
                self.eredmeny_text.insert(tk.END,f"{k}. kérdés: Hibás (több válasz bejelölve)\n")

        self.eredmeny_text.insert(tk.END,"\n"+"="*60+"\n")

        pont, max_pont = self.pontozas(self.eredmeny, self.javitokulcs_eredmeny)
        self.eredmeny_text.insert(tk.END, f"\nÖsszpontszám: {pont} / {max_pont}\n")


    def pontozas(self, kitoltott, javitokulcs):
        pont = 0
        max_pont = 0


        for k, helyes in javitokulcs["igaz_hamis"].items():
            max_pont += 1
            if k in kitoltott["igaz_hamis"] and kitoltott["igaz_hamis"][k] == helyes:
                pont += 1

        for k, helyes_index in javitokulcs["feleletvalasztos"].items():
            max_pont += 1
            if k in kitoltott["feleletvalasztos"] and kitoltott["feleletvalasztos"][k] == helyes_index:
                pont += 1

        return pont, max_pont

    def betolt_debug_kepet(self, kep_utvonal):
        if not os.path.exists(kep_utvonal):
            return
        img = Image.open(kep_utvonal)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0,0, anchor=tk.NW, image=self.photo)
        self.canvas.configure(scrollregion=(0,0,img.width,img.height))

    def megnyit_debug_kepet(self):
        debug_kep_path = "debug_output.png"
        if os.path.exists(debug_kep_path):
            import platform
            if platform.system()=="Windows":
                os.startfile(debug_kep_path)
            elif platform.system()=="Darwin":
                os.system(f'open "{debug_kep_path}"')
            else:
                os.system(f'xdg-open "{debug_kep_path}"')
        else:
            messagebox.showwarning("Figyelmeztetés","Debug kép nem található!")


    def mentes_eredmeny(self):
        if not self.eredmeny:
            messagebox.showwarning("Figyelmeztetés","Nincs kiértékelt eredmény!")
            return
        try:
            kimeneti_mappa = "eredmenyek"
            if not os.path.exists(kimeneti_mappa):
                os.makedirs(kimeneti_mappa)

            from datetime import datetime
            neptun_kod = self.eredmeny.get('neptun_kod','ISMERETLEN')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fajlnev = f"{neptun_kod}_{timestamp}.json"
            fajl_utvonal = os.path.join(kimeneti_mappa,fajlnev)


            to_save = {
                "kitoltott": self.eredmeny,
                "helyes_valaszok": self.javitokulcs_eredmeny if self.javitokulcs_eredmeny else {},
            }

            with open(fajl_utvonal,'w',encoding='utf-8') as f:
                json.dump(to_save,f,ensure_ascii=False,indent=4)

            messagebox.showinfo("Siker", f"Eredmény mentve:\n{fajl_utvonal}")
            self.status_var.set(f"Eredmény mentve: {fajl_utvonal}")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba történt a mentés során:\n{str(e)}")

def main():
    root = tk.Tk()
    app = TesztlapKiertekeloUI(root)
    root.mainloop()

if __name__=="__main__":
    main()
