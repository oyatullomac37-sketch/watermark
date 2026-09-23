# 🚀 Batch Watermark Studio — Deploy Qilish Bo'yicha To'liq Qo'llanma

Ushbu hujjat **Batch Watermark Studio** dasturini turli platformalarda (Docker, Linux VPS, Cloud) serverga deploy qilish va uzluksiz ishga tushirish bo'yicha to'liq qo'llanmadir.

---

## 📋 Mundarija
1. [1-Usul: Docker & Docker Compose orqali (Tavsiya etiladi)](#1-usul-docker--docker-compose-orqali-tavsiya-etiladi)
2. [2-Usul: Bepul Bulutli Platformalar (Render, Railway, Hugging Face)](#2-usul-bepul-bulutli-platformalar)
3. [3-Usul: Linux VPS Serverda (Ubuntu / Debian + Nginx + SSL)](#3-usul-linux-vps-serverda-ubuntu--debian)
4. [⚙️ Muhit O'zgaruvchilari (Environment Variables)](#️-muhit-ozgaruvchilari)
5. [🌐 Masofaviy Foydalanish Imkoniyatlari](#-masofaviy-foydalanish-imkoniyatlari)

---

## 1-Usul: Docker & Docker Compose orqali (Tavsiya etiladi)

Docker orqali ishga tushirish eng qulay va ishonchli usuldir, chunki barcha shriftlar (DejaVu, Liberation) va Python kutubxonalari avtomatik sozlanadi.

### A) Docker Compose bilan 1 ta buyruq:
```bash
# Konteynerni fonda (detached) ishga tushirish:
docker compose up -d --build
```

- **Ko'rish:** Brauzeringizda oching: `http://localhost:7860` yoki `http://SERVER_IP:7860`
- **Loglarni ko'rish:**
  ```bash
  docker compose logs -f
  ```
- **To'xtatish:**
  ```bash
  docker compose down
  ```

### B) Oddiy Docker buyruqlari orqali:
```bash
# 1. Obrazni qurish (Build)
docker build -t watermark-studio .

# 2. Ishga tushirish (Run)
docker run -d \
  --name watermark_app \
  -p 7860:7860 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/watermarked_output:/app/watermarked_output \
  watermark-studio
```

---

## 2-Usul: Bepul Bulutli Platformalar

### A) Render.com (1-Click Blueprint Deploy)
Loyiha ichida `render.yaml` fayli allaqachon tayyorlangan:
1. Loyihani o'zingizning GitHub/GitLab profilingizga yuklang (push).
2. [Render.com](https://render.com) ga kiring va **Blueprints** bo'limidan omboringizni (repository) tanlang.
3. Render `render.yaml` faylini avtomatik taniydi va bepul veb-xizmat yaratib beradi.
4. Bir necha daqiqada sizga `https://watermark-studio.onrender.com` kabi bepul HTTPS havola taqdim etiladi.

### B) Railway.app
Loyiha ichida `Procfile` mavjud:
1. [Railway.app](https://railway.app) ga kiring va **New Project -> Deploy from GitHub** ni tanlang.
2. Railway avtomatik ravishda `requirements.txt` va `Procfile` ni aniqlab, `0.0.0.0` portida ishga tushiradi.
3. **Settings -> Generate Domain** tugmasini bosing va o'z havolangizga ega bo'ling.

### C) Hugging Face Spaces (Docker Space)
1. Hugging Face da yangi **Space** oching va SDK sifatida **Docker** ni tanlang.
2. Loyiha fayllarini (Dockerfile bilan birga) Space repozitoriyasiga yuklang.
3. Hugging Face avtomatik ravishda `7860` portida ishlaydigan bepul serverni ishga tushiradi.

### D) Vercel.com
Loyihada Vercel uchun `vercel.json` va Serverless `handler` eksporti to'liq tayyorlangan:
1. [Vercel.com](https://vercel.com) ga kiring va **Add New -> Project** orqali `watermark` repozitoriyangizni tanlang.
2. Hech qanday sozlamalarni o'zgartirmasdan **Deploy** tugmasini bosing.
3. Vercel bir necha soniyada bepul `https://watermark-xxxx.vercel.app` domenini beradi.

> ⚠️ **Muhim Eslatma:** Vercel serverless platforma bo'lib, bepul tarifda har bir so'rovga maksimal **10 soniya** timeout beradi. Shuning uchun 500-1000 ta juda katta rasmlarni uzluksiz qayta ishlash uchun **Render.com**, **Railway** yoki **Docker VPS** (timeout cheklovisiz) tavsiya etiladi. Vercel esa tezkor sinov va kichikroq to'plamlar uchun juda qulaydir.

---

## 3-Usul: Linux VPS Serverda (Ubuntu / Debian)

Agar o'zingizning shaxsiy VPS serveringiz (Ubuntu 22.04 / 24.04) bo'lsa, uni Nginx va Systemd orqali to'g'ridan-to'g'ri sozlash mumkin:

### 1-Qadam: Tizim paketlarini o'rnatish
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx git \
    fonts-dejavu-core fonts-freefont-ttf fonts-liberation
```

### 2-Qadam: Loyihani serverga joylashtirish
```bash
sudo mkdir -p /var/www/watermark
cd /var/www/watermark

# Loyihani yuklash yoki git clone qilish:
# git clone <sizning-repo-link> .

# Virtual muhit yaratish va kutubxonalarni o'rnatish:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ruxsatlarni berish:
sudo chown -R www-data:www-data /var/www/watermark
sudo chmod -R 775 /var/www/watermark/uploads /var/www/watermark/watermarked_output
```

### 3-Qadam: Systemd orqali xizmatni yoqish
Loyihadagi `watermark.service` faylidan foydalaning:
```bash
sudo cp /var/www/watermark/watermark.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now watermark

# Holatini tekshirish:
sudo systemctl status watermark
```

### 4-Qadam: Nginx Reverse Proxy sozlash
Loyihadagi `nginx.conf` faylini Nginx ga nusxalash:
```bash
sudo cp /var/www/watermark/nginx.conf /etc/nginx/sites-available/watermark.conf

# Fayldagi 'sizning-domeningiz.uz' o'rniga o'z domeningiz yoki server IP'ingizni yozing:
sudo nano /etc/nginx/sites-available/watermark.conf

# Faollashtirish:
sudo ln -s /etc/nginx/sites-available/watermark.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5-Qadam: Bepul SSL (HTTPS) o'rnatish
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d sizning-domeningiz.uz
```

---

## ⚙️ Muhit O'zgaruvchilari (Environment Variables)

| O'zgaruvchi | Sukut bo'yicha | Tavsif |
|-------------|----------------|--------|
| `HOST`      | `0.0.0.0`      | Qaysi interfeysda tinglash (0.0.0.0 - barcha tashqi ulanishlar uchun) |
| `PORT`      | `7860`         | Web server ishlaydigan port (Cloud platformalarda avtomatik olinadi) |

Terminalda o'zgartirib ishga tushirish namunasi:
```bash
HOST=0.0.0.0 PORT=8080 python3 server.py
```

---

## 🌐 Masofaviy Foydalanish Imkoniyatlari

Server masofaga (Cloud/VPS) deploy qilinganida foydalanuvchilar o'z kompyuteridagi fayllarni oson ishlatishi uchun yangi qulayliklar qo'shildi:

1. **📤 Brauzerdan Yuklash (Upload):**
   - 1-qadamda "Yuklash (Rasmlar / ZIP)" tugmasini bosing.
   - 1000 ta rasmni yoki bitta `.ZIP` arxivini brauzerga sudrab tashlang (Drag & Drop). Server ularni avtomatik ochadi va tayyorlaydi.

2. **📥 Natijalarni ZIP Qilib Yuklab Olish (Download ZIP):**
   - Suv belgisi qo'yish yakunlangach, ekranda paydo bo'ladigan **"Barcha rasmlarni ZIP qilib yuklab olish"** tugmasini bosing.
   - Barcha suv belgili rasmlar bitta siqilgan `watermarked_images.zip` fayl holida kompyuteringizga yuklab olinadi.

3. **💓 Health Check Endpoint:**
   - Har qanday monitoring yoki load balancer tizimlari uchun `GET /health` endpointi mavjud:
   ```bash
   curl http://localhost:7860/health
   # Natija: {"status": "healthy", "service": "batch-watermark-studio", ...}
   ```
