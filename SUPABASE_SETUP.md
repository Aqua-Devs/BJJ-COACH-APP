# Supabase Setup voor BJJ Coach App

## 🗄️ Stap 1: Supabase Project Maken

1. Ga naar [supabase.com](https://supabase.com)
2. Klik **Start your project** (gratis)
3. Maak een nieuw project:
   - **Name**: `bjj-coach`
   - **Database Password**: Bewaar dit goed! (bijv in password manager)
   - **Region**: `West EU (Ireland)` of `North EU (Frankfurt)`
4. Wacht 2 minuten tot project ready is

---

## 🔧 Stap 2: Database Schema Aanmaken

1. In je Supabase project → **SQL Editor** (linker menu)
2. Klik **New query**
3. Kopieer HELE inhoud van `schema.sql`
4. Plak in SQL editor
5. Klik **Run** (of CTRL+Enter)
6. Je zou moeten zien: "Success. No rows returned"

✅ **Check**: Ga naar **Table Editor** → Je zou nu 10 tabellen moeten zien

---

## 🔗 Stap 3: Connection String Ophalen

1. In Supabase → **Project Settings** (tandwiel icoon linksonder)
2. **Database** tab
3. Scroll naar **Connection string** sectie
4. Kies **URI** tab
5. **Kopieer de connection string**

Het ziet er zo uit:
```
postgresql://postgres.abcdefgh:[YOUR-PASSWORD]@aws-0-eu-west-1.pooler.supabase.com:5432/postgres
```

⚠️ **BELANGRIJK**: Vervang `[YOUR-PASSWORD]` met je database password uit Stap 1!

---

## 🚀 Stap 4: Render Configureren

1. Ga naar je Render web service
2. **Environment** tab
3. Voeg toe of update:

```
DATABASE_URL = postgresql://postgres.abcdefgh:JE-WACHTWOORD@aws-0-eu-west-1.pooler.supabase.com:5432/postgres
```

4. **Save Changes**
5. Render zal automatisch opnieuw deployen

---

## ✅ Stap 5: Testen

1. Wacht tot deploy klaar is (~2-3 min)
2. Ga naar je app URL
3. Je zou de login pagina moeten zien
4. Registreer eerste account (wordt admin)
5. Check in Supabase **Table Editor** → **users** → Je account staat er!

---

## 🔒 Security Tips

### Row Level Security (RLS) - Optioneel maar aanbevolen

Supabase heeft RLS standaard **UIT** staan. Voor extra security:

1. Supabase → **Authentication** → **Policies**
2. Voor elke tabel, klik **Enable RLS**
3. Voeg policies toe (of laat uit voor development)

**Voor development**: RLS uit laten is OK
**Voor production**: RLS aanzetten + policies maken

---

## 🐛 Troubleshooting

### "Connection refused"
- Check of DATABASE_URL correct is
- Vervang `[YOUR-PASSWORD]` met ECHT wachtwoord
- Check of IP whitelist in Supabase op "Allow all" staat

### "relation does not exist"
- Run `schema.sql` opnieuw in SQL Editor
- Check Table Editor of tabellen bestaan

### App werkt maar data verdwijnt
- Check of je naar juiste database wijst
- Niet per ongeluk development + production door elkaar halen

---

## 📊 Data Bekijken

**In Supabase:**
- **Table Editor** → Klik een tabel → Zie alle data
- **SQL Editor** → Run custom queries

**Voorbeeld query:**
```sql
SELECT * FROM students ORDER BY name;
SELECT * FROM sessions WHERE date > '2026-04-01';
```

---

## 💾 Backup

Supabase doet automatisch backups (gratis tier = 7 dagen history)

**Manual backup:**
1. **Database** → **Backups** → **Download**

---

## 🎉 Klaar!

Je BJJ Coach app draait nu op:
- ✅ Render (hosting)
- ✅ Supabase (PostgreSQL database)
- ✅ Production ready met persistent data!

Data blijft nu behouden bij redeployments! 🚀
