
import streamlit as st
import os
from PIL import Image
import threading
import time
import shutil
import json
import base64
from openai import OpenAI
from datetime import datetime
# Initialize OpenAI client
api_key = st.secrets["OPENAI_API_KEY"]


client = OpenAI(api_key=api_key)

# Create required directories
for dir in ["uploads", "processed"]:
    if not os.path.exists(dir):
        os.makedirs(dir)

# Configure Streamlit page
st.set_page_config(
    page_title="Label Compliance Checker",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Utility Functions
def parse_openai_response(description):

    """Parse OpenAI response that comes wrapped in markdown code blocks"""
    try:
        # Handle string that's already JSON
        if isinstance(description, dict):
            return description
            
        # Remove unicode whitespace characters
        description = description.replace('\u202f', ' ')
        
        # Remove markdown code block syntax if present
        if description.startswith('```json\n'):
            description = description[8:-4]  # Remove ```json\n and ```
        elif description.startswith('```\n'):
            description = description[4:-4]  # Remove ```\n and ```
        
        # Strip any leading/trailing whitespace
        description = description.strip()
            
        # Parse the cleaned JSON string
        return json.loads(description)
    except Exception as e:
        print(f"Raw description: {description}")
        raise Exception(f"Error parsing JSON response: {str(e)}")

# When loading the analysis file, update the call:
def analyze_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        print("Uploading image to OpenAI...") 
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Please analyze the provided product label and check for basic mandatory compliance requirements. Don't check if the data is present. Just check if field is present or not as these will be generic labels and data will be filled in fields later. Return a JSON response ONLY and no other text for the following core elements:

    {
    "manufacturer_info": {
        "compliant": boolean,
        "found_name": string,
        "found_address": string,
        "notes": string
    },
    "dates": {
        "manufacturing_date": {
        "compliant": boolean,
        "found_date": string,
        "notes": string
        },
        "expiry_date": {
        "compliant": boolean,
        "found_date": string,
        "notes": string
        }
    },
    "product_content": {
        "ingredients_list": {
        "compliant": boolean,
        "found_ingredients": [string],
        "notes": string
        },
        "net_quantity": {
        "compliant": boolean,
        "found_value": string,
        "notes": string
        }
    },
    "overall_status": {
        "is_compliant": boolean,
        "missing_elements": [string],
        "recommendations": [string]
    }
    }

    Rules:
    1. Check if manufacturer name and complete address are present
    2. Verify dates are in clear, readable format
    3. Confirm ingredients are listed in descending order
    4. Ensure net quantity is in metric units
    5. Mark missing required elements in overall_status"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        print("Returning Image Description...") 
        return response.choices[0].message.content
    except Exception as e:
        print("Error analyzing image..." + str(e))
        print("Error analyzing image...")

        raise Exception(f"Error analyzing image: {str(e)}")

def background_process(filename):
    """Process uploaded image in background"""
    source = os.path.join("uploads", filename)
    destination = os.path.join("processed", filename)
    
    # Copy file to processed directory
    shutil.copy2(source, destination)
    
    try:
        # Analyze image
        description = analyze_image(source)
        results = {
            "filename": filename,
            "description": description,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        results = {
            "filename": filename,
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # Save analysis results
    with open(os.path.join("processed", f"{filename}_analysis.json"), "w") as f:
        json.dump(results, f, indent=4)

def display_compliance_status(desc):
    """Display compliance status with consistent styling"""
    status = desc['overall_status']['is_compliant']
    color = "green" if status else "red"
    icon = "✅" if status else "❌"
    
    st.markdown(
        f"""
        <div style='background-color: {"#f0f9f0" if status else "#fff0f0"}; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin-bottom: 20px'>
            <h3 style='color: {color}; margin: 0; font-size: 20px'>
                Overall Compliance Status: {icon}
            </h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    if desc['overall_status']['missing_elements']:
        st.markdown("""
            <h4 style='color: #bf0000; font-size: 18px'>Missing Elements:</h4>
        """, unsafe_allow_html=True)
        for element in desc['overall_status']['missing_elements']:
            st.markdown(f"<p style='margin-left: 20px; font-size: 16px'>• {element}</p>", unsafe_allow_html=True)

def display_compliance_detail(label, value, notes=""):
    """Display compliance details with consistent styling"""
    st.markdown(f"<p style='font-size: 16px; margin-bottom: 5px'><strong>{label}:</strong>", unsafe_allow_html=True)
    
    if isinstance(value, bool):
        icon = "✅" if value else "❌"
        st.markdown(f"<p style='font-size: 16px; margin-left: 20px'>{icon}</p>", unsafe_allow_html=True)
    elif isinstance(value, list):
        for item in value:
            st.markdown(f"<p style='margin-left: 20px; font-size: 16px'>• {item}</p>", unsafe_allow_html=True)
    elif value:
        st.markdown(f"<p style='margin-left: 20px; font-size: 16px'>{value}</p>", unsafe_allow_html=True)
    
    if notes and notes.strip():
        st.markdown(
            f"""
            <div style='background-color: #e1f5fe; 
                        padding: 10px; 
                        border-radius: 5px; 
                        margin: 10px 0; 
                        font-size: 16px'>
                {notes}
            </div>
            """, 
            unsafe_allow_html=True
        )
        
# Update expander headers to use consistent styling
st.markdown("""
    <style>
    .streamlit-expanderHeader {
        font-size: 18px !important;
        font-weight: 600 !important;
    }
    .stExpander {
        border: 1px solid #ddd !important;
        border-radius: 5px !important;
        margin-bottom: 10px !important;
    }
    h3 {
        font-size: 20px !important;
    }
    h4 {
        font-size: 18px !important;
    }
    </style>
    """, unsafe_allow_html=True)
def display_compliance_detail(label, value, notes=""):
    """Display a compliance detail with appropriate formatting"""
    if isinstance(value, bool):
        icon = "✅" if value else "❌"
        st.write(f"{label}: {icon}")
    elif isinstance(value, list):
        st.write(f"{label}:")
        for item in value:
            st.write(f"  • {item}")
    elif value:  # Only show non-empty strings
        st.write(f"{label}: {value}")
    
    if notes and notes.strip():
        st.info(notes)

# Page Functions
def upload_page():
    """Upload page functionality"""
    st.title("Label Image Upload")
    st.markdown("---")
    
    uploaded_file = st.file_uploader(
        "Choose a label image to analyze...", 
        type=["jpg", "png", "jpeg"]
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Label", use_container_width=True)
        
        with col2:
            st.info("Image Details:")
            st.write(f"📁 Filename: {uploaded_file.name}")
            st.write(f"📏 Size: {uploaded_file.size / 1024:.1f} KB")
            
            # Save and process image
            upload_path = os.path.join("uploads", uploaded_file.name)
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success("✅ Image uploaded successfully!")
            
            # Start background processing
            with st.spinner("Starting analysis..."):
                thread = threading.Thread(
                    target=background_process, 
                    args=(uploaded_file.name,)
                )
                thread.daemon = True
                thread.start()
                time.sleep(2)  # Give time for processing to start
                st.info("🔄 Analysis started in background")
                
                # Add view analysis button
                if st.button("View Analysis"):
                    st.experimental_set_query_params(page="analysis")
                    st.rerun()

def analysis_page():
    """Analysis page functionality"""
    st.title("Label Analysis Results")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📊 Grid View", "🔍 Detailed View"])
    
    with tab1:
        grid_view()
    with tab2:
        detailed_view()

def grid_view():
    """Grid view of processed images"""
    cols = st.columns(3)
    processed_files = {}
    
    # Get processed files
    for file in os.listdir("processed"):
        if file.endswith("_analysis.json"):
            continue
        json_file = f"{file}_analysis.json"
        if os.path.exists(os.path.join("processed", json_file)):
            processed_files[file] = json_file
    
    if not processed_files:
        st.warning("No processed images found")
        return
    
    # Display grid
    for idx, (img_file, json_file) in enumerate(processed_files.items()):
        col = cols[idx % 3]
        with col:
            with st.container():
                st.markdown("---")
                img_path = os.path.join("processed", img_file)
                json_path = os.path.join("processed", json_file)
                
                # Display image
                image = Image.open(img_path)
                st.image(image, caption=img_file, use_container_width=True)
                
                # Display basic analysis
                try:
                    with open(json_path, 'r') as f:
                        analysis = json.load(f)
                    
                    desc = parse_openai_response(analysis['description'])
                    display_compliance_status(desc)
                    
                    # Show key stats
                    st.write("Quick Summary:")
                    missing = len(desc['overall_status']['missing_elements'])
                    st.write(f"Missing Elements: {missing}")
                    st.write(f"Analysis Time: {analysis['timestamp']}")
                except Exception as e:
                    st.error(f"Error loading analysis: {str(e)}")

def detailed_view():
    """Detailed view of individual images"""
    processed_images = [f for f in os.listdir("processed") 
                       if not f.endswith("_analysis.json")]
    
    if not processed_images:
        st.warning("No processed images found")
        return
    
    selected_image = st.selectbox(
        "Select an image to view detailed analysis",
        processed_images
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        img_path = os.path.join("processed", selected_image)
        image = Image.open(img_path)
        st.image(image, caption=selected_image, use_container_width=True)
    
    with col2:
        json_path = os.path.join("processed", f"{selected_image}_analysis.json")
        if not os.path.exists(json_path):
            st.error("Analysis file not found")
            return
            
        with open(json_path, 'r') as f:
            analysis = json.load(f)
        
        st.info(f"Analysis Timestamp: {analysis['timestamp']}")
        
        try:
            desc = parse_openai_response(analysis['description'])
            
            # Manufacturer Information
            with st.expander("Manufacturer Information", expanded=True):
                info = desc['manufacturer_info']
                display_compliance_detail("Compliance", info['compliant'])
                display_compliance_detail("Name", info['found_name'])
                display_compliance_detail("Address", info['found_address'])
                if info['notes']:
                    st.info(info['notes'])
            
            # Dates Information
            with st.expander("Dates Information", expanded=True):
                mfg = desc['dates']['manufacturing_date']
                exp = desc['dates']['expiry_date']
                
                st.subheader("Manufacturing Date")
                display_compliance_detail("Compliance", mfg['compliant'])
                display_compliance_detail("Date", mfg['found_date'])
                if mfg['notes']:
                    st.info(mfg['notes'])
                
                st.subheader("Expiry Date")
                display_compliance_detail("Compliance", exp['compliant'])
                display_compliance_detail("Date", exp['found_date'])
                if exp['notes']:
                    st.info(exp['notes'])
            
            # Product Content
            with st.expander("Product Content", expanded=True):
                ing = desc['product_content']['ingredients_list']
                qty = desc['product_content']['net_quantity']
                
                st.subheader("Ingredients")
                display_compliance_detail("Compliance", ing['compliant'])
                display_compliance_detail("Found Ingredients", ing['found_ingredients'])
                if ing['notes']:
                    st.info(ing['notes'])
                
                st.subheader("Net Quantity")
                display_compliance_detail("Compliance", qty['compliant'])
                display_compliance_detail("Value", qty['found_value'])
                if qty['notes']:
                    st.info(qty['notes'])
            
            # Overall Status
            with st.expander("Overall Status", expanded=True):
                st.subheader("Final Assessment")
                display_compliance_status(desc)
                
                # if desc['overall_status']['missing_elements']:
                #     st.write("Missing Elements:")
                #     for element in desc['overall_status']['missing_elements']:
                #         st.write(f"• {element}")
                
                if desc['overall_status']['recommendations']:
                    st.write("Recommendations:")
                    for rec in desc['overall_status']['recommendations']:
                        st.write(f"• {rec}")
                        
        except Exception as e:
            st.error(f"Error parsing analysis: {str(e)}")
            st.code(analysis['description'], language="json")

def main():
    """Main application"""
    # Sidebar navigation
    st.sidebar.title("Navigation")
    current_page = st.sidebar.radio(
        "Select Page",
        ["Upload", "Analysis"],
        key="nav"
    )
    # VIP part. Uncomment if app does not work
    # ---------------------------------------
    # ---------------------------------------
    # ---------------------------------------   
    # ---------------------------------------
    # Set query parameter based on selection
    # st.experimental_set_query_params(
    #     page=current_page.lower()
    # )
    
    # Display selected page
    if current_page == "Upload":
        upload_page()
    else:
        analysis_page()

if __name__ == "__main__":
    main()
