#!/usr/bin/env python3
"""
PTAM DOCX Generation Regression Test
Tests the PTAM DOCX generation after refactoring into helper functions.
"""
import requests
import json
import os
from datetime import datetime

# Get backend URL from frontend .env
BACKEND_URL = "https://review-simples.preview.emergentagent.com/api"

def test_ptam_docx_regression():
    """
    Regression test for PTAM DOCX generation after refactoring.
    Tests the complete flow: register/login -> create PTAM -> download DOCX -> verify -> cleanup
    """
    print("🧪 PTAM DOCX Generation Regression Test")
    print("=" * 60)
    
    # Test credentials as specified in the request
    test_email = "docx-regress-test@romatec.com"
    test_password = "senha123"
    
    session = requests.Session()
    token = None
    ptam_id = None
    
    try:
        # Step 1: Register or login user
        print("1️⃣ Authenticating user...")
        
        # Try login first
        login_response = session.post(f"{BACKEND_URL}/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        
        if login_response.status_code == 401:
            # User doesn't exist, register
            print("   User not found, registering...")
            register_response = session.post(f"{BACKEND_URL}/auth/register", json={
                "name": "DOCX Regression Test User",
                "email": test_email,
                "password": test_password,
                "role": "Engenheiro Civil",
                "crea": "CREA-MA 123456"
            })
            
            if register_response.status_code != 200:
                print(f"   ❌ Registration failed: {register_response.status_code}")
                print(f"   Response: {register_response.text}")
                return False
                
            auth_data = register_response.json()
            print(f"   ✅ User registered successfully")
        else:
            if login_response.status_code != 200:
                print(f"   ❌ Login failed: {login_response.status_code}")
                print(f"   Response: {login_response.text}")
                return False
                
            auth_data = login_response.json()
            print(f"   ✅ User logged in successfully")
        
        token = auth_data["token"]
        user_id = auth_data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Create PTAM with minimal data as specified
        print("2️⃣ Creating PTAM with minimal data...")
        
        ptam_data = {
            "property_label": "Teste Regressão",
            "solicitante": "Cliente XYZ",
            "impact_areas": [
                {
                    "name": "Área 01",
                    "classification": "Rural",
                    "area_sqm": 1000,
                    "unit_value": 50
                }
            ]
        }
        
        create_response = session.post(f"{BACKEND_URL}/ptam", 
                                     json=ptam_data, 
                                     headers=headers)
        
        if create_response.status_code != 200:
            print(f"   ❌ PTAM creation failed: {create_response.status_code}")
            print(f"   Response: {create_response.text}")
            return False
            
        ptam = create_response.json()
        ptam_id = ptam["id"]
        print(f"   ✅ PTAM created successfully (ID: {ptam_id})")
        print(f"   📄 PTAM Number: {ptam.get('number', 'N/A')}")
        
        # Step 3: Download DOCX via GET /api/ptam/{id}/docx
        print("3️⃣ Downloading DOCX file...")
        
        docx_response = session.get(f"{BACKEND_URL}/ptam/{ptam_id}/docx", 
                                   headers=headers)
        
        if docx_response.status_code != 200:
            print(f"   ❌ DOCX download failed: {docx_response.status_code}")
            print(f"   Response: {docx_response.text}")
            return False
            
        # Step 4: Verify response format and content
        print("4️⃣ Verifying DOCX response...")
        
        # Check Content-Type
        content_type = docx_response.headers.get("Content-Type", "")
        expected_content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        if content_type != expected_content_type:
            print(f"   ❌ Wrong Content-Type: {content_type}")
            print(f"   Expected: {expected_content_type}")
            return False
        print(f"   ✅ Content-Type correct: {content_type}")
        
        # Check Content-Disposition header
        content_disposition = docx_response.headers.get("Content-Disposition", "")
        if "attachment" not in content_disposition or "PTAM_" not in content_disposition:
            print(f"   ❌ Wrong Content-Disposition: {content_disposition}")
            return False
        print(f"   ✅ Content-Disposition correct: {content_disposition}")
        
        # Check body size > 5000 bytes
        body_size = len(docx_response.content)
        if body_size <= 5000:
            print(f"   ❌ Body size too small: {body_size} bytes (expected > 5000)")
            return False
        print(f"   ✅ Body size adequate: {body_size:,} bytes")
        
        # Check first 2 bytes are "PK" (ZIP/DOCX signature)
        if len(docx_response.content) < 2 or docx_response.content[:2] != b"PK":
            print(f"   ❌ Invalid DOCX signature: {docx_response.content[:2]}")
            return False
        print(f"   ✅ DOCX signature valid: {docx_response.content[:2]}")
        
        # Additional verification: Check if it's a valid ZIP structure
        try:
            import zipfile
            from io import BytesIO
            
            zip_buffer = BytesIO(docx_response.content)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                file_list = zip_file.namelist()
                # DOCX files should contain these essential files
                required_files = ["[Content_Types].xml", "word/document.xml"]
                for req_file in required_files:
                    if req_file not in file_list:
                        print(f"   ❌ Missing required DOCX file: {req_file}")
                        return False
                print(f"   ✅ Valid DOCX structure with {len(file_list)} files")
        except Exception as e:
            print(f"   ❌ Invalid ZIP/DOCX structure: {str(e)}")
            return False
        
        print("5️⃣ All DOCX verification checks passed! ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        return False
        
    finally:
        # Step 5: Cleanup - Delete the test PTAM
        if ptam_id and token:
            print("6️⃣ Cleaning up test data...")
            try:
                delete_response = session.delete(f"{BACKEND_URL}/ptam/{ptam_id}", 
                                                headers={"Authorization": f"Bearer {token}"})
                if delete_response.status_code == 200:
                    print("   ✅ Test PTAM deleted successfully")
                else:
                    print(f"   ⚠️ Failed to delete test PTAM: {delete_response.status_code}")
            except Exception as e:
                print(f"   ⚠️ Cleanup error: {str(e)}")


def main():
    """Run the PTAM DOCX regression test."""
    print(f"🚀 Starting PTAM DOCX Regression Test at {datetime.now()}")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print()
    
    success = test_ptam_docx_regression()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 PTAM DOCX REGRESSION TEST PASSED")
        print("✅ All verification checks completed successfully")
        print("✅ DOCX generation working correctly after refactoring")
    else:
        print("💥 PTAM DOCX REGRESSION TEST FAILED")
        print("❌ Issues found in DOCX generation")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    main()