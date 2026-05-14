from typing import Container
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import os
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'users.db')
upload_path = os.path.join(basedir, 'uploads')
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torchvision import transforms
import timm
import cv2
from PIL import Image
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
import io
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================
# DATABASE SETUP
# ============================================
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            age TEXT,
            purpose TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ============================================
# LOAD MODELS
# ============================================
print("Loading models...")

# Load XGBoost model
model_xgb = joblib.load('model/xgboost_model.pkl')
scaler = joblib.load('model/scaler.pkl')
feature_names = joblib.load('model/feature_names.pkl')

# Define FastViT Model Class
class FastViTClassifier(nn.Module):
    def __init__(self, num_classes=5):
        super(FastViTClassifier, self).__init__()
        self.base_model = timm.create_model('fastvit_t8', pretrained=False, num_classes=0)
        
        with torch.no_grad():
            dummy_input = torch.randn(1, 3, 224, 224)
            feature_size = self.base_model(dummy_input).shape[1]
        
        self.classifier = nn.Sequential(
            nn.BatchNorm1d(feature_size),
            nn.Dropout(0.3),
            nn.Linear(feature_size, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        features = self.base_model(x)
        output = self.classifier(features)
        return output

# Load FastViT model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model_fastvit = FastViTClassifier(num_classes=5)
model_fastvit.load_state_dict(torch.load('model/best_fastvit_model.pth', map_location=device))
model_fastvit = model_fastvit.to(device)
model_fastvit.eval()

# Cell type names
class_names = ['Dyskeratotic', 'Koilocytotic', 'Metaplastic', 'Parabasal', 'Superficial-Intermediate']

print("✓ Models loaded successfully!")

# ============================================
# HELPER FUNCTIONS
# ============================================

def create_full_feature_vector(user_input):
    """
    Creates full 35-feature vector from user's 10 inputs.
    Remaining 25 features are filled with 0.
    """
    # Feature indices for Top 10 features
    feature_indices = {
        'Age': 0,
        'Number of sexual partners': 1,
        'First sexual intercourse': 2,
        'Num of pregnancies': 3,
        'Smokes (packs/year)': 6,
        'STDs (number)': 12,
        'STDs:genital herpes': 19,
        'Dx:CIN': 29,
        'Schiller': 33,
        'Citology': 34
    }
    
    # Initialize all 35 features with 0
    full_features = np.zeros(35)
    
    # Fill in user's inputs at correct indices
    for feature_name, value in user_input.items():
        if feature_name in feature_indices:
            idx = feature_indices[feature_name]
            full_features[idx] = value
    
    return full_features.reshape(1, -1)

def predict_risk(user_input):
    """
    Predicts cervical cancer risk using XGBoost model.
    Returns: prediction (0 or 1), probability, shap_values
    """
    # Create full feature vector
    full_features = create_full_feature_vector(user_input)
    
    # Scale features
    features_scaled = scaler.transform(full_features)
    
    # Predict
    prediction = model_xgb.predict(features_scaled)[0]
    probability = model_xgb.predict_proba(features_scaled)[0]
    
    # Calculate SHAP values
    explainer = shap.TreeExplainer(model_xgb)
    shap_values = explainer.shap_values(features_scaled)
    
    return prediction, probability, shap_values, features_scaled

def generate_shap_plot(shap_values, features_scaled):
    """
    Generates SHAP waterfall plot and returns as base64 string.
    """
    plt.figure(figsize=(10, 6))
    
    # Create SHAP explanation object
    explainer = shap.TreeExplainer(model_xgb)
    shap_explanation = shap.Explanation(
        values=shap_values[0],
        base_values=explainer.expected_value,
        data=features_scaled[0],
        feature_names=feature_names
    )
    
    # Generate waterfall plot
    shap.waterfall_plot(shap_explanation, show=False)
    plt.title('SHAP Feature Impact Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return img_base64

def predict_image(image_path):
    """
    Predicts cell type using FastViT model.
    Returns: predicted_class, confidence, class_probabilities
    """
    # Load and preprocess image
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Transform for model
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    input_tensor = transform(image_rgb).unsqueeze(0).to(device)
    
    # Predict
    with torch.no_grad():
        output = model_fastvit(input_tensor)
        probabilities = torch.softmax(output, dim=1)[0].cpu().numpy()
        predicted_class = np.argmax(probabilities)
        confidence = probabilities[predicted_class] * 100
    
    return predicted_class, confidence, probabilities

def generate_gradcam(image_path, predicted_class):
    """
    Generates Grad-CAM heatmap for the image.
    Returns: base64 encoded heatmap image
    """
    # Load image
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_resized = cv2.resize(image_rgb, (224, 224))
    
    # Transform for model
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    input_tensor = transform(image_rgb).unsqueeze(0).to(device)
    
    # Initialize Grad-CAM
    target_layers = [model_fastvit.base_model.stages[-1]]
    cam = GradCAM(model=model_fastvit, target_layers=target_layers)
    
    # Generate CAM
    grayscale_cam = cam(input_tensor=input_tensor, targets=None)
    heatmap = show_cam_on_image(image_resized / 255.0, grayscale_cam[0], use_rgb=True)
    
    # Convert to base64
    _, buffer = cv2.imencode('.png', cv2.cvtColor(heatmap, cv2.COLOR_RGB2BGR))
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return img_base64

# ============================================
# ROUTES
# ============================================

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('detection'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['username'] = username
            session['user_id'] = user[0]
            flash('Login successful!', 'success')
            return redirect(url_for('detection'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        age = request.form.get('age')
        purpose = request.form.get('purpose')
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, password, email, first_name, last_name, age, purpose)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, hashed_password, email, first_name, last_name, age, purpose))
            conn.commit()
            conn.close()
            
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/detection')
def detection():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('detection.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get user inputs (Top 10 features)
        user_input = {
            'Age': float(request.form.get('age')),
            'Schiller': int(request.form.get('schiller')),
            'Citology': int(request.form.get('citology')),
            'Dx:CIN': int(request.form.get('dx_cin')),
            'STDs:genital herpes': int(request.form.get('genital_herpes')),
            'STDs (number)': int(request.form.get('stds_number')),
            'Number of sexual partners': int(request.form.get('sexual_partners')),
            'First sexual intercourse': float(request.form.get('first_intercourse')),
            'Num of pregnancies': int(request.form.get('pregnancies')),
            'Smokes (packs/year)': float(request.form.get('smoking'))
        }
        
        # Predict risk
        prediction, probability, shap_values, features_scaled = predict_risk(user_input)
        
        # Generate SHAP plot
        shap_plot = generate_shap_plot(shap_values, features_scaled)
        
        # Store results in files instead of session (session cookie size limit)
        user_id = session.get('user_id')
        results_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'results_{user_id}')
        os.makedirs(results_dir, exist_ok=True)
        
        # Save SHAP plot to file
        shap_path = os.path.join(results_dir, 'shap_plot.txt')
        with open(shap_path, 'w') as f:
            f.write(shap_plot)
        
        # Store minimal data in session
        session['prediction'] = int(prediction)
        session['probability'] = float(probability[1])
        session['user_input'] = user_input
        
        # Determine risk level
        risk_probability = probability[1]
        
        if risk_probability <= 0.5:
            # LOW RISK - Redirect to results page
            return jsonify({
                'status': 'low_risk',
                'redirect': url_for('results')
            })
        else:
            # HIGH RISK - Stay on page, show image upload
            # Load SHAP plot from file
            user_id = session.get('user_id')
            shap_path = os.path.join(app.config['UPLOAD_FOLDER'], f'results_{user_id}', 'shap_plot.txt')
            with open(shap_path, 'r') as f:
                shap_plot = f.read()
            
            return jsonify({
                'status': 'high_risk',
                'probability': float(risk_probability),
                'shap_plot': shap_plot
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Save image
        filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Predict cell type
        predicted_class, confidence, probabilities = predict_image(filepath)
        
        # Generate Grad-CAM
        gradcam_img = generate_gradcam(filepath, predicted_class)
        
        # Store results in files
        user_id = session.get('user_id')
        results_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'results_{user_id}')
        
        # Save Grad-CAM to file
        gradcam_path = os.path.join(results_dir, 'gradcam.txt')
        with open(gradcam_path, 'w') as f:
            f.write(gradcam_img)
        
        # Store minimal data in session
        session['cell_type'] = class_names[predicted_class]
        session['cell_confidence'] = float(confidence)
        
        # Clean up uploaded image
        os.remove(filepath)
        
        return jsonify({
            'status': 'success',
            'cell_type': class_names[predicted_class],
            'confidence': float(confidence),
            'gradcam': gradcam_img,
            'probabilities': {class_names[i]: float(probabilities[i]) for i in range(5)}
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/results')
def results():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if 'prediction' not in session:
        return redirect(url_for('detection'))
    
    # Load SHAP plot from file
    user_id = session.get('user_id')
    shap_path = os.path.join(app.config['UPLOAD_FOLDER'], f'results_{user_id}', 'shap_plot.txt')
    
    if os.path.exists(shap_path):
        with open(shap_path, 'r') as f:
            session['shap_plot'] = f.read()
    
    return render_template('results.html')


@app.route('/download_report')
def download_report():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        # 1. Call the logic-separated function
        pdf_buffer = generate_advanced_report(session, app)
        
        # 2. Return the file
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"Cervical_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        app.logger.error(f"PDF Error: {str(e)}")
        return "Error generating PDF report", 500
def generate_advanced_report(session_data, app_instance):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter # 'height' is used here

    # --- 1. Define Missing Colors (CRITICAL CHANGE) ---
    PRIMARY = colors.HexColor("#2c3e50")   # Navy
    ACCENT = colors.HexColor("#3498db")    # Blue
    RED = colors.HexColor("#e74c3c")       # Define Red
    GREEN = colors.HexColor("#27ae60")     # Define Green
    
    # --- 2. Header & Branding ---
    c.setFillColor(PRIMARY)
    c.rect(0, height - 110, width, 110, fill=1, stroke=0)
    
    # Logo Placement
    logo_path = "logo.jpg"
    if os.path.exists(logo_path):
        try:
            # Shifted slightly for better margin
            c.drawImage(logo_path, 35, height - 95, width=75, height=75, 
                        preserveAspectRatio=True, mask='auto')
        except:
            pass 

    # Text Placement (Increased X-coordinate to 140 to prevent superimposition)
    c.setFillColor(colors.whitesmoke)
    c.setFont("Helvetica-Bold", 19)
    c.drawString(140, height - 50, "CERVICAL CANCER RISK ASSESSMENT")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(140, height - 70, "SCHOOL OF ENGINEERING (SOE) | ACADEMIC PROJECT")
    
    c.setFont("Helvetica", 8)
    c.drawString(140, height - 85, f"Authenticated Report: {datetime.now().strftime('%B %d, %Y | %H:%M')}")

    y = height - 150

    # --- 3. Patient Summary ---
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Patient Diagnostic Summary")
    y -= 10
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.5)
    c.line(50, y, width - 50, y)
    y -= 35

    patient_data = [
        ["Patient Name:", session_data.get('username', 'N/A'), "User ID:", f"ID-{session_data.get('user_id', '000')}"],
        ["Analysis Mode:", "Dual-Stage AI", "Supervision:", "SOE Institutional"]
    ]
    pt_table = Table(patient_data, colWidths=[1.2*inch, 2*inch, 1*inch, 2*inch])
    pt_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), PRIMARY),
    ]))
    pt_table.wrapOn(c, 50, y)
    pt_table.drawOn(c, 50, y)

    # --- 4. Risk Box (Now using defined RED/GREEN) ---
    prob = session_data.get('probability', 0)
    is_high = prob > 0.5
    status_color = RED if is_high else GREEN # This now works
    
    y -= 80 # Create space for the box
    c.setFillColor(colors.whitesmoke)
    c.setStrokeColor(status_color)
    c.roundRect(50, y, width - 100, 70, 8, fill=1, stroke=1)
    
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(70, y + 50, "AI CLASSIFICATION RESULT")
    
    c.setFillColor(status_color)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(70, y + 20, f"{'HIGH RISK' if is_high else 'LOW RISK'}")
    
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 80, y + 25, f"Confidence Level: {prob:.2%}")
    y -= 40

    # --- 5. Clinical Input Table ---
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "Clinical Input Data")
    y -= 25
    
    u_in = session_data.get('user_input', {})
    input_data = [
        ["Feature", "Value", "Feature", "Value"],
        ["Age", f"{u_in.get('Age', 0):.0f}", "Pregnancies", f"{u_in.get('Num of pregnancies', 0):.0f}"],
        ["Schiller", "Positive" if u_in.get('Schiller') == 1 else "Negative", "Citology", "Positive" if u_in.get('Citology') == 1 else "Negative"],
        ["Smoking", f"{u_in.get('Smokes (packs/year)', 0)} pk/yr", "Partners", f"{u_in.get('Number of sexual partners', 0)}"]
    ]
    
    t_feat = Table(input_data, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 1.2*inch])
    t_feat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    t_feat.wrapOn(c, 50, y - 60)
    t_feat.drawOn(c, 50, y - 60)
    y -= 110

    # --- 6. SHAP Plot (Centered) ---
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "Explainable AI (XAI) - Feature Importance")
    y -= 210 
    
    user_id = session_data.get('user_id')
    shap_path = os.path.join(app_instance.config['UPLOAD_FOLDER'], f'results_{user_id}', 'shap_plot.txt')
    if os.path.exists(shap_path):
        with open(shap_path, 'r') as f:
            shap_img = ImageReader(io.BytesIO(base64.b64decode(f.read())))
            c.drawImage(shap_img, 60, y, width=480, height=200, preserveAspectRatio=True)

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(width/2, 30, "Confidential: SOE Medical AI Research Report")

    # --- Page 2: Cytology (If High Risk) ---
    if 'cell_type' in session_data:
        c.showPage()
        y = height - 60
        c.setFillColor(PRIMARY)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "Cytology Visual Analysis (Stage 2)")
        y -= 40
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"Cell Classification: {session_data.get('cell_type')}")
        c.drawRightString(width-50, y, f"Model Confidence: {session_data.get('cell_confidence', 0):.2f}%")
        y -= 320
        
        gc_path = os.path.join(app_instance.config['UPLOAD_FOLDER'], f'results_{user_id}', 'gradcam.txt')
        if os.path.exists(gc_path):
            with open(gc_path, 'r') as f:
                gc_img = ImageReader(io.BytesIO(base64.b64decode(f.read())))
                c.drawImage(gc_img, 100, y, width=400, height=300)
                y -= 20
                c.setFont("Helvetica-Oblique", 9)
                c.drawCentredString(width/2, y, "Heatmap (Grad-CAM) highlights cellular regions analyzed for malignancy.")

    # --- Page 3: Recommendations (FIXED VARIABLE NAME) ---
    c.showPage()
    y = height - 50 # Changed 'H' to 'height'
    c.setFont('Helvetica-Bold', 14)
    c.setFillColor(PRIMARY)
    c.drawString(50, y, 'Clinical Recommendations:')
    y -= 30
    c.setFont('Helvetica', 10)
    recs = [
        '• Continue regular cervical cancer screenings as advised by your healthcare provider.',
        '• Maintain a healthy lifestyle with balanced diet and regular exercise.',
        '• Attend routine gynecological check-ups annually.',
        '• Discuss HPV vaccination with your doctor if not already vaccinated.',
        '• Report any unusual symptoms (abnormal bleeding, discharge) immediately.',
        '• Avoid smoking — it significantly increases cervical cancer risk.',
    ]
    for rec in recs:
        c.drawString(70, y, rec)
        y -= 18

    y -= 30
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, y, 'Medical Disclaimer:')
    y -= 20
    c.setFont('Helvetica', 9)
    c.setFillColor(colors.black)
    disclaimer = [
        'This AI-powered assessment is for informational and academic purposes only.',
        'It does NOT constitute medical diagnosis or replace professional consultation.',
        'Always consult a qualified healthcare provider for medical advice and treatment.'
    ]
    for line in disclaimer:
        c.drawString(70, y, line)
        y -= 14

    c.save()
    buffer.seek(0)
    return buffer
    
   
@app.route('/get_gradcam')
def get_gradcam():
    """Serve Grad-CAM image from file"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    gradcam_path = os.path.join(app.config['UPLOAD_FOLDER'], f'results_{user_id}', 'gradcam.txt')
    
    if os.path.exists(gradcam_path):
        with open(gradcam_path, 'r') as f:
            gradcam_data = f.read()
        return jsonify({'gradcam': gradcam_data})
    
    return jsonify({'error': 'Grad-CAM not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)