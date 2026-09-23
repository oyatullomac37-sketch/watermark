# 🌊 1000+ Rasmga Watermark Qo'yish Dasturi (Batch Watermark Studio)

Bu dastur bitta papkada turgan **1000 ta va undan ortiq rasmlarga** bir necha soniya ichida matnli yoki logoli suv belgisi (watermark) qo'yib berish uchun maxsus yaratilgan.

Tizim kompyuteringizning **8 ta protsessor yadrosidan parallel (`multiprocessing`)** foydalanadi, natijada 1000 ta rasm o'rtacha **8-12 soniyada** to'liq qayta ishlanadi.

---

## 🚀 Qanday Foydalanish Mumkin?

Sizda **2 xil qulay usul** mavjud:

### 1-Usul: Qulay Web-Interfeys (Jonli Ko'rinish / Live Preview)

Brauzeringizda ochiladi, slayderlar yordamida suv belgisining shaffofligi, o'lchami va burchagini sozlab, natijani namunaviy rasmda jonli ko'rishingiz mumkin.

1. Terminalda quyidagi buyruqni ishga tushiring:
   ```bash
   python3 server.py
   ```
2. Brauzerda oching:
   👉 **http://127.0.0.1:7860**
3. **Rasmlar papkasini kiriting:** 1000 ta rasm turgan papka yo'lini kiriting va `Tekshirish` tugmasini bosing.
4. **Watermark sozlamalari:**
   - **Matnli rejim:** Matnni kiriting (masalan `@brend_nomi`), rang va kontur tanlang.
   - **Logo rejimi:** Shaffof PNG logoni tanlang yoki sudrab tashlang (Drag & Drop).
   - **Joylashuv:** 9 ta pozitsiyadan birini (masalan Pastki-o'ng) yoki **Tiled (butun rasm bo'ylab takrorlanuvchi)** tugmasini bosing.
   - **Shaffoflik & Hajm:** Slayderlarni surib, o'zingizga ma'qul ko'rinishga keltiring.
5. **"Barcha rasmlarga qo'llash"** tugmasini bosing. Jarayon bir necha soniyada tugaydi va natijalar papkasi alohida saqlanadi.

---

### 2-Usul: Terminal orqali (CLI)

Agar terminaldan foydalanish sizga tezroq bo'lsa:

#### A) Interaktiv Yordamchi (Savol-javob ko'rinishida):
Faqat buyruqning o'zini yozing:
```bash
python3 cli.py
```
Dastur sizdan navbatma-navbat papka yo'lini, matn yoki logo tanlovini va shaffoflikni so'raydi hamda jarayonni boshlaydi.

#### B) To'g'ridan-to'g'ri bitta qator buyruq bilan:

**Matnli watermark uchun:**
```bash
python3 cli.py -i "/Users/a1234/Desktop/rasmlar" -t "@brend_nomi" -p bottom-right --opacity 0.7
```

**Logo rasm (PNG) bilan:**
```bash
python3 cli.py -i "/Users/a1234/Desktop/rasmlar" -m image -l "logo.png" -p bottom-right --opacity 0.8
```

**Butun rasm bo'ylab takrorlanuvchi diagonal himoya (Tiled):**
```bash
python3 cli.py -i "/Users/a1234/Desktop/rasmlar" -t "MAXFIY" -p tiled --opacity 0.25
```

---

## ⚙️ Imkoniyatlar va Afzalliklar

- **Asl nusxalar xavfsizligi:** Original rasmlarga ziyon yetmaydi, natijalar har doim alohida `watermarked_output` papkasiga saqlanadi.
- **EXIF aylanish burchagini to'g'irlash:** Telefonlar bilan olingan vertikal/gorizontal rasmlar qiyshayib qolmaydi, avtomatik to'g'irlanadi.
- **Yuqori sifat:** Rasmlarning original sifati (JPEG 95, PNG, WEBP) saqlanib qoladi.
- **Tezlik:** 1 soniyada 90-150 tagacha rasm qayta ishlanadi.
