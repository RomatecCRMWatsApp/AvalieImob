#!/usr/bin/env python3
"""
Backend test suite for RomaTec AvalieImob PTAM endpoints
Testing the NEW PTAM (Parecer Técnico de Avaliação Mercadológica) endpoints
"""

import requests
import json
import os
from pathlib import Path

# Get backend URL from frontend .env
frontend_env_path = Path("/app/frontend/.env")
backend_url = None

if frontend_env_path.exists():
    with open(frontend_env_path, 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                backend_url = line.split('=', 1)[1].strip()
                break

if not backend_url:
    print("❌ CRITICAL: Could not find REACT_APP_BACKEND_URL in /app/frontend/.env")
    exit(1)

BASE_URL = f"{backend_url}/api"
print(f"🔗 Testing backend at: {BASE_URL}")

# Test data
TEST_EMAIL_1 = "ptam-test@romatec.com"
TEST_PASSWORD = "senha123"
TEST_EMAIL_2 = "ptam-test2@romatec.com"

# Global variables for test state
user1_token = None
user2_token = None
ptam_id = None

def test_auth_setup():
    """Setup authentication for testing"""
    global user1_token, user2_token
    
    print("\n🔐 Setting up authentication...")
    
    # Register first user
    register_data = {
        "name": "PTAM Test User 1",
        "email": TEST_EMAIL_1,
        "password": TEST_PASSWORD,
        "role": "Engenheiro Civil",
        "crea": "CREA-MA 123456"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code == 200:
        user1_token = response.json()["token"]
        print(f"✅ User 1 registered successfully")
    elif response.status_code == 400 and "já cadastrado" in response.text:
        # User already exists, try login
        login_data = {"email": TEST_EMAIL_1, "password": TEST_PASSWORD}
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            user1_token = response.json()["token"]
            print(f"✅ User 1 logged in successfully")
        else:
            print(f"❌ User 1 login failed: {response.status_code} - {response.text}")
            return False
    else:
        print(f"❌ User 1 registration failed: {response.status_code} - {response.text}")
        return False
    
    # Register second user for isolation testing
    register_data2 = {
        "name": "PTAM Test User 2",
        "email": TEST_EMAIL_2,
        "password": TEST_PASSWORD,
        "role": "Arquiteto",
        "crea": "CREA-MA 654321"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data2)
    if response.status_code == 200:
        user2_token = response.json()["token"]
        print(f"✅ User 2 registered successfully")
    elif response.status_code == 400 and "já cadastrado" in response.text:
        # User already exists, try login
        login_data = {"email": TEST_EMAIL_2, "password": TEST_PASSWORD}
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            user2_token = response.json()["token"]
            print(f"✅ User 2 logged in successfully")
        else:
            print(f"❌ User 2 login failed: {response.status_code} - {response.text}")
            return False
    else:
        print(f"❌ User 2 registration failed: {response.status_code} - {response.text}")
        return False
    
    return True

def test_create_ptam():
    """Test 1: Create PTAM with comprehensive data"""
    global ptam_id
    
    print("\n📝 Test 1: Creating PTAM...")
    
    headers = {"Authorization": f"Bearer {user1_token}"}
    
    ptam_data = {
        "property_label": "Gleba Pequiá-Brejão, Parte do Lote 78",
        "purpose": "Avaliação mercadológica para fins judiciais em ação de servidão administrativa",
        "solicitante": "CEIMA - Sociedade Espiritusantense de Industrialização de Madeiras LTDA",
        "judicial_process": "0806769-95.2025.8.10.0022",
        "judicial_action": "Servidão Administrativa",
        "forum": "1ª Vara Cível de Açailândia",
        "requerente": "Equatorial Maranhão Distribuidora de Energia S/A",
        "requerido": "CEIMA - Sociedade Espiritosantense",
        "property_address": "BR 222, ALTURA DO KM 90 - GLEBA PEQUIÁ-BREJÃO",
        "property_city": "Açailândia/MA",
        "property_matricula": "2591",
        "property_area_ha": 53.7013,
        "property_area_sqm": 537013,
        "vistoria_date": "2026-01-15",
        "vistoria_objective": "Verificar caracterização física e contexto urbano",
        "topography": "Terreno predominantemente plano com leve inclinação",
        "methodology": "Método Comparativo Direto de Dados de Mercado",
        "methodology_justification": "Aplicação conforme NBR 14.653",
        "impact_areas": [
            {
                "name": "Área de Impacto 01",
                "classification": "Rural",
                "area_sqm": 24494,
                "unit_value": 28.18,
                "total_value": 690231.00,
                "samples": [
                    {"number": 1, "neighborhood": "Zona Rural", "area_total": 9567515, "value": 210566915.14, "value_per_sqm": 22.01},
                    {"number": 2, "neighborhood": "Gleba 14", "area_total": 1138894, "value": 25800000, "value_per_sqm": 22.65}
                ]
            },
            {
                "name": "Área de Impacto 02",
                "classification": "Urbana",
                "area_sqm": 27822.15,
                "unit_value": 381.73,
                "total_value": 10626883.72,
                "samples": [
                    {"number": 1, "neighborhood": "Pequiá", "area_total": 10000, "value": 3268172.89, "value_per_sqm": 326.82}
                ]
            }
        ],
        "total_indemnity": 11317114.72,
        "total_indemnity_words": "onze milhões, trezentos e dezessete mil, cento e quatorze reais e setenta e dois centavos",
        "conclusion_city": "Açailândia/MA",
        "conclusion_date": "2026-01-21"
    }
    
    response = requests.post(f"{BASE_URL}/ptam", json=ptam_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        ptam_id = result["id"]
        number = result.get("number", "")
        user_id = result.get("user_id", "")
        
        print(f"✅ PTAM created successfully")
        print(f"   - ID: {ptam_id}")
        print(f"   - Number: {number}")
        print(f"   - User ID: {user_id}")
        
        # Verify auto-generated number format (should be like "2026-0001")
        if number and "-" in number:
            year, seq = number.split("-", 1)
            if year == "2026" and seq.isdigit():
                print(f"✅ Auto-generated number format correct: {number}")
            else:
                print(f"⚠️  Auto-generated number format unexpected: {number}")
        else:
            print(f"⚠️  Auto-generated number missing or invalid: {number}")
        
        return True
    else:
        print(f"❌ PTAM creation failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_list_ptam():
    """Test 2: List PTAMs"""
    print("\n📋 Test 2: Listing PTAMs...")
    
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.get(f"{BASE_URL}/ptam", headers=headers)
    
    if response.status_code == 200:
        ptams = response.json()
        print(f"✅ PTAMs listed successfully")
        print(f"   - Count: {len(ptams)}")
        
        if len(ptams) > 0:
            ptam = ptams[0]
            print(f"   - First PTAM ID: {ptam.get('id', 'N/A')}")
            print(f"   - First PTAM Number: {ptam.get('number', 'N/A')}")
            print(f"   - Property Label: {ptam.get('property_label', 'N/A')}")
        
        return True
    else:
        print(f"❌ PTAM listing failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_get_ptam_by_id():
    """Test 3: Get PTAM by ID"""
    print("\n🔍 Test 3: Getting PTAM by ID...")
    
    if not ptam_id:
        print("❌ No PTAM ID available for testing")
        return False
    
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.get(f"{BASE_URL}/ptam/{ptam_id}", headers=headers)
    
    if response.status_code == 200:
        ptam = response.json()
        print(f"✅ PTAM retrieved successfully")
        print(f"   - ID: {ptam.get('id', 'N/A')}")
        print(f"   - Number: {ptam.get('number', 'N/A')}")
        print(f"   - Property Label: {ptam.get('property_label', 'N/A')}")
        print(f"   - Impact Areas Count: {len(ptam.get('impact_areas', []))}")
        
        # Verify nested data structure
        impact_areas = ptam.get('impact_areas', [])
        if impact_areas:
            first_area = impact_areas[0]
            samples = first_area.get('samples', [])
            print(f"   - First area samples count: {len(samples)}")
            if samples:
                print(f"   - First sample neighborhood: {samples[0].get('neighborhood', 'N/A')}")
        
        return True
    else:
        print(f"❌ PTAM retrieval failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_update_ptam():
    """Test 4: Update PTAM"""
    print("\n✏️  Test 4: Updating PTAM...")
    
    if not ptam_id:
        print("❌ No PTAM ID available for testing")
        return False
    
    headers = {"Authorization": f"Bearer {user1_token}"}
    
    # First get the current PTAM data
    response = requests.get(f"{BASE_URL}/ptam/{ptam_id}", headers=headers)
    if response.status_code != 200:
        print(f"❌ Could not fetch PTAM for update: {response.status_code}")
        return False
    
    ptam_data = response.json()
    
    # Modify the status and add a note
    ptam_data["status"] = "Em revisão"
    ptam_data["conclusion_text"] = "PTAM atualizado durante teste automatizado"
    
    # Remove fields that shouldn't be in the update request
    update_data = {k: v for k, v in ptam_data.items() 
                   if k not in ['id', 'user_id', 'created_at', 'updated_at']}
    
    response = requests.put(f"{BASE_URL}/ptam/{ptam_id}", json=update_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ PTAM updated successfully")
        print(f"   - Status: {result.get('status', 'N/A')}")
        print(f"   - Conclusion Text: {result.get('conclusion_text', 'N/A')[:50]}...")
        return True
    else:
        print(f"❌ PTAM update failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_generate_docx():
    """Test 5: Generate DOCX - CRITICAL TEST"""
    print("\n📄 Test 5: Generating DOCX (CRITICAL)...")
    
    if not ptam_id:
        print("❌ No PTAM ID available for testing")
        return False
    
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.get(f"{BASE_URL}/ptam/{ptam_id}/docx", headers=headers)
    
    if response.status_code == 200:
        print(f"✅ DOCX generated successfully")
        
        # Check Content-Type
        content_type = response.headers.get('Content-Type', '')
        expected_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if content_type == expected_type:
            print(f"✅ Content-Type correct: {content_type}")
        else:
            print(f"⚠️  Content-Type unexpected: {content_type}")
        
        # Check Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'PTAM_' in content_disposition and '.docx' in content_disposition:
            print(f"✅ Content-Disposition header correct: {content_disposition}")
        else:
            print(f"⚠️  Content-Disposition header unexpected: {content_disposition}")
        
        # Check response body size
        body_size = len(response.content)
        print(f"   - Response body size: {body_size} bytes")
        if body_size > 5000:
            print(f"✅ Response body size adequate (> 5000 bytes)")
        else:
            print(f"⚠️  Response body size too small (< 5000 bytes)")
        
        # Check if it's a valid DOCX (ZIP format - starts with "PK")
        if response.content[:2] == b'PK':
            print(f"✅ Valid DOCX format (ZIP signature detected)")
        else:
            print(f"⚠️  Invalid DOCX format (no ZIP signature)")
            print(f"   First 10 bytes: {response.content[:10]}")
        
        # Save file for verification
        docx_path = f"/app/test_ptam_{ptam_id}.docx"
        with open(docx_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ DOCX saved to: {docx_path}")
        
        return True
    else:
        print(f"❌ DOCX generation failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_user_isolation():
    """Test 6: User isolation - second user should not see first user's PTAM"""
    print("\n🔒 Test 6: Testing user isolation...")
    
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = requests.get(f"{BASE_URL}/ptam", headers=headers)
    
    if response.status_code == 200:
        ptams = response.json()
        print(f"✅ User 2 PTAM list retrieved")
        print(f"   - Count: {len(ptams)}")
        
        if len(ptams) == 0:
            print(f"✅ User isolation working correctly (empty array)")
            return True
        else:
            print(f"⚠️  User isolation may be broken (found {len(ptams)} PTAMs)")
            for ptam in ptams:
                print(f"   - PTAM ID: {ptam.get('id', 'N/A')}")
            return False
    else:
        print(f"❌ User 2 PTAM listing failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_delete_ptam():
    """Test 7: Delete PTAM"""
    print("\n🗑️  Test 7: Deleting PTAM...")
    
    if not ptam_id:
        print("❌ No PTAM ID available for testing")
        return False
    
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.delete(f"{BASE_URL}/ptam/{ptam_id}", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ PTAM deleted successfully")
        print(f"   - Response: {result}")
        
        # Verify deletion by trying to get the PTAM
        get_response = requests.get(f"{BASE_URL}/ptam/{ptam_id}", headers=headers)
        if get_response.status_code == 404:
            print(f"✅ PTAM deletion verified (404 on subsequent GET)")
            return True
        else:
            print(f"⚠️  PTAM may not be fully deleted (GET returned {get_response.status_code})")
            return False
    else:
        print(f"❌ PTAM deletion failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def run_all_tests():
    """Run all PTAM tests"""
    print("🚀 Starting PTAM Backend Tests")
    print("=" * 50)
    
    tests = [
        ("Authentication Setup", test_auth_setup),
        ("Create PTAM", test_create_ptam),
        ("List PTAMs", test_list_ptam),
        ("Get PTAM by ID", test_get_ptam_by_id),
        ("Update PTAM", test_update_ptam),
        ("Generate DOCX (CRITICAL)", test_generate_docx),
        ("User Isolation", test_user_isolation),
        ("Delete PTAM", test_delete_ptam),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("🏁 PTAM Test Results Summary")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("🎉 All PTAM tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed - see details above")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)