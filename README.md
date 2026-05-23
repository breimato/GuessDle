# 🎮 GuessDle

**GuessDle** es una aplicación web para jugar al clásico **Wordle**, pero con un giro temático:  
🌊 *One Piece*, ⚡ *Harry Potter*, 🧬 *Pokémon*, 🧠 *League of Legends*... ¡y muchos más!

---

## 🌟 Características principales

- 🎯 Juegos tipo Wordle según franquicia.
- 🛠️ Añade nuevos juegos fácilmente desde el panel de administración de Django (sin tocar código).
- 🔁 Soporte para APIs externas o archivos `.json` locales.
- 🔐 Sistema de inicio de sesión y registro.
- 🏆 Estadísticas por usuario y rankings:
  - Ranking global 🌍
  - Ranking por juego 🎮
  - Tus estadísticas personales 📈

---

## 🧩 ¿Cómo crear un nuevo juego?

1. Accede al **panel de administración de Django**.
2. Crea un nuevo `Game` y completa:
   - La **URL de la API** (si tienes una), o
   - Déjala vacía si vas a usar un archivo `.json` en la carpeta `data/`.
3. Mapea los campos del modelo (como `name`, `image`, etc.) con los nombres reales del JSON.
4. Ejecuta uno de estos comandos:
   - `sync_game_data` si usas una API.
   - `sync_game_data_without_api` si usas un `.json`.

¡Y ya estaría! El juego aparecerá automáticamente en la web 🎉

---

## 🚀 Instalación rápida

```bash
git clone https://github.com/breimato/guessdle.git
cd guessdle
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

```

Accede a la aplicación en:

```bash

http://localhost:8000
```

________

# 🎮 GuessDle

**GuessDle** is a web app to play the classic **Wordle**, but with a themed twist:  
🌊 *One Piece*, ⚡ *Harry Potter*, 🧬 *Pokémon*, 🧠 *League of Legends*... and many more!

---

## 🌟 Main Features

- 🎯 Wordle-style games based on popular franchises.
- 🛠️ Add new games via the Django admin panel – no coding required.
- 🔁 Supports both external APIs and local `.json` files.
- 🔐 Login and registration system.
- 🏆 User statistics and leaderboards:
  - Global ranking 🌍  
  - Game-specific rankings 🎮  
  - Your own performance stats 📈

---

## 🧩 How to Add a New Game

1. Go to the **Django admin panel**.
2. Create a new `Game` entry and provide:
   - The **API URL** (if available), or
   - Leave it empty if you’ll use a `.json` file inside the `data/` folder.
3. Map your game fields (e.g., `name`, `image`, etc.) to the actual field names in the JSON response.
4. Run one of the following commands:
   - `sync_game_data` (if you're using an API).
   - `sync_game_data_without_api` (if you're using a local `.json`).

That’s it – the game will be available on the site automatically! 🎉

---

## 🚀 Quick Setup

```bash
git clone https://github.com/breimato/guessdle.git
cd guessdle
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Access the app at:

```bash
http://localhost:8000
```
