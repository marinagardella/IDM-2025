import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Test de Imágenes: ¿Verdadera o Falsa?", page_icon="🧠", layout="centered")

DATA_FILE = "resultados.csv"
IMAGES_FOLDER = "images"

# Ensure CSV exists
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=["nombre", "edad", "carpeta", "respuesta", "verdadero_falso", "correcta", "puntaje_total", "total_imagenes", "fecha"]).to_csv(DATA_FILE, index=False)

# Get image paths from relevant subfolders
image_paths = []
for subdir in ["real", "firefly", "midjourney"]:
    folder = os.path.join(IMAGES_FOLDER, subdir)
    if os.path.exists(folder):
        for f in os.listdir(folder):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_paths.append(os.path.join(subdir, f))

# Extract ground truth from filename
def get_ground_truth(filename):
    if "true" in filename.lower():
        return "Verdadera"
    elif "false" in filename.lower():
        return "Falsa"
    else:
        return None

# -----------------------------
# SESSION STATE
# -----------------------------
if "step" not in st.session_state:
    st.session_state.step = "inicio"
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "selected_images" not in st.session_state:
    st.session_state.selected_images = []

# -----------------------------
# PANTALLA INICIAL
# -----------------------------
if st.session_state.step == "inicio":
    st.title("🧠 Test de Imágenes: ¿Verdadera o Falsa?")
    st.write("Por favor, completá tus datos para comenzar:")

    nombre = st.text_input("Nombre")
    edad = st.number_input("Edad", min_value=1, max_value=120, step=1)
    consentimiento = st.checkbox("Acepto que los resultados de este test sean analizados con fines académicos.")

    if st.button("Comenzar"):
        if not nombre.strip():
            st.warning("⚠️ Por favor, ingresá tu nombre.")
        elif not consentimiento:
            st.warning("⚠️ Debés aceptar el uso de los resultados para continuar.")
        else:
            st.session_state.nombre = nombre
            st.session_state.edad = edad

            # Select 5 real + 5 AI (firefly + midjourney)
            real_imgs = [p for p in image_paths if "real" in p]
            fake_imgs = [p for p in image_paths if "real" not in p]
            selected_real = random.sample(real_imgs, min(5, len(real_imgs)))
            selected_fake = random.sample(fake_imgs, min(5, len(fake_imgs)))
            st.session_state.selected_images = selected_real + selected_fake
            random.shuffle(st.session_state.selected_images)

            st.session_state.step = "preguntas"
            st.rerun()

# -----------------------------
# TEST LOOP
# -----------------------------
elif st.session_state.step == "preguntas":
    idx = st.session_state.current_index
    if idx < len(st.session_state.selected_images):
        rel_path = st.session_state.selected_images[idx]
        img_path = os.path.join(IMAGES_FOLDER, rel_path)
        ground_truth = get_ground_truth(rel_path)

        st.image(img_path, use_container_width=True)
        st.write(f"Imagen {idx+1} de {len(st.session_state.selected_images)}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟩 Verdadera", key=f"verdadera_{idx}"):
                st.session_state.answers.append(("Verdadera", ground_truth, rel_path))
                if ground_truth == "Verdadera":
                    st.session_state.score += 1
                st.session_state.current_index += 1
                st.rerun()
        with col2:
            if st.button("🟥 Falsa", key=f"falsa_{idx}"):
                st.session_state.answers.append(("Falsa", ground_truth, rel_path))
                if ground_truth == "Falsa":
                    st.session_state.score += 1
                st.session_state.current_index += 1
                st.rerun()
    else:
        st.session_state.step = "resultado"
        st.rerun()

# -----------------------------
# RESULTADOS
# -----------------------------
elif st.session_state.step == "resultado":
    total = len(st.session_state.selected_images)
    score = st.session_state.score
    nombre = st.session_state.nombre
    edad = st.session_state.edad

    st.success(f"🎉 ¡Test completado, {nombre}! Tu puntaje total: **{score}/{total}**")

    # Save all answers (detailed and total)
    df = pd.read_csv(DATA_FILE)
    new_entries = []
    for respuesta, truth, path in st.session_state.answers:
        carpeta = path.split(os.sep)[0]
        correcta = (respuesta == truth)
        new_entries.append({
            "nombre": nombre,
            "edad": edad,
            "carpeta": carpeta,
            "respuesta": respuesta,
            "verdadero_falso": truth,
            "correcta": correcta,
            "puntaje_total": score,
            "total_imagenes": total,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

    st.session_state.step = "leaderboard"
    st.rerun()

# -----------------------------
# LEADERBOARD
# -----------------------------
elif st.session_state.step == "leaderboard":
    st.title("🏆 Leaderboard")

    df = pd.read_csv(DATA_FILE)
    leaderboard = (
        df.groupby(["nombre", "edad", "fecha"])
        .agg({"puntaje_total": "max", "total_imagenes": "max"})
        .reset_index()
        .sort_values(by="puntaje_total", ascending=False)
    )

    st.dataframe(leaderboard, use_container_width=True)

    if st.button("Reiniciar test"):
        for key in ["step", "current_index", "score", "answers", "nombre", "edad", "selected_images"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
