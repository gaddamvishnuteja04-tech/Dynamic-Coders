# 🏛 Gruha Alankara – Interior Design Platform
## AR & AI-Powered · Dark Luxury Theme · Vanilla JS

---

## 📁 Project Structure

```
gruha-alankara/
├── templates/
│   ├── index.html          → Home page with hero, features, testimonials
│   ├── login.html          → Login with social auth, flash messages
│   ├── register.html       → Registration with password strength meter
│   ├── dashboard.html      → Dashboard with sidebar, stat cards, activity feed
│   ├── design-studio.html  → WebRTC camera + AI analysis + style selector
│   ├── ar-view.html        → Live AR feed + drag-drop furniture placement
│   └── gallery.html        → Filterable design gallery with hover effects
│
├── static/
│   ├── css/
│   │   └── style.css       → Complete dark luxury theme (1500+ lines)
│   └── js/
│       └── main.js         → All JS: WebRTC, API, Toast, Flash, Spinner (500+ lines)
│
└── README.md
```

---

## 🎨 Design System

**Color Palette:**
- Background: `#060810` (void) → `#10141f` (cards)
- Gold accent: `#f0c060` (bright) · `#c8922a` (mid)
- Teal accent: `#3de8d0` (bright) · `#1aada0` (mid)  
- Terracotta: `#c4603a`

**Typography:**
- Display: `Cinzel Decorative` (headings)
- Title: `Cinzel` (sub-headings, nav)
- Body: `DM Sans` (all body text)
- Mono: `DM Mono` (code, coordinates)

---

## ⚡ Features

### WebRTC (MediaDevices API)
- Design Studio: `getUserMedia()` for room capture with `facingMode: environment`
- AR View: Live video feed with furniture overlay
- Snapshot: Canvas-based frame capture + download

### AI Integration (Ready for backend)
- `API.post('/studio/upload', formData)` → room image upload
- `API.post('/ai/analyze', { style, dimensions })` → design suggestions
- `API.get('/tts?text=...')` → gTTS audio playback endpoint

### Toast & Flash System
- `Toast.success('title', 'message')` 
- `Toast.error()`, `Toast.info()`, `Toast.warning()`
- `Flash.success()`, `Flash.error()`, `Flash.info()`

### Voice Assistant
- Web Speech API for voice recognition
- `SpeechSynthesisUtterance` for gTTS audio playback
- Navigate by voice: "go to gallery", "open studio", etc.

### AR Drag & Drop
- Mouse + touch support for furniture placement
- Delete key to remove selected furniture
- Position tracking with simulated depth (Z-axis)

---

## 🔌 Backend Integration

Replace simulated `await sleep(...)` calls in `main.js` with real endpoints:

```python
# Flask example
@app.route('/api/studio/upload', methods=['POST'])
def upload_image():
    image = request.files['image']
    style = request.form['style']
    # Process with your AI model
    return jsonify({ 'analysis': '...' })

@app.route('/api/tts')
def text_to_speech():
    text = request.args.get('text')
    from gtts import gTTS
    tts = gTTS(text=text, lang='en-in')
    # Save and return URL
    return jsonify({ 'url': '/static/audio/response.mp3' })
```

---

## 🚀 Quick Start

```bash
# Serve locally with Python
python -m http.server 8000

# Or with Node.js
npx serve .

# Open in browser
open http://localhost:8000/templates/index.html
```

---

*Crafted with ❤️ for Indian Homes · Gruha Alankara © 2024*
