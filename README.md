# BJJ Coach App - Complete Gym Management System

Full-stack web app voor BJJ coaching met student tracking, curriculum management, en sparring analytics.

## 🚀 Deployment naar Render

### 1. GitHub Setup

```bash
# In je project folder op Windows:
git init
git add .
git commit -m "Initial commit - BJJ Coach App"
git branch -M main

# Maak EERST een nieuwe repo aan op github.com, dan:
git remote add origin https://github.com/[jouw-username]/bjj-coach.git
git push -u origin main
```

### 2. Render Setup

1. Ga naar [render.com](https://render.com) en maak account
2. Klik **New +** → **Web Service**
3. Connect je GitHub repository
4. **Settings:**
   - Name: `bjj-coach`
   - Region: `Europe (Frankfurt)`
   - Branch: `main`
   - Runtime: `Python 3`
   - Build Command: `./build.sh`
   - Start Command: `gunicorn app:app`

5. **Environment Variables** toevoegen:
   - Key: `SECRET_KEY` 
   - Value: Genereer random (bijv via: https://randomkeygen.com)
   
   - Key: `PYTHON_VERSION`
   - Value: `3.11.0`

6. Klik **Create Web Service**

### 3. Deploy Process
- Duurt 2-5 minuten
- Check logs voor errors
- App live op: `https://[jouw-naam].onrender.com`

### 4. Eerste Gebruik
1. Ga naar app URL
2. Klik "Registreer"
3. Eerste account = automatisch ADMIN
4. Login en begin!

---

## 📱 Lokaal Draaien (Development)

```bash
# Windows:
pip install -r requirements.txt
py app.py

# Ga naar: http://localhost:5000
```

---

## 🥋 Features

- Student management (belt, stripes, gym)
- Curriculum planning met datums
- Session logging uit curriculum
- 3 aparte notitie velden (Goed/Focus/Algemeen)
- Technique mastery sliders
- Sparring tracking met stats
- Injury management
- Competition prep mode
- User auth + admin approval
- Belt progression tracking
- Peer comparison analytics

---

## 🔐 Users

- **Eerste user** = Admin (auto)
- **Nieuwe users** = Wachten op goedkeuring
- **Admin** = 👑 Users management toegang

---

## 📄 License

MIT - Vrij te gebruiken
