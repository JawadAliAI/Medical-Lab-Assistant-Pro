from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
import os
from datetime import datetime
import json

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Lab data structure
LAB_DATA = {
    "Total PSA": {"value": 0.421, "range": "0 - 4", "unit": "ng/ml", "status": "Normal"},
    "Free PSA": {"value": 0.238, "range": "0 - 4", "unit": "ng/ml", "status": "Normal"},
    "Hemoglobin": {"value": 16.6, "range": "13.6 - 16.7", "unit": "g/dL", "status": "Normal"},
    "RBC Count": {"value": 5.8, "range": "4.56 - 6.22", "unit": "x10^6/µL", "status": "Normal"},
    "HCT": {"value": 49.1, "range": "35 - 49", "unit": "%", "status": "High"},
    "MCV": {"value": 84.4, "range": "75 - 97", "unit": "fL", "status": "Normal"},
    "MCH": {"value": 28.5, "range": "26.5 - 33", "unit": "pg", "status": "Normal"},
    "MCHC": {"value": 33.8, "range": "32 - 36", "unit": "g/dL", "status": "Normal"},
    "RDW-CV": {"value": 16.5, "range": "11.8 - 15.6", "unit": "%", "status": "High"},
    "Platelet Count": {"value": 256, "range": "150 - 450", "unit": "x10^6/µL", "status": "Normal"},
    "MPV": {"value": 10.5, "range": "7.4 - 11", "unit": "fL", "status": "Normal"},
    "WBC": {"value": 8.5, "range": "3.38 - 11.31", "unit": "x10^3/µL", "status": "Normal"},
    "Neutrophils": {"value": 4.74, "range": "1.21 - 6.81", "unit": "x10^3/µL", "status": "Normal"},
    "Lymphocytes": {"value": 2.6, "range": "1.31 - 4.12", "unit": "x10^3/µL", "status": "Normal"},
    "Monocytes": {"value": 0.8, "range": "0.26 - 0.83", "unit": "x10^3/µL", "status": "Normal"},
    "Eosinophils": {"value": 0.37, "range": "0.05 - 0.64", "unit": "x10^3/µL", "status": "Normal"},
    "Basophils": {"value": 0, "range": "0.01 - 0.14", "unit": "x10^3/µL", "status": "Low"},
    "Serum Ferritin": {"value": 27.4, "range": "11 - 365", "unit": "ng/ml", "status": "Normal"},
    "Free T4": {"value": 1.62, "range": "0.9 - 1.75", "unit": "ng/dL", "status": "Normal"},
    "Free T3": {"value": 3.06, "range": "2 - 4.2", "unit": "pg/ml", "status": "Normal"},
    "FSH": {"value": 9.38, "range": "1 - 9.3", "unit": "mIU/ml", "status": "High"},
    "LH": {"value": 15, "range": "1.1 - 10", "unit": "mIU/ml", "status": "High"},
    "Progesterone": {"value": 0.757, "range": "< 1.35", "unit": "ng/ml", "status": "Normal"},
    "Free Testosterone": {"value": 16, "range": "9-54", "unit": "pg/ml", "status": "Normal"},
    "Prolactin": {"value": 5.31, "range": "2.52 - 26.81", "unit": "ng/ml", "status": "Normal"},
    "TSH": {"value": 1.39, "range": "0.3 - 4.5", "unit": "uIU/mL", "status": "Normal"},
    "IgE": {"value": 43.4, "range": "0 - 200", "unit": "IU/mL", "status": "Normal"},
    "Vitamin D": {"value": 23.9, "range": "30 - 100", "unit": "ng/ml", "status": "Low"},
    "Vitamin B12": {"value": 335, "range": "190 - 950", "unit": "pg/ml", "status": "Normal"}
}

