from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import random
from pdf2image import convert_from_path
import os
import sys

# Próbáljuk meg megtalálni az Arial font-ot
arial_font_path = None
if sys.platform == "win32":
    possible_paths = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\Arial.ttf"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            arial_font_path = path
            break

if arial_font_path:
    pdfmetrics.registerFont(TTFont('Arial', arial_font_path))
else:
    # Ha nem találjuk az Arial-t, használjuk a Helvetica-t (beépített)
    print("[WARNING] Arial font nem található, Helvetica használata...")


true_false_questions = [
    "A Nap egy csillag.",
    "A víz forráspontja 50°C.",
    "A Föld lapos.",
    "A DNS kettős spirál szerkezetű.",
    "A hidrogén a periódusos rendszer első eleme.",
]

multiple_choice_questions = [
    ("Melyik ország fővárosa Párizs?", ["Németország", "Franciaország", "Spanyolország", "Olaszország"], 1),
    ("Melyik a legnagyobb bolygó a Naprendszerben?", ["Föld", "Mars", "Jupiter", "Vénusz"], 2),
    ("Ki írta a Hamletet?", ["Tolkien", "Shakespeare", "Goethe", "Hemingway"], 1),
    ("Melyik szín keverékéből lesz lila?", ["Piros + Kék", "Zöld + Sárga", "Kék + Sárga", "Fekete + Fehér"], 0),
]

# ===== Kérdések összekeverése =====
# Minden kérdést típussal együtt tároljunk
all_questions = []

# Igaz/Hamis kérdések hozzáadása
for q in true_false_questions:
    all_questions.append(("IH", q))

# Feleletválasztós kérdések hozzáadása
for q_data in multiple_choice_questions:
    all_questions.append(("FV", q_data))

# Kérdések véletlenszerű összekeverése
random.shuffle(all_questions)

# Fájl mentése az aktuális munkakönyvtárba
file_path = os.path.join(os.getcwd(), "tesztkep.pdf")
c = canvas.Canvas(file_path, pagesize=A4)

width, height = A4
margin = 2 * cm
y = height - margin

# ===== Sarokjelölők / Alignment boxok =====
corner_size = 1 * cm
c.setFillColorRGB(0, 0, 0)  # fekete kitöltés

# Bal felső sarok
c.rect(0.5 * cm, height - 1.5 * cm, corner_size, corner_size, fill=1, stroke=0)
# Jobb felső sarok
c.rect(width - 1.5 * cm, height - 1.5 * cm, corner_size, corner_size, fill=1, stroke=0)
# Bal alsó sarok
c.rect(0.5 * cm, 0.5 * cm, corner_size, corner_size, fill=1, stroke=0)
# Jobb alsó sarok
c.rect(width - 1.5 * cm, 0.5 * cm, corner_size, corner_size, fill=1, stroke=0)

# ===== Cím (balra zárt) =====
c.setFillColorRGB(0, 0, 0)
c.setFont("Arial", 18)
title_x = margin
c.drawString(title_x, y, "Tudásfelmérő Tesztlap")

# ===== Neptun azonosító mező =====
neptun_box_width = 5.5 * cm
neptun_box_height = 1.0 * cm

# nagyobb távolság a címtől
neptun_x = width - margin - neptun_box_width
neptun_y = y - 0.3 * cm  # kb. a cím vonalával egy magasságban marad

c.setLineWidth(1)
c.rect(neptun_x, neptun_y - 0.2 * cm, neptun_box_width, neptun_box_height, stroke=1, fill=0)

c.setFont("Arial", 10)
c.drawRightString(neptun_x - 0.3 * cm, neptun_y + neptun_box_height / 2 - 0.1 * cm, "Neptun-kód:")

y = neptun_y - 1.7 * cm  # továbblépünk a mező alá

# ===== Szöveg beállítás =====
c.setFont("Arial", 12)
box_size = 10
line_thickness = 1.8
frame_padding_top = 6
frame_padding_bottom = 6
option_spacing = 0.6 * cm
question_spacing = 0.8 * cm

# ===== Kérdések kirajzolása (összekevert sorrendben) =====
ih_counter = 1
fv_counter = 1

for q_type, q_data in all_questions:
    if q_type == "IH":
        # ===== Igaz / Hamis kérdés =====
        q = q_data
        content_height = question_spacing
        box_height = content_height + frame_padding_top + frame_padding_bottom

        c.setLineWidth(3.5)  # Keret vastagsága (kompromisszum 3 és 4 között)
        c.rect(margin, y - box_height + frame_padding_bottom, width - 2 * margin, box_height, stroke=1, fill=0)

        text_y = y - frame_padding_bottom - (box_height - frame_padding_top - frame_padding_bottom) / 2 + 4
        c.drawString(margin + 4, text_y - 2, f"{ih_counter}. {q}")

        # Igaz / Hamis jelölőnégyzetek
        x_box_start = width - 7.2 * cm
        c.setLineWidth(line_thickness)
        c.rect(x_box_start, text_y - 3, box_size, box_size)
        c.drawString(x_box_start + box_size + 4, text_y - 3, "Igaz")

        x_hamis = x_box_start + box_size + 55
        c.rect(x_hamis, text_y - 3, box_size, box_size)
        c.drawString(x_hamis + box_size + 4, text_y - 2, "Hamis")

        y -= box_height + 0.3 * cm
        ih_counter += 1
        
    else:  # q_type == "FV"
        # ===== Feleletválasztós kérdés =====
        question, options, correct = q_data
        content_height = question_spacing + option_spacing * len(options) + 0.3 * cm
        box_height = content_height + frame_padding_top + frame_padding_bottom

        c.setLineWidth(3.5)  # Keret vastagsága (kompromisszum 3 és 4 között)
        c.rect(margin, y - box_height + frame_padding_bottom, width - 2 * margin, box_height, stroke=1, fill=0)

        text_y = y - frame_padding_bottom - (box_height - frame_padding_top - frame_padding_bottom) / 2 + (
            option_spacing * len(options)
        ) / 2 + 2
        c.drawString(margin + 4, text_y, f"{fv_counter}. {question}")

        option_y = text_y - question_spacing
        for option in options:
            c.setLineWidth(line_thickness)
            c.rect(margin + 0.4 * cm, option_y - 3, box_size, box_size)
            c.drawString(margin + 0.4 * cm + box_size + 6, option_y - 2, option)
            option_y -= option_spacing

        y -= box_height + 0.3 * cm
        fv_counter += 1

c.save()
print(f"[OK] PDF generalva: {file_path}")

# ===== PDF konvertálása PNG formátumba =====
try:
    png_path = file_path.replace('.pdf', '.png')

    # PDF konvertálása képpé (300 DPI felbontással)
    images = convert_from_path(file_path, dpi=300)

    # Első oldal mentése PNG-ként
    if images:
        images[0].save(png_path, 'PNG')
        print(f"[OK] PNG generalva: {png_path}")

except Exception as e:
    print(f"[WARNING] PNG konverzio hiba: {e}")
    print("   Telepítsd a Poppler-t a PDF->PNG konverzióhoz:")
    print("   https://github.com/oschwartz10612/poppler-windows/releases/")
