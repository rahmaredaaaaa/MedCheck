# 💊 MedCheck — Smart Medicine Scanner

> An AI-powered desktop application that helps users identify medicines from package images, view medicine information, and compare prescriptions with previously scanned medicines.

---

## 📌 Overview

**MedCheck** is a Windows desktop application built with **Python, PyQt5, OpenCV, and AI Vision technology**.

The application allows users to:

- 📷 Scan medicine packages using a laptop camera.
- 🤖 Analyze medicine images using an AI vision model.
- 💊 Extract visible medicine information.
- 📋 View detailed medicine information.
- 🖼️ Keep multiple scanned medicines in the same session.
- 📝 Upload a prescription image.
- 🔎 Compare prescription medicines with the medicines already scanned.
- ✅ Display only medicines that match the scanned inventory.
- ⚡ Keep the graphical interface responsive using background workers.

MedCheck is designed with a clean and modern medical-tech interface that focuses on simplicity, usability, and clear information presentation.

---

## ✨ Features

### 📷 Live Camera Scanning

MedCheck connects to the laptop's default camera using OpenCV and displays a live camera preview directly inside the desktop application.

Users can capture the current frame by clicking:

**Scan Medicine**

---

### 🤖 AI Medicine Recognition

After capturing an image, the application sends the image to the AI vision service for analysis.

The AI attempts to identify information that is actually visible on the medicine package, including:

- Medicine Name
- Active Ingredient
- Dosage
- Dosage Unit
- Manufacturer
- Medicine Type
- Package Size
- Description
- Confidence Score
- Visible Text

The application avoids displaying unsupported information when the required details cannot be read from the image.

---

### 💊 Medicine Cards

Every scanned medicine is displayed as a separate card containing:

- Medicine image
- Medicine name
- Identification status
- Active ingredient
- Dosage
- Manufacturer
- Medicine type
- Package size
- Confidence score
- Description

Users can also open:

**View Details**

to see a complete medicine record.

---

### ➕ Multiple Medicine Scanning

Users can scan more than one medicine during the same session.

Previously scanned medicines remain visible while new medicines are added.

This creates a temporary medicine inventory that can later be used for prescription checking.

---

### 📋 Prescription Scanner

MedCheck includes a dedicated prescription-checking workflow.

Users can upload a prescription image and compare its medicines against the medicines scanned during the current session.

The application identifies matching medicines and displays:

- ✅ Match status
- 💊 Scanned medicine name
- 🖼️ Matching medicine image
- 📋 How to use information

Non-matching medicines are intentionally hidden from the results interface to keep the output focused and easy to understand.

---

### ⚡ Responsive UI

AI requests can take time to complete.

To prevent the application interface from freezing during AI processing, MedCheck uses:

- `QThread`
- Background analysis workers
- PyQt signals

This allows the GUI to remain responsive while image analysis is running.

---

### 🛡️ Error Handling

The application includes error handling for:

- Camera access problems
- Missing API keys
- AI service errors
- Invalid images
- Image loading failures
- Unexpected processing errors

User-friendly error messages are displayed through the interface.

---

## 🖥️ Application Workflow

```text
                 ┌─────────────────────┐
                 │      Launch App      │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Open Laptop       │
                 │      Camera         │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Scan Medicine     │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Capture Image Frame │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    AI Vision        │
                 │     Analysis        │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Medicine Information│
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Medicine Card     │
                 └──────────┬──────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │      Scan More Medicines    │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │    Upload Prescription      │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │ Compare With Scanned        │
              │ Medicines Inventory         │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │ Show Matching Medicines     │
              └─────────────────────────────┘