class MedicalChatbot:
    def __init__(self):
        self.llm = None
        self.memory = ConversationBufferWindowMemory(k=10, return_messages=True)
        self.conversation = None
        
    def initialize_llm(self, api_key):
        """Initialize the LLM with API key"""
        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.7,
                max_tokens=1024
            )
            
            # Create conversation chain with custom prompt
            self.conversation = ConversationChain(
                llm=self.llm,
                memory=self.memory,
                verbose=True
            )
            
            return True
        except Exception as e:
            print(f"Error initializing LLM: {str(e)}")
            return False
    
    def get_system_prompt(self):
        """Generate comprehensive system prompt with lab data"""
        lab_summary = self._format_lab_data()
        abnormal_findings = self._get_abnormal_findings()
        
        system_prompt = f"""You are Dr. AI, a highly experienced medical doctor specializing in laboratory medicine and internal medicine. You are analyzing a patient's comprehensive lab results and providing professional medical consultation.

PATIENT'S COMPLETE LAB RESULTS:
{lab_summary}

KEY ABNORMAL FINDINGS REQUIRING ATTENTION:
{abnormal_findings}

MEDICAL GUIDELINES FOR RESPONSES:
1. **Professional Medical Approach**: Respond as an experienced physician would during a consultation
2. **Evidence-Based Analysis**: Provide medical explanations based on established clinical knowledge
3. **Clinical Correlation**: Consider how different lab values relate to each other and overall health
4. **Risk Stratification**: Explain the clinical significance of abnormal values
5. **Differential Diagnosis**: When appropriate, discuss possible causes for abnormal findings
6. **Treatment Recommendations**: Suggest appropriate next steps, lifestyle modifications, or further testing
7. **Patient Education**: Explain complex medical terms in understandable language
8. **Safety First**: Always emphasize the importance of follow-up with healthcare providers

COMMUNICATION STYLE:
- Be thorough but accessible
- Show empathy and understanding
- Provide specific, actionable advice
- Use medical terminology appropriately with explanations
- Structure responses clearly with bullet points or sections when helpful
- Always end with appropriate medical disclaimers

IMPORTANT CLINICAL CONTEXT:
- The patient's thyroid function (TSH, T3, T4) is normal
- Testosterone levels are within normal range despite elevated gonadotropins
- PSA levels are reassuringly low
- Most blood counts are normal with minor variations
- No evidence of autoimmune conditions based on antibody tests
- Negative infectious disease markers

Remember: You are providing medical consultation based on these specific lab results. Always recommend consulting with the patient's healthcare provider for comprehensive care and treatment decisions."""

        return system_prompt
    
    def _format_lab_data(self):
        """Format lab data for the prompt"""
        formatted_data = []
        for test, data in LAB_DATA.items():
            status_indicator = "⚠️" if data["status"] in ["High", "Low"] else "✅"
            formatted_data.append(
                f"{status_indicator} {test}: {data['value']} {data['unit']} "
                f"(Reference: {data['range']}) - {data['status']}"
            )
        return "\n".join(formatted_data)
    
    def _get_abnormal_findings(self):
        """Extract and format abnormal findings"""
        abnormal = []
        for test, data in LAB_DATA.items():
            if data["status"] in ["High", "Low"]:
                clinical_significance = self._get_clinical_significance(test, data["status"])
                abnormal.append(f"• {test}: {data['value']} {data['unit']} ({data['status']}) - {clinical_significance}")
        
        return "\n".join(abnormal) if abnormal else "No significant abnormal findings."
    
    def _get_clinical_significance(self, test, status):
        """Get clinical significance of abnormal values"""
        significance_map = {
            ("Vitamin D", "Low"): "Deficiency - may affect bone health, immune function, and mood",
            ("FSH", "High"): "Elevated follicle-stimulating hormone - may indicate aging, menopause, or testicular dysfunction",
            ("LH", "High"): "Elevated luteinizing hormone - suggests gonadal dysfunction or hormonal imbalance", 
            ("HCT", "High"): "Elevated hematocrit - may indicate dehydration, polycythemia, or high altitude exposure",
            ("RDW-CV", "High"): "Increased red cell distribution width - suggests mixed cell populations or nutritional deficiencies",
            ("Basophils", "Low"): "Low basophils - usually not clinically significant, may be stress-related"
        }
        
        return significance_map.get((test, status), "Requires clinical correlation")
    
    def get_response(self, user_message):
        """Generate response using LangChain"""
        if not self.llm:
            return "Please initialize the chatbot with your API key first."
        
        try:
            # Add system context to the conversation if it's the first message
            if len(self.memory.chat_memory.messages) == 0:
                system_message = SystemMessage(content=self.get_system_prompt())
                self.memory.chat_memory.add_message(system_message)
            
            # Get response from conversation chain
            response = self.conversation.predict(input=user_message)
            
            return response
            
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your question: {str(e)}. Please try again or check your API key."

# Global chatbot instance
chatbot = MedicalChatbot()

@app.route('/')
def index():
    """Serve the main HTML page"""
    try:
        with open('inddex.html', 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return jsonify({"error": "Frontend file not found"}), 404

@app.route('/api/init', methods=['POST'])
def initialize_chatbot():
    """Initialize chatbot with API key"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({"error": "API key is required"}), 400
        
        success = chatbot.initialize_llm(api_key)
        
        if success:
            return jsonify({
                "message": "Chatbot initialized successfully",
                "status": "ready",
                "lab_summary": chatbot._format_lab_data()
            })
        else:
            return jsonify({"error": "Failed to initialize chatbot"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        if not chatbot.llm:
            return jsonify({"error": "Chatbot not initialized. Please provide API key first."}), 400
        
        response = chatbot.get_response(user_message)
        
        return jsonify({
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/lab-data', methods=['GET'])
def get_lab_data():
    """Get formatted lab data"""
    try:
        return jsonify({
            "lab_data": LAB_DATA,
            "abnormal_findings": chatbot._get_abnormal_findings(),
            "total_tests": len(LAB_DATA)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_conversation():
    """Reset conversation memory"""
    try:
        chatbot.memory.clear()
        return jsonify({"message": "Conversation reset successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "chatbot_ready": chatbot.llm is not None
    })

if __name__ == '__main__':
    print("🩺 Medical Chatbot Backend Starting...")
    print("📊 Lab data loaded with", len(LAB_DATA), "test results")
    print("🚀 Server starting on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